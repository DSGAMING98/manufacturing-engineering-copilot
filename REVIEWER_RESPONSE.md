# Supervisor-review response and reproducibility checklist

**Status (14 November 2026):** Export verification, five baselines for each UCI task, repeated stratified CV and a 125-prompt developer-authored router diagnostic were **executed successfully** in [GitHub Actions run 43568404827](https://github.com/DSGAMING98/manufacturing-engineering-copilot/actions/runs/43568404827). Human-user, independent retrieval relevance and cross-plant studies remain unperformed.

**Research positioning:** MFG Workbench (legacy repository name: MFG Copilot) is a traceable manufacturing decision-support workbench. Its deployed request router is a deterministic keyword-and-field parser, not a running Qwen language model. The active ML experiments use Random Forest for UCI Steel Plates Faults and Extra Trees for UCI SECOM.

| Reviewer concern | Concrete change | Status |
|---|---|---|
| Known UCI benchmarks, no controls | Added real_models/benchmark_baselines.py with majority-class, logistic regression, RBF SVM, kNN and gradient boosting | Executed; recorded metrics linked below |
| One random split | Added repeated stratified cross-validation on the development partition | Executed: 3 folds x 2 repeats, 5 baselines per task |
| Paired tests | Added paired correctness checks (exact McNemar-style binomial test) versus incumbent | Does not test AUC or F1 directly |
| JSON export parity | Added real_models/verify_export.py to compare the original forest with deployment on all 389 test records and all class probabilities | **PASS:** 389/389 class labels, maximum probability delta 4.9984e-7 |
| Router and refusal evidence | Added real_models/review_diagnostics.py containing 105 domain prompts and 20 unsupported/ambiguous probes | **114/125 correct (91.2%)**; 20/20 unsupported prompts refused; not externally validated |
| Retrieval effectiveness | Diagnostic records source inventory but intentionally does not invent relevance judgements | Relevance-labelled query set needed for hit@k |
| Usability | Plan a 5-10 participant, consented SUS study | No study or SUS result yet |
| 27-feature public form | Explicitly describe as a numeric-feature demonstration | External vision/metrology feature pipeline not implemented |
| LLM branding | Rename paper to decision-support workbench, remove irrelevant QLoRA literature | Updated IEEE manuscript available separately |
| Prior art | Verify two relevant Steel Plates Faults classifier papers | Different splits prevent direct accuracy ranking |
| Questioned bibliography | Maghanaki 2026 and Hoang 2026 journal articles verified by DOI | Verified; may omit if not pertinent to software research |
| Mixed plot | Split steel and SECOM metric summaries; enlarge dataset-split legend | Updated IEEE manuscript available separately |

## Measured follow-up results (same existing test partitions)

**Steel classifier (389 test rows; 3-fold x 2-repeat CV on development records; CV metric macro-F1)**

| Method | CV F1 mean ± SD | Existing-test accuracy | Existing-test macro-F1 | Exact paired McNemar p |
|---|---:|---:|---:|---:|
| Majority | 0.0735 ± 0.0002 | 0.3470 | 0.0736 | 1.02e-33 |
| Logistic regression | 0.6673 ± 0.0068 | 0.6581 | 0.6467 | 1.95e-9 |
| RBF SVM | 0.7295 ± 0.0121 | 0.7172 | 0.7378 | 8.77e-5 |
| 11-NN | 0.7076 ± 0.0252 | 0.7069 | 0.6883 | 1.69e-5 |
| Gradient boosting | 0.7818 ± 0.0141 | 0.7738 | 0.7750 | **0.126** |
| Released 300-tree RF | not measured by repeated CV | **0.8021** | **0.8039** | reference |

**SECOM classifier (314 test rows; CV metric ROC-AUC)**

| Method | CV AUC mean ± SD | Existing-test ROC-AUC | Existing-test failure F1 | Exact paired McNemar p |
|---|---:|---:|---:|---:|
| Majority | 0.5000 ± 0.0000 | 0.5000 | 0.1254 | 8.70e-58 |
| Logistic regression | 0.6298 ± 0.0167 | 0.5612 | 0.1951 | 2.15e-6 |
| RBF SVM | 0.6642 ± 0.0416 | 0.6218 | 0.1346 | 0.165 |
| 11-NN | 0.6151 ± 0.0584 | 0.6650 | 0.1579 | 1.59e-7 |
| Gradient boosting | 0.6861 ± 0.0454 | 0.7534 | 0.0645 | 8.95e-8 |
| Released 600-tree Extra Trees | not measured by repeated CV | **0.7964** | **0.2804** | reference |

**Export integrity:** The original lightweight forest export lost precision by rounding thresholds and not matching sklearn's float32 inference inputs. Both were corrected. After retraining and exporting, the JSON implementation and original sklearn model agreed on **all 389/389 test labels**; the maximum absolute discrepancy among seven class probabilities was **4.9984e-7**, below the specified **1e-6** tolerance. The corrected deployed artifact was committed by GitHub Actions.

**Request router:** 114/125 developer-authored prompts routed as expected (91.2%); 20/20 unsupported prompts refused. This is a development diagnostic, **not independently labelled operator accuracy**. Retrieval hit@k and SUS have not been measured.

**Important statistical limits:** McNemar p values are two-sided, unadjusted and compare **paired correctness of thresholded labels**, not F1 or ROC-AUC. On SECOM, the pass-majority can make correctness tests misleading for failure detection. All these baseline comparisons are **post-hoc on an already reported test partition** and do not constitute new external validation.

## Reproduce the reviewer diagnostics

Use Python 3.11/3.12 and the research dependency file.

~~~powershell
cd C:\Users\Prajwal\Desktop\python\manufacturing-copilot
.\.venv\Scripts\python.exe -m pip install -r requirements-research.txt
.\.venv\Scripts\python.exe -m real_models.verify_export
.\.venv\Scripts\python.exe -m real_models.benchmark_baselines --cv-folds 3 --cv-repeats 2
.\.venv\Scripts\python.exe -m real_models.review_diagnostics
~~~

Reports are written under real_models/evidence and uploaded by the GitHub Actions research workflow. The values above come from the successful workflow logs; verify against the attached machine-readable JSON artifacts when preparing a submission.

## Scientific reporting caveats

1. The existing test partitions have already been opened and reported. New baseline comparisons on those same records are **post-hoc**. They are not a second untouched blind evaluation.
2. Developer-authored routing prompts can expose software faults. They are not representative field data; independently labelled real-world manufacturing requests, a retrieval relevance set and a human study remain necessary.
3. No cross-site, cross-machine or time-separated evaluation has been performed.
4. The steel web form needs the original 27 numeric features; an upstream inspection system or feature-extraction bridge is not implemented.

## Journal positioning

SoftwareX is a reasonable software-focused direction, but its journal-specific template and metadata differ from IEEEtran. IEEE Access requires more empirical comparison and software integration evidence. Neither choice guarantees acceptance, and submission must follow its current author and AI-assistance rules.

## Confirmed DOI sources

- Kordatos and Benardos 2022: https://doi.org/10.1504/IJMMS.2022.127211
- Ghasemkhani et al. 2023: https://doi.org/10.3390/machines11070679
- Maghanaki et al. 2026: https://doi.org/10.1007/s00170-026-18711-4
- Hoang et al. 2026: https://doi.org/10.1016/j.ijpe.2026.110091
