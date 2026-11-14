# Sixth supervisor review: independent SECOM preprint, verified prevalence, and Draft VII

**Date:** 14 November 2026  
**Manuscript:** *MFG Workbench: Reproducible SECOM Time-Split Audits and Failure-Screening Diagnostics*  
**Status:** IEEE-style revised research draft; faculty review still required.

## Critical novelty acknowledgement

Allahverdi and Akbarzadeh, ["Application of Machine Learning in Optimizing Industrial Assembly Lines: A Chronologically Validated Study of Predictive Quality Control"](https://doi.org/10.21203/rs.3.rs-11317815/v1), Research Square preprint posted **26 October 2026**, already documents the SECOM random-versus-chronological performance gap. Their random RF 5x5-fold ROC-AUC was **0.768 ± 0.010** and their five-block temporal model-family means were **0.514–0.599**. Their thresholded XGBoost analysis flagged 323/471 units to find 23/26 failures at precision 0.071.

The present work must therefore **not claim priority for discovering SECOM time-split sensitivity**. Its narrower independently executed additions are:
- Fifty separately seeded 60/20/20 stratified random holdouts, mean ROC-AUC 0.7359 (SD 0.0517); the original seed-42 ROC-AUC 0.7964 is only one favorable observation.
- Three expanding-origin Extra Trees tests, ROC-AUC 0.5598, 0.5409 and 0.4732.
- Source-verified time-block fail-rate counts and their connection to alert-threshold sensitivity.
- Transparent alert counts, degenerate all-failure 5-NN decision behavior, and 16-row block-bootstrap uncertainty.
- Fully reproducible scripts and hashes, plus separate exported-steel model parity checks.

Scores from the two papers have differing training, validation and chronological test protocols, so they are **not directly comparable as an algorithm leaderboard**.

## Raw timestamp-label audit: executed and passed

- [Audit source](real_models/audit_temporal_prevalence.py)
- [Recorded audit JSON](real_models/evidence/secom_temporal_prevalence.json)
- [GitHub Actions audit run](https://github.com/DSGAMING98/manufacturing-engineering-copilot/actions/runs/43576477500)

SECOM's original `secom_labels.data` has 1,567 observations and 104 failures. Stable timestamp ordering and five consecutive, disjoint ranges give:

| Record range | Total | Failures | Failure prevalence |
|---|---:|---:|---:|
| 1–627 | 627 | 65 | 0.1037 |
| 628–862 | 235 | 6 | 0.0255 |
| 863–1097 | 235 | 7 | 0.0298 |
| 1098–1332 | 235 | 17 | 0.0723 |
| 1333–1567 | 235 | 9 | 0.0383 |

**65/104 (62.5%)** of failures occur in the first 627 samples (40.0% of records). The 60/20/20 chronological split includes 76/940, 11/313, 17/314 failures. Different observed failure prevalence is **not proof** that prevalence changes caused the ROC-AUC gap; changing feature-label relationships, process conditions and inter-record dependence remain untested explanations.

## Editorial changes in Draft VII

- Retitled and reframed as **independent confirmation and decision-level extension**, not a novel chronology finding.
- Cited the Research Square preprint by DOI, marked it as a preprint and compared protocols side by side.
- Rewrote SECOM prior work around published 2018 and 2026 studies, dated manufacturing process monitoring and time-aware validation.
- Added a plot from independently audited original UCI time-block failures.
- Kept the random-split **mean 0.736** ahead of single-seed **0.7964** in the abstract and conclusion.
- Explained chronological logistic regression's 225 alerts, 210 false alarms and 0.124 failure F1, plus 5-NN's all-failure threshold.
- Reported chronological SVM ROC-AUC 0.342 with standard row-bootstrap CI [0.220,0.495], explicitly noting temporal-dependence limits.
- Standardized SECOM ROC-AUC, AP and F1 values to a 0–1 scale, and labelled alert counts explicitly.
- Corrected chart terminology to **expanding-origin**.
- Retained approved university author block, substantive AI-drafting disclosure, IEEE two-column format and 31 fully cited references.

## Outstanding publication and integrity requirements

The repository has `CITATION.cff`, but no Zenodo DOI was minted. A Zenodo deposit requires an authorized linked account and an actual versioned release. Do not invent a DOI. No independent user/retrieval evaluation or prospective plant data exists. A journal may still deem the additional benchmark analysis insufficiently novel. Journal-specific templates and AI-disclosure policies must be reviewed with the faculty coauthor before submission.
