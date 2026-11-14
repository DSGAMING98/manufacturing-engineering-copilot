"""Chronological SECOM sensitivity experiment, separate from released random-split test.

Sort the UCI SECOM source rows by their recorded timestamp, fit on the
earliest 60%, select hyperparameters/threshold on the next 20%, and measure
the final 20%. This retrospective chronological split is NOT a prospective
plant evaluation and does not establish generalization across equipment/sites.

Run: python -m real_models.evaluate_secom_chrono
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (average_precision_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, roc_auc_score)
from sklearn.pipeline import Pipeline

from real_models.train_real_models import fetch

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "real_models/evidence/secom_chronological_report.json"


def read_labels_and_timestamps(path):
    labels, times = [], []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        pieces = line.strip().split(maxsplit=1)
        if len(pieces) != 2:
            raise ValueError(f"SECOM labels line {line_no} missing timestamp")
        labels.append(1 if int(pieces[0]) == 1 else 0)
        timestamp = pieces[1].strip().strip('"').strip("'")
        parsed = None
        for fmt in ("%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(timestamp, fmt)
                break
            except ValueError:
                pass
        if parsed is None:
            raise ValueError(f"Cannot parse timestamp at row {line_no}: {timestamp!r}")
        times.append(parsed)
    return np.asarray(labels, dtype=int), np.asarray(times, dtype=object)


def get_scores(y, prob, threshold):
    pred = (prob >= threshold).astype(int)
    return {
        "roc_auc": round(float(roc_auc_score(y, prob)), 6),
        "average_precision": round(float(average_precision_score(y, prob)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 6),
        "failure_f1": round(float(f1_score(y, pred, zero_division=0)), 6),
        "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
    }


def main():
    folder, source_hash = fetch("secom")
    x = np.genfromtxt(folder / "secom.data", missing_values="NaN")
    labels, times = read_labels_and_timestamps(folder / "secom_labels.data")
    if x.shape != (len(labels), 590):
        raise AssertionError(f"Unexpected SECOM dimensions {x.shape}")
    order = np.argsort(times, kind="stable")
    x, y, times = x[order], labels[order], times[order]
    n = len(y)
    a, b = int(n*.6), int(n*.8)
    sections = [
        ("train", slice(0, a)),
        ("validation", slice(a, b)),
        ("test", slice(b, n)),
    ]
    splits = {name: {"count": int(len(y[s])),
                      "failures": int(y[s].sum()),
                      "first_timestamp": times[s][0].isoformat(sep=" "),
                      "last_timestamp": times[s][-1].isoformat(sep=" ")}
              for name, s in sections}
    if not all(len(set(y[s])) == 2 for _, s in sections):
        outcome = {"status": "NOT_ESTIMABLE", "reason": "One temporal partition has only one class",
                   "splits": splits, "source_sha256": source_hash}
        DEST.write_text(json.dumps(outcome, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(outcome, indent=2))
        return
    candidates = []
    for fraction in ("sqrt", 0.3, 0.5):
        model = Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("forest", ExtraTreesClassifier(n_estimators=600,
                class_weight="balanced", max_features=fraction,
                random_state=42, n_jobs=-1)),
        ])
        model.fit(x[:a], y[:a])
        valp = model.predict_proba(x[a:b])[:, 1]
        score = float(roc_auc_score(y[a:b], valp))
        candidates.append((score, fraction, model, valp))
    score, fraction, model, valp = max(candidates, key=lambda c:c[0])
    threshold = float(max(np.unique(valp), key=lambda t:
                          (f1_score(y[a:b], valp >= t, zero_division=0), t)))
    prob = model.predict_proba(x[b:])[:, 1]
    output = {
        "status": "MEASURED",
        "source": "UCI SECOM, DOI 10.24432/C54305",
        "source_archive_sha256": source_hash,
        "method": "retrospective timestamp-sorted contiguous 60/20/20",
        "time_zone": "not supplied by UCI source",
        "split_rule": "stable sort by supplied timestamp; never randomize rows",
        "splits": splits,
        "selection": {"validation_roc_auc": round(score, 6),
                      "selected_max_features": fraction,
                      "validation_selected_failure_f1_threshold": threshold},
        "validation": get_scores(y[a:b], valp, threshold),
        "chronological_test": get_scores(y[b:], prob, threshold),
        "limitations": [
            "Not a prospective or cross-plant test.",
            "The timestamp order may correlate with shifts or equipment changes.",
            "The released random-split model and this chronological model were trained on different partitions.",
            "Hyperparameter and operating threshold selection uses only chronological validation records."
        ],
    }
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
