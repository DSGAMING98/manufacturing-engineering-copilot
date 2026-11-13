# Demonstration and paper guide

## Demonstration sequence

1. Open the deployed prototype.
2. Run one deterministic quality or OEE calculation and point out the explicit
   inputs, equations and status.
3. Open **Observed-Data Model**, keep the included observed UCI row, and run the
   seven-class steel-fault classifier.
4. Show `real_models/evidence/real_model_report.json` for locked-test metrics,
   confusion matrices, dataset hashes and licenses.
5. Explain that the language layer routes requests while calculators and trained
   models perform bounded work.

## Defensible summary

The project is a hybrid manufacturing engineering copilot. It integrates
deterministic engineering calculations, traceable document retrieval and two
models trained on 3,508 observed public manufacturing records. The steel model
reaches 80.39% macro-F1 on a locked test. The SECOM risk model reaches 79.64%
ROC-AUC but only 28.04% failure F1, showing that rare-failure detection remains
the main weakness. The results are public-dataset benchmarks, not proof of
cross-plant deployment readiness.

## Likely questions

**Is this an LLM?** The current release is a small hybrid prototype. Natural
language routing is conservative; calculations and observed-data predictions are
handled by auditable tools. A local SLM/LLM can later improve explanations and
document interaction without becoming the source of engineering numbers.

**Is the data real?** Yes. Active model training uses UCI Steel Plates Faults
and UCI SECOM observed manufacturing records. Both sources have DOI and CC BY 4.0
licensing. Raw archive hashes are recorded in the evidence report.

**Why is the accuracy not 100%?** A credible unseen test contains difficult and
ambiguous cases. Reporting error by class is more informative than promising an
unrealistic perfect result.

**What is missing?** A grouped machine/time/site holdout from the intended plant,
confidence intervals, engineering error review, and a frozen external replication.
