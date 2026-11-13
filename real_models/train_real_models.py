"""Download licensed observed datasets, train locked models, and export evidence.

The raw files are cached locally and are deliberately not committed. The training
report records source URLs, DOIs and SHA-256 hashes so every run can be audited.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score,
    confusion_matrix, f1_score, precision_recall_fscore_support, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "public_real"
ARTIFACTS = ROOT / "real_models" / "artifacts"
EVIDENCE = ROOT / "real_models" / "evidence"
SOURCES = {
    "secom": {
        "url": "https://archive.ics.uci.edu/static/public/179/secom.zip",
        "doi": "10.24432/C54305",
        "license": "CC BY 4.0",
    },
    "steel": {
        "url": "https://archive.ics.uci.edu/static/public/198/steel+plates+faults.zip",
        "doi": "10.24432/C5J88N",
        "license": "CC BY 4.0",
    },
}
STEEL_FEATURES = [
    "X_Minimum", "X_Maximum", "Y_Minimum", "Y_Maximum", "Pixels_Areas",
    "X_Perimeter", "Y_Perimeter", "Sum_of_Luminosity", "Minimum_of_Luminosity",
    "Maximum_of_Luminosity", "Length_of_Conveyer", "TypeOfSteel_A300",
    "TypeOfSteel_A400", "Steel_Plate_Thickness", "Edges_Index", "Empty_Index",
    "Square_Index", "Outside_X_Index", "Edges_X_Index", "Edges_Y_Index",
    "Outside_Global_Index", "LogOfAreas", "Log_X_Index", "Log_Y_Index",
    "Orientation_Index", "Luminosity_Index", "SigmoidOfAreas",
]
STEEL_CLASSES = ["Pastry", "Z_Scratch", "K_Scratch", "Stains", "Dirtiness", "Bumps", "Other_Faults"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(name: str) -> tuple[Path, str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / f"{name}.zip"
    if not archive.exists():
        urllib.request.urlretrieve(SOURCES[name]["url"], archive)
    extracted = CACHE / name
    if not extracted.exists():
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(extracted)
    return extracted, sha256(archive)


def classification_metrics(y_true, y_pred, *, labels) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=range(len(labels)), zero_division=0
    )
    rng = np.random.default_rng(20261114)
    accuracy_samples, macro_f1_samples = [], []
    for _ in range(1000):
        indices = rng.integers(0, len(y_true), len(y_true))
        accuracy_samples.append(accuracy_score(y_true[indices], y_pred[indices]))
        macro_f1_samples.append(f1_score(y_true[indices], y_pred[indices], average="macro"))
    return {
        "n": int(len(y_true)),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro")), 6),
        "bootstrap_95_ci": {
            "method": "1000 percentile bootstrap resamples; seed 20261114",
            "accuracy": [round(float(v), 6) for v in np.percentile(accuracy_samples, [2.5, 97.5])],
            "macro_f1": [round(float(v), 6) for v in np.percentile(macro_f1_samples, [2.5, 97.5])],
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=range(len(labels))).tolist(),
        "per_class": {
            label: {"precision": round(float(precision[i]), 6), "recall": round(float(recall[i]), 6),
                    "f1": round(float(f1[i]), 6), "support": int(support[i])}
            for i, label in enumerate(labels)
        },
    }


def export_forest(model: RandomForestClassifier, path: Path) -> None:
    trees = []
    for estimator in model.estimators_:
        tree = estimator.tree_
        trees.append({
            "f": tree.feature.astype(int).tolist(),
            "t": [round(float(value), 9) for value in tree.threshold],
            "l": tree.children_left.astype(int).tolist(),
            "r": tree.children_right.astype(int).tolist(),
            "v": [[round(float(v), 9) for v in row[0]] for row in tree.value],
        })
    payload = {
        "model_version": "steel-rf-2026-11-14",
        "dataset": "UCI Steel Plates Faults",
        "dataset_doi": SOURCES["steel"]["doi"],
        "features": STEEL_FEATURES,
        "classes": STEEL_CLASSES,
        "trees": trees,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as handle:
        json.dump(payload, handle, separators=(",", ":"))


def train_steel(folder: Path) -> tuple[dict, RandomForestClassifier]:
    matrix = np.loadtxt(folder / "Faults.NNA")
    x, y = matrix[:, :27], matrix[:, 27:].argmax(axis=1)
    x_dev, x_test, y_dev, y_test = train_test_split(x, y, test_size=0.20, random_state=42, stratify=y)
    x_train, x_val, y_train, y_val = train_test_split(x_dev, y_dev, test_size=0.25, random_state=42, stratify=y_dev)
    candidates = []
    for depth in (12, 18, None):
        model = RandomForestClassifier(
            n_estimators=300, max_depth=depth, class_weight="balanced_subsample",
            max_features="sqrt", random_state=42, n_jobs=-1,
        ).fit(x_train, y_train)
        score = f1_score(y_val, model.predict(x_val), average="macro")
        candidates.append((score, depth, model))
    _, depth, model = max(candidates, key=lambda item: item[0])
    report = {
        "dataset": "UCI Steel Plates Faults", "observed_records": int(len(y)),
        "split": {"method": "fixed stratified 60/20/20", "seed": 42,
                  "train": int(len(y_train)), "validation": int(len(y_val)), "test": int(len(y_test))},
        "selection": {"metric": "validation macro-F1", "max_depth_candidates": [12, 18, None], "selected_max_depth": depth},
        "validation": classification_metrics(y_val, model.predict(x_val), labels=STEEL_CLASSES),
        "locked_test": classification_metrics(y_test, model.predict(x_test), labels=STEEL_CLASSES),
        "limitations": ["Random split does not measure cross-plant transfer.", "Input features are anonymized and do not cover every steel process."],
    }
    return report, model


def train_secom(folder: Path) -> tuple[dict, Pipeline]:
    x = np.genfromtxt(folder / "secom.data", missing_values="NaN")
    y = (np.loadtxt(folder / "secom_labels.data", usecols=0).astype(int) == 1).astype(int)
    x_dev, x_test, y_dev, y_test = train_test_split(x, y, test_size=0.20, random_state=42, stratify=y)
    x_train, x_val, y_train, y_val = train_test_split(x_dev, y_dev, test_size=0.25, random_state=42, stratify=y_dev)
    candidates = []
    for fraction in ("sqrt", 0.3, 0.5):
        model = Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("forest", ExtraTreesClassifier(n_estimators=600, class_weight="balanced", max_features=fraction, random_state=42, n_jobs=-1)),
        ]).fit(x_train, y_train)
        probabilities = model.predict_proba(x_val)[:, 1]
        candidates.append((roc_auc_score(y_val, probabilities), fraction, model, probabilities))
    _, fraction, model, val_prob = max(candidates, key=lambda item: item[0])
    thresholds = np.unique(val_prob)
    threshold = float(max(thresholds, key=lambda value: f1_score(y_val, val_prob >= value)))
    test_prob = model.predict_proba(x_test)[:, 1]

    def metrics(target, probability):
        prediction = probability >= threshold
        rng = np.random.default_rng(20261114)
        samples = {"balanced_accuracy": [], "failure_f1": [], "average_precision": [], "roc_auc": []}
        for _ in range(1000):
            indices = rng.integers(0, len(target), len(target))
            if len(np.unique(target[indices])) < 2:
                continue
            actual, score, decided = target[indices], probability[indices], prediction[indices]
            samples["balanced_accuracy"].append(balanced_accuracy_score(actual, decided))
            samples["failure_f1"].append(f1_score(actual, decided))
            samples["average_precision"].append(average_precision_score(actual, score))
            samples["roc_auc"].append(roc_auc_score(actual, score))
        return {"n": int(len(target)), "threshold": round(threshold, 6),
                "balanced_accuracy": round(float(balanced_accuracy_score(target, prediction)), 6),
                "failure_f1": round(float(f1_score(target, prediction)), 6),
                "average_precision": round(float(average_precision_score(target, probability)), 6),
                "roc_auc": round(float(roc_auc_score(target, probability)), 6),
                "bootstrap_95_ci": {"method": "1000 percentile bootstrap resamples; seed 20261114",
                                     **{name: [round(float(v), 6) for v in np.percentile(values, [2.5, 97.5])]
                                        for name, values in samples.items()}},
                "confusion_matrix": confusion_matrix(target, prediction).tolist()}

    return {
        "dataset": "UCI SECOM", "observed_records": int(len(y)), "failures": int(y.sum()),
        "split": {"method": "fixed stratified 60/20/20", "seed": 42,
                  "train": int(len(y_train)), "validation": int(len(y_val)), "test": int(len(y_test))},
        "selection": {"metric": "validation ROC-AUC", "max_features_candidates": ["sqrt", 0.3, 0.5], "selected_max_features": fraction,
                      "decision_threshold_selected_on_validation_only": round(threshold, 6)},
        "validation": metrics(y_val, val_prob), "locked_test": metrics(y_test, test_prob),
        "limitations": ["Failure prevalence is low, so accuracy is not reported as the primary metric.", "Anonymized sensor columns limit physical interpretation.", "Random split does not establish future-lot or cross-fab generalization."],
    }, model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Delete no files; re-download only if cache is absent")
    args = parser.parse_args()
    del args
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    secom_folder, secom_hash = fetch("secom")
    steel_folder, steel_hash = fetch("steel")
    steel_report, steel_model = train_steel(steel_folder)
    secom_report, secom_model = train_secom(secom_folder)
    export_forest(steel_model, ROOT / "phase5" / "model" / "steel_fault_forest.json.gz")
    joblib.dump(secom_model, ARTIFACTS / "secom_failure_model.joblib")
    report = {
        "report_version": 1, "trained_at": "2026-11-14", "data_policy": "observed_public_records_only",
        "sources": {
            "steel": {**SOURCES["steel"], "download_sha256": steel_hash},
            "secom": {**SOURCES["secom"], "download_sha256": secom_hash},
        },
        "models": {"steel_fault_classifier": steel_report, "secom_failure_risk": secom_report},
        "research_claim": "Two models trained and evaluated exclusively on observed public manufacturing records.",
    }
    (EVIDENCE / "real_model_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"steel_test": steel_report["locked_test"], "secom_test": secom_report["locked_test"]}, indent=2))


if __name__ == "__main__":
    main()
