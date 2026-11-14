# MFG Copilot — current technical report

## Objective

Build a domain-focused manufacturing assistant that supports engineering design,
process planning, production, quality, maintenance, documentation and evidence
retrieval while keeping calculations and model claims traceable.

## Implemented system

The prototype combines deterministic engineering tools, registered-document
retrieval and two models trained on observed manufacturing measurements. The
website exposes eight workspaces and returns structured reports with status,
inputs, derived values and citations.

The active ML evidence comprises 3,508 public observed records. Steel fault
classification reaches 80.39% macro-F1 on a locked 389-record test. The SECOM
failure-risk model reaches 79.64% ROC-AUC and 73.60% balanced accuracy on a locked
314-record test, but failure F1 is only 28.04%; this limitation is material.

## Engineering methods

- Design: worst-case one-dimensional limit arithmetic.
- Process: turning-speed, feed-rate and ideal-time equations.
- Production: availability × performance × quality OEE calculation.
- Quality: inclusive lower/upper specification comparison.
- Maintenance: retrospective MTBF, MTTR and observed availability.
- Documentation: schema-validated inspection-record drafts.
- Evidence: local chunk retrieval with SHA-256 and line-level provenance.
- ML quality: balanced random forest over 27 steel measurements.
- ML process risk: imputed Extra Trees ensemble over 590 SECOM columns.

## Verification

Model selection uses training and validation partitions only. Final metrics come
from locked test partitions. The repository includes per-class results, confusion
matrices, source hashes, licenses, fixed seeds and training code. Unit, integration,
security and stress tests run without network access after artifacts are present.

## Results and figures

The headline locked-test comparison, class-level metrics, confusion matrices and
dataset split counts are reproduced from
[`real_models/evidence/real_model_report.json`](real_models/evidence/real_model_report.json)
by `python -m real_models.plot_real_results`.

- [Figure 1 — locked-test metrics and 95% confidence intervals](real_models/figures/Fig01_real_model_performance.png)
- [Figure 2 — steel precision, recall and F1 by class](real_models/figures/Fig02_steel_per_class_metrics.png)
- [Figure 3 — steel confusion matrix](real_models/figures/Fig03_steel_confusion_matrix.png)
- [Figure 4 — SECOM confusion matrix](real_models/figures/Fig04_secom_confusion_matrix.png)
- [Figure 5 — observed dataset partitions](real_models/figures/Fig05_dataset_splits.png)

Every figure has a matching SVG and CSV export in `real_models/figures/`. This
keeps the report graphics traceable to exact machine-readable evidence.

## Research interpretation

The prototype demonstrates feasibility on public observed manufacturing data; it
does not yet demonstrate plant transfer. A defensible paper should frame the
present results as within-dataset benchmarks and make the next study a grouped
machine, lot, date or site holdout. Any stronger industrial claim requires an
authorized target-plant dataset collected under a frozen protocol.

## Deployment

- Source: https://github.com/DSGAMING98/manufacturing-engineering-copilot
- Prototype: https://manufacturing-engineering-copilot.vercel.app/
- Runtime: dependency-free Python inference for the deployed forest plus static UI
