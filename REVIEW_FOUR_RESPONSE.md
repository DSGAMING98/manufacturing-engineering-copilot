# Supervisor review IV: measured fixes and outstanding validation

**Manuscript:** MFG Workbench: Temporal Robustness of Manufacturing Failure Screening and Traceable Engineering Software  
**Date:** 14 November 2026  
**Status:** Revised IEEE-style research draft; NOT an accepted or submission-ready journal paper.

## Newly executed experiments

- [Successful, reproducible GitHub Actions research run](https://github.com/DSGAMING98/manufacturing-engineering-copilot/actions/runs/43572614414)
- [Chronological SECOM baseline evidence](real_models/evidence/chrono_baseline_report.json)
- [Repeated-CV and retuned baseline evidence](real_models/evidence/fair_cv_review.json)
- [Original model and dataset evidence](real_models/evidence/real_model_report.json)
- [Source publication metadata](CITATION.cff)

### Chronological SECOM, fixed timestamp order

Earliest 940 training rows (76 failures), next 313 validation (11 failures), latest 314 test rows (17 failures). Models selected hyperparameters on chronological validation, not test.

| Method | Test ROC-AUC | Test AP | Failure F1 | Alerts (of 314) |
|---|---:|---:|---:|---:|
| Always pass | 0.5000 | 0.0541 | 0 | 0 |
| Always failure | 0.5000 | 0.0541 | 0.1027 | 314 |
| Logistic regression (C=.1) | **0.6681** | 0.0946 | 0.1240 | 225 |
| RBF SVM (C=.1) | 0.3422 | 0.0424 | 0.0411 | 129 |
| kNN (k=5) | 0.4571 | 0.0511 | 0.1027 | 314 |
| Gradient boosting (60 estimators) | 0.4381 | 0.0496 | 0.0580 | 52 |
| Extra Trees (max_features=.5) | **0.4965** | 0.0545 | 0.0333 | 43 |

Extra Trees chronology AUC 95% row-bootstrap CI: [0.3559, 0.6398]; logistic [0.5345, 0.7932]. Logistic detects 15/17 failures but incorrectly alerts on 210/297 nonfailures. These exploratory holdout comparisons do not prove model superiority or causal concept drift.

**Original stratified random-split Extra Trees ROC-AUC = 0.7964**, measured on a *different* test split with a different model fit. The contrast with chronology is a sensitivity finding, not a paired controlled drift experiment.

### Repeated 3-fold x 2-repeat development-set CV, original split

- Released steel RF macro-F1: **0.7875 ± 0.0174**; original held-out test accuracy **0.8021**.
- Released SECOM Extra Trees ROC-AUC: **0.7249 ± 0.0297**; original held-out test ROC-AUC **0.7964**.
- Competitors validated over small configuration grids before post-hoc test comparison. The CV procedure is *not fully nested* because the original validation subset influenced candidate choice.
- Tuned steel gradient-boosting held-out test accuracy **0.7712** vs RF **0.8021**. Paired correctness exact McNemar p = **0.09614** (unadjusted, not statistically significant at 0.05). The test partition was already reported before these comparisons.
- The full per-method CV, selected hyperparameters, holdout metrics and paired p values are preserved in the two JSON files above.

### Release parity and development diagnostics

- The exported steel forest agrees with the refitted scikit-learn reference on **389/389** held-out labels. Maximum absolute 7-class probability difference: **4.9984e-7**. This parity required correcting threshold export precision and float32 inference semantics.
- Developer-authored request-router test: **114/125** correct, including 20/20 unsupported prompts abstained. This is an internal diagnostic, **not independent routing accuracy**.
- Retrieval hit@k and human SUS are **not measured**. No invented labels or usability respondents.

## Editorial and integrity responses

- Lead with temporal evaluation-protocol sensitivity, not claims of a new estimator.
- State that old results were posted in GitHub release documentation, not a previously published journal article.
- Describe numerical feature input, SECOM low positive counts (random validation 21, chronological validation 11), and that released models were trained only on original training portions, not refitted on train+validation.
- Expose SECOM failure F1 and AP in performance figure; show steel per-class test support.
- Correct BM25 attribution, captions, author affiliation, provenance, repetition, grammar and DOI URLs.
- Retain substantive AI-drafting disclosure, subject to the selected venue's policy.

## Remaining actions before submission

1. Recruit independent qualified evaluators to label manufacturing routing queries and relevance pairs, then report blinded inter-reviewer agreement and hit@k; **no independent results exist yet**.
2. Confirm coauthor roles, approvals and the target journal's ethics and AI policies.
3. Archive a version-tagged reproducible GitHub release via Zenodo to obtain a **real DOI**. The repository has a CITATION.cff but no minted DOI.
4. Use the target venue's actual manuscript template. An IEEEtran conference draft is not a SoftwareX manuscript.

**Venue note:** SoftwareX is a plausible software-paper route. JOSS currently requires a sustained public software-development history (over six months), which this newly created repo does not yet meet. No venue acceptance is promised.
