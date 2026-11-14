"""Baseline comparisons for peer review, using the existing MFG Copilot split.

Run: python -m real_models.benchmark_baselines --cv-folds 3 --cv-repeats 2
These are post-hoc comparisons on a previously reported test partition,
not experiments on a new untouched holdout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             f1_score, roc_auc_score, average_precision_score,
                             confusion_matrix)
from sklearn.model_selection import (RepeatedStratifiedKFold, cross_val_score,
                                     train_test_split)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from real_models.train_real_models import fetch, train_steel, train_secom

ROOT = Path(__file__).resolve().parents[1]


def splits(x, y):
    xd, xt, yd, yt = train_test_split(x, y, test_size=.2, stratify=y, random_state=42)
    xtr, xv, ytr, yv = train_test_split(xd, yd, test_size=.25,
                                       stratify=yd, random_state=42)
    return xd, yd, xtr, xv, xt, ytr, yv, yt


def candidates():
    def scale(model):
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), model)
    return {
        "dummy_majority": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": scale(LogisticRegression(
            max_iter=1800, class_weight="balanced", random_state=42)),
        "rbf_svm": scale(SVC(C=1.0, kernel="rbf", class_weight="balanced",
                             probability=True, random_state=42)),
        "knn_11": scale(KNeighborsClassifier(n_neighbors=11)),
        "gradient_boosting": make_pipeline(
            SimpleImputer(strategy="median"),
            GradientBoostingClassifier(random_state=42)),
    }


def select_threshold(yval, prob):
    # The threshold must never be tuned on the test set.
    return float(max(np.unique(prob),
                     key=lambda v: (f1_score(yval, prob >= v, zero_division=0), v)))


def paired_correctness(ytrue, incumbent, baseline):
    a, b = incumbent == ytrue, baseline == ytrue
    b_only, a_only = int((~a & b).sum()), int((a & ~b).sum())
    discordant = b_only + a_only
    p = float(binomtest(min(a_only, b_only), discordant, .5).pvalue) if discordant else 1.0
    return {
        "baseline_only_correct": b_only, "incumbent_only_correct": a_only,
        "discordant": discordant, "exact_mcnemar_two_sided_p": p,
        "note": "Tests paired correctness, not paired F1/ROC-AUC differences"
    }


def run_task(name, x, y, incumbent, *, folds, repeats):
    xd, yd, xtr, xv, xt, ytr, yv, yt = splits(x, y)
    if name == "steel":
        ref, cv_metric = incumbent.predict(xt), "f1_macro"
    else:
        ref_threshold, ref_model = incumbent
        ref = (ref_model.predict_proba(xt)[:, 1] >= ref_threshold).astype(int)
        cv_metric = "roc_auc"
    cv = RepeatedStratifiedKFold(n_splits=folds, n_repeats=repeats, random_state=42)
    result = {
        "task": name, "records": len(y),
        "train": len(ytr), "validation": len(yv), "test": len(yt),
        "development_cv": {"folds": folds, "repeats": repeats, "metric": cv_metric},
        "baselines": {}
    }
    for label, model in candidates().items():
        scores = cross_val_score(model, xd, yd, scoring=cv_metric, cv=cv,
                                 n_jobs=1, error_score="raise")
        model.fit(xtr, ytr)
        if name == "steel":
            pred = model.predict(xt)
            metrics = {"accuracy": float(accuracy_score(yt, pred)),
                       "macro_f1": float(f1_score(yt, pred, average="macro"))}
        else:
            val_prob = model.predict_proba(xv)[:, 1]
            threshold = select_threshold(yv, val_prob)
            prob = model.predict_proba(xt)[:, 1]
            pred = (prob >= threshold).astype(int)
            metrics = {
                "threshold_selected_on_validation": threshold,
                "roc_auc": float(roc_auc_score(yt, prob)),
                "average_precision": float(average_precision_score(yt, prob)),
                "balanced_accuracy": float(balanced_accuracy_score(yt, pred)),
                "failure_f1": float(f1_score(yt, pred, zero_division=0)),
                "confusion_matrix": confusion_matrix(yt, pred).tolist(),
            }
        result["baselines"][label] = {
            "cv_mean": float(np.mean(scores)), "cv_std": float(np.std(scores, ddof=1)),
            "existing_holdout_metrics": metrics,
            "paired_correctness_vs_incumbent": paired_correctness(yt, ref, pred)
        }
        print(f"{name}: {label}: CV={np.mean(scores):.4f}, test results recorded")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cv-folds", type=int, default=3)
    p.add_argument("--cv-repeats", type=int, default=2)
    args = p.parse_args()
    if args.cv_folds < 2 or args.cv_repeats < 1:
        p.error("folds >= 2 and repeats >= 1 are required")
    sfolder, shash = fetch("steel")
    matrix = np.loadtxt(sfolder / "Faults.NNA")
    _, steel = train_steel(sfolder)
    s = run_task("steel", matrix[:, :27], matrix[:, 27:].argmax(axis=1),
                 steel, folds=args.cv_folds, repeats=args.cv_repeats)
    efolder, ehash = fetch("secom")
    x = np.genfromtxt(efolder / "secom.data", missing_values="NaN")
    y = (np.loadtxt(efolder / "secom_labels.data", usecols=0).astype(int) == 1).astype(int)
    secom_report, secom_model = train_secom(efolder)
    e = run_task("secom", x, y, (
        secom_report["selection"]["decision_threshold_selected_on_validation_only"],
        secom_model), folds=args.cv_folds, repeats=args.cv_repeats)
    output = {
        "scope": "posthoc_reference_comparisons; same previously reported holdouts",
        "not_new_unseen_data": True,
        "source_archive_sha256": {"steel": shash, "secom": ehash},
        "steel": s, "secom": e,
    }
    path = ROOT / "real_models/evidence/reviewer_baselines.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {path}; do not mix unrelated task metrics.")


if __name__ == "__main__":
    main()
