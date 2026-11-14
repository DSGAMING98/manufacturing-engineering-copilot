# Fifth academic review: measured temporal robustness and manuscript response

**Research artifact:** MFG Workbench (historical repository slug: manufacturing-engineering-copilot).
**Date:** 14 November 2026.
**Research status:** Post-hoc sensitivity investigation on public SECOM; does not establish causal concept drift or industrial reliability.

## Reproducibility

- [Successful 50-seed, rolling-origin and block-bootstrap Actions run](https://github.com/DSGAMING98/manufacturing-engineering-copilot/actions/runs/43574776524)
- [Complete machine-readable report](real_models/evidence/temporal_robustness_report.json)
- [Executable research source](real_models/temporal_robustness_review.py)

### 50 repeated random splits

The repeated experiment applied stratified 60/20/20 partitions on 50 seeds, each selecting 600-tree Extra Trees feature subsampling from sqrt, 0.3 and 0.5 using its validation split.

| Statistic | ROC-AUC |
|---|---:|
| Random-split mean | 0.735947 |
| Random-split sample SD | 0.051748 |
| Median | 0.740817 |
| Min, max | 0.551438, 0.813831 |
| Empirical 2.5th, 97.5th percentiles | 0.632316, 0.808394 |
| Separate chronological reference | 0.496534 |
| Random-split AUC at/below chronological | 0/50 |

This is a **descriptive, retrospective reference**, not a paired significance test or a confidence interval for future-plant generalization.

### Expanding-origin SECOM evaluation

| Fold | Train n | Validation failures | Test failures | Test ROC-AUC | Test AP | Failure F1 |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 627 | 6 | 7 | 0.559837 | 0.044350 | 0.065041 |
| 2 | 862 | 7 | 17 | 0.540880 | 0.075236 | 0.047619 |
| 3 | 1,097 | 17 | 9 | 0.473206 | 0.047364 | 0.060976 |

The original chronological test had 17 failures, ROC-AUC **0.496534**, and a 16-row circular moving-block bootstrap interval of **[0.276888, 0.671255]** at 95% using 1,200 resamples. This interval is sensitive to block width and the few positive outcomes.

### Five-model chronological comparison

Four of the five learned models have ROC-AUC at or below 0.5. Logistic regression is the single moderate-ranking exception (ROC-AUC 0.6681), yet at its validation-selected threshold flags 225/314 observations with 210 false positives and a failure F1 of 0.1240. Always-failure F1 is 0.1027. Therefore, the regression result is **not evidence of a ready-to-deploy selective failure detector**.

## Manuscript changes (Draft VI)

- Abstract and main narrative now lead with the common failure pattern rather than the best post-hoc model.
- The system description is condensed to a short supporting software-artifact section.
- SECOM accuracy-based McNemar p-values are removed from the comparison table. Steel paired results retain directions (model-only correct versus baseline-only correct).
- ROC-AUC is presented on a 0–1 scale throughout prose, tables and updated figures.
- Post-hoc test reuse, small positive counts, and the 5-NN all-failure threshold are explicit.
- Original baseline validation-selected settings are listed with both tables.
- Added actual 50-seed, expanding-origin and block-bootstrap results with provenance links.
- The IEEE-style manuscript has nine pages and 32 cited sources.
- Hoang et al. 2026 volume 300, article 110091 and Brooke 1996 SUS chapter DOI 10.1201/9781498710411-35 were independently verified.

## Remaining before submission

1. Obtain independently labelled router/retrieval examples or frame the study exclusively as temporal benchmark methodology plus reproducible software.
2. Preserve a tagged public code/data archive and mint a real Zenodo DOI. CITATION.cff by itself is not a DOI.
3. Obtain faculty approval of authorship and substantive AI-assistance disclosure; follow target journal template.
4. Obtain a genuinely held-out prospective/time-block or cross-plant evaluation before claiming future industrial reliability.

**No human study, user-validation metric, journal acceptance or DOI has been invented.**
