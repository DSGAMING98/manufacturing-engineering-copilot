# Research-paper readiness

## Completed evidence

- Two citable, CC BY 4.0 manufacturing datasets with DOI and source URL.
- Source archive SHA-256 hashes recorded in machine-readable evidence.
- Fixed training, validation and locked test partitions.
- Validation-only hyperparameter and threshold selection.
- Accuracy, macro-F1, per-class precision/recall/F1 and confusion matrix for steel.
- ROC-AUC, average precision, balanced accuracy, failure F1 and confusion matrix
  for imbalanced SECOM data.
- Deterministic 1,000-resample percentile bootstrap confidence intervals for
  locked-test metrics.
- Reproducible training command and committed deployed model export.
- Explicit limitations and no claim of cross-plant validation.

## Required before claiming industrial validation

- Permission-cleared data from the intended plant or an independently held-out site.
- Split by machine, product lot, time period or site rather than random rows.
- Frozen preprocessing and endpoint before opening the final test set.
- Repeated grouped resampling on a future machine/time/site-separated dataset.
- Comparison with simple baselines and ablation of major feature groups.
- Error review by qualified manufacturing personnel.
- Runtime, memory and latency measurements on the intended hardware.
- Venue-specific paper template, page limits, ethics statements and disclosure.

## Accurate paper wording

Use “trained and evaluated on observed public manufacturing datasets.” Do not use
“industrially validated,” “production ready,” “100% validated,” or “autonomous.”
The current study supports a real-data benchmark claim, not a plant-deployment
claim.
