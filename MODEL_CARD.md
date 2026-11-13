# Model card: observed-data manufacturing models

## Steel surface-fault classifier

- Version: `steel-rf-2026-11-14`
- Algorithm: 300-tree random forest
- Training source: UCI Steel Plates Faults, DOI `10.24432/C5J88N`
- Source license: CC BY 4.0
- Records: 1,941; features: 27; classes: 7
- Split: fixed stratified 60/20/20, seed 42
- Selection: maximum depth chosen by validation macro-F1
- Locked test: 389 records, 80.21% accuracy (95% bootstrap CI 75.84–84.07%),
  80.39% macro-F1 (95% bootstrap CI 74.72–84.78%)

Per-class test F1: Pastry 71.88%, Z_Scratch 81.58%, K_Scratch 96.73%,
Stains 96.30%, Dirtiness 66.67%, Bumps 73.75%, Other_Faults 75.81%.

Intended use: reproducible surface-fault classification research using the
published 27-feature schema. It is not a product-release system.

## SECOM failure-risk model

- Algorithm: 600-estimator Extra Trees ensemble with median imputation
- Training source: UCI SECOM, DOI `10.24432/C54305`
- Source license: CC BY 4.0
- Records: 1,567; observed failures: 104; input columns: 590
- Split: fixed stratified 60/20/20, seed 42
- Selection: feature subsampling by validation ROC-AUC; threshold by validation F1
- Locked test: 314 records, 79.64% ROC-AUC, 73.60% balanced accuracy,
  28.04% failure F1, 19.17% average precision
- 95% bootstrap CIs: ROC-AUC 70.06–87.27%, balanced accuracy 63.09–83.10%,
  failure F1 17.78–39.66%, average precision 11.27–34.82%
- Locked-test confusion matrix: TN 222, FP 71, FN 6, TP 15

Intended use: research on ranking and screening process records for investigation.
The low failure F1 and false-positive count make it unsuitable for unattended
operational decisions.

## Common limitations

The sources are observed manufacturing data, but public dataset performance does
not establish performance at another site. Neither evaluation is time-separated
or plant-separated. Metrics represent one fixed split and one model-selection
procedure. Full machine-readable evidence is in
`real_models/evidence/real_model_report.json`.
