"""Compare all held-out steel rows against the deployed JSON forest.

Run: python -m real_models.verify_export
Requires research dependencies and UCI dataset download access.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split

from phase5.real_model import load_model, predict_steel_fault
from real_models.train_real_models import STEEL_CLASSES, fetch, train_steel

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    args = parser.parse_args()
    folder, archive_hash = fetch("steel")
    matrix = np.loadtxt(folder / "Faults.NNA")
    x, y = matrix[:, :27], matrix[:, 27:].argmax(axis=1)
    _, x_test, _, y_test = train_test_split(
        x, y, test_size=.2, random_state=42, stratify=y)
    report, original = train_steel(folder)
    names = load_model()["classes"]
    if names != STEEL_CLASSES:
        raise AssertionError("Deployed class order differs from training class order")
    original_probs = original.predict_proba(x_test)
    exported_probs = np.asarray([
        [predict_steel_fault(row.tolist())["probabilities"][label] for label in names]
        for row in x_test], dtype=float)
    original_labels = np.argmax(original_probs, axis=1)
    exported_labels = np.argmax(exported_probs, axis=1)
    differences = np.max(np.abs(original_probs - exported_probs), axis=1)
    mismatches = np.flatnonzero(original_labels != exported_labels)
    observed_accuracy = float(np.mean(exported_labels == y_test))
    recorded_accuracy = float(report["locked_test"]["accuracy"])
    passed = (len(mismatches) == 0 and
              bool(np.max(differences) <= args.tolerance) and
              abs(observed_accuracy - recorded_accuracy) < 1e-5)
    outcome = {
        "status": "PASS" if passed else "FAIL",
        "test_rows": int(len(x_test)),
        "source_archive_sha256": archive_hash,
        "exported_model_version": load_model()["model_version"],
        "mismatched_predicted_classes": int(len(mismatches)),
        "mismatch_test_positions": mismatches.tolist(),
        "maximum_class_probability_delta": float(np.max(differences)),
        "numerical_tolerance": args.tolerance,
        "exported_locked_test_accuracy": round(observed_accuracy, 6),
        "retrained_locked_test_accuracy": round(recorded_accuracy, 6),
        "method": "all locked-test rows; full seven-class probability-vector comparison"
    }
    output = ROOT / "real_models/evidence/export_parity_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(outcome, indent=2))
    if not passed:
        raise SystemExit("Export parity FAILED; do not claim exact agreement")


if __name__ == "__main__":
    main()
