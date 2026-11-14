# Supervisor review VII: focused SECOM research, measured time-block and missingness audits

**Date:** 2026-11-14
**Paper:** *Dissecting SECOM Random-Split Performance: Time-Block and Decision Diagnostics*
**Status:** IEEE conference-style manuscript prepared separately from the MFG Workbench software article, for mentor review. **Not an accepted paper.**

## Evidence and source

- [Successful GitHub Actions diagnostic run](https://github.com/DSGAMING98/manufacturing-engineering-copilot/actions/runs/43578872493)
- [Measured full JSON report](real_models/evidence/secom_block_diagnostics.json)
- [Reproducible new diagnostics script](real_models/secom_block_diagnostics.py)
- [Earlier 50-seed and expanding-origin results](real_models/evidence/temporal_robustness_report.json)
- [Verified raw timestamped failure counts](real_models/evidence/secom_temporal_prevalence.json)
- UCI SECOM source DOI: https://doi.org/10.24432/C54305, archive SHA-256 `eea568baf3c2229096d7d294cf0b096b5502bd96d92c0b80a65b84714059be8e`

## Independent prior art must be credited

A. Allahverdi and S. Akbarzadeh, *Application of Machine Learning in Optimizing Industrial Assembly Lines: A Chronologically Validated Study of Predictive Quality Control*, Research Square preprint (posted October 26, 2026), DOI https://doi.org/10.21203/rs.3.rs-11317815/v1. Their manuscript predates this paper and already reports random-vs-temporal SECOM degradation. The present work **must not claim to have discovered that effect**. Research Square indexing can lag; this citation is also supported by the manuscript PDF supplied for review.

## New full-scale results (executed, not predicted)

**Block-conditioned ROC-AUC from the SAME 50 random-split test predictions:**
- First 627 records: **0.6710 ± 0.0731** (seed SD, 50 seeds).
- Last 940 records: **0.7292 ± 0.0823** (50 seeds).
- Mean paired early-minus-later AUC: **−0.0581 ± 0.1203**; early exceeds later in **16/50** runs.
- Consecutive five-block means: 0.6710 (50/50 defined), 0.7038 (39/50), 0.7900 (40/50), 0.5901 (48/50), 0.8825 (44/50). In narrow blocks, class absence and very few failures make ROC-AUC unstable.
- This DISCONFIRMS the simple hypothesis that early, high-failure TEST rows alone raise the overall random-split metric. It **does not identify the causal mechanism** for chronological deterioration, because the random training sets include observations from later periods.

**Temporal missingness:**
- Missing-cell fraction across chronological blocks: 5.262%, 5.308%, 3.620%, 3.202%, 4.088%.
- Separate missingness-only classification of first 627 vs later 940 rows: ROC-AUC **0.8890**, accuracy **0.7919**, versus period-majority accuracy **0.6008**.
- Train-only feature filter retaining 440/590 features (less than 40% missing; nonconstant): chronological ROC-AUC **0.4858**, vs baseline **0.4965**. This filter did not restore chronological ranking.
- Time-specific missingness is observed, but no causal link between missingness and failure-prediction deterioration has been established.

**Chronological failure screening (314 records, 17 failures):**
- Validation-selected threshold: 43 alerts, 1/17 failures caught, failure F1 0.0333.
- Fixed alert top 5%: 16 alerts, 0/17 caught, F1 0.
- Top 10%: 32 alerts, 1/17 caught, F1 0.0408.
- Top 20%: 63 alerts, 3/17 caught, F1 0.0750.
- Hindsight best test-F1 (invalid deployable threshold): 294 alerts, 17/17 caught, F1 0.1093. This is only slightly above all-failure F1 0.1027; choosing this threshold using test labels would constitute test leakage if advertised as an operating policy.

**Pre-existing reference:**
- Fifty random-split mean ROC-AUC 0.73595 (SD 0.05175); separate chronological Extra Trees ROC-AUC 0.49653.
- Three expanding-origin ROC-AUC 0.55984 / 0.54088 / 0.47321, with 7 / 17 / 9 test failures.

## Manuscript changes

1. New SECOM-only title; no steel classifier, OEE, turning, MTBF, RAG, keyword router or export-parity padding.
2. Time-block decomposition, missingness-period diagnostic, alert budgets, small-label uncertainty and feature-filter sensitivity lead the contribution.
3. Thirty-two literature and dataset references (all cited) and explicitly cited prior preprint.
4. All split analyses called retrospective and post-hoc; paper avoids "locked test" terminology.
5. Six-page IEEE two-column layout retains the faculty mentor and student affiliation and AI-drafting disclosure.
6. Released source code and evidence remain under the historical GitHub slug; no false Zenodo DOI is claimed.

## Further work before submission

- Independently validate the result and annotate any physical or equipment metadata required to explain shift causally.
- Obtain mentor confirmation of authorship, journal AI-disclosure requirements and publication route.
- Archive a tagged, DOI-backed code snapshot through an authorized Zenodo integration. No DOI has yet been issued.
- A single historical dataset and repeatedly inspected tests cannot establish cross-plant generalization.
