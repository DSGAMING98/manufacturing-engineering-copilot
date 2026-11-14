# Supervisor-review response and reproducibility checklist

**Status:** Reviewer scripts have been committed to the project. Comparative results, export agreement, and independent user studies must be measured before making new numerical claims.

**Research positioning:** MFG Copilot is a traceable manufacturing decision-support workbench. Its deployed request router is a deterministic keyword-and-field parser, not a running Qwen language model. The active ML experiments use Random Forest for UCI Steel Plates Faults and Extra Trees for UCI SECOM.

| Reviewer concern | Concrete change | Status |
|---|---|---|
| Known UCI benchmarks, no controls | Added real_models/benchmark_baselines.py with majority-class, logistic regression, RBF SVM, kNN and gradient boosting | Code committed; scores pending |
| One random split | Added repeated stratified cross-validation on the development partition | Code committed; results pending |
| Paired tests | Added paired correctness checks (exact McNemar-style binomial test) versus incumbent | Does not test AUC or F1 directly |
| JSON export parity | Added real_models/verify_export.py to compare the original forest with deployment on all 389 test records and all class probabilities | Code committed; execution pending |
| Router and refusal evidence | Added real_models/review_diagnostics.py containing 105 domain prompts and 20 unsupported/ambiguous probes | Developer-authored diagnostics, not an expert-labelled independent benchmark |
| Retrieval effectiveness | Diagnostic records source inventory but intentionally does not invent relevance judgements | Relevance-labelled query set needed for hit@k |
| Usability | Plan a 5-10 participant, consented SUS study | No study or SUS result yet |
| 27-feature public form | Explicitly describe as a numeric-feature demonstration | External vision/metrology feature pipeline not implemented |
| LLM branding | Rename paper to decision-support workbench, remove irrelevant QLoRA literature | Updated IEEE manuscript available separately |
| Prior art | Verify two relevant Steel Plates Faults classifier papers | Different splits prevent direct accuracy ranking |
| Questioned bibliography | Maghanaki 2026 and Hoang 2026 journal articles verified by DOI | Verified; may omit if not pertinent to software research |
| Mixed plot | Split steel and SECOM metric summaries; enlarge dataset-split legend | Updated IEEE manuscript available separately |

## Reproduce the reviewer diagnostics

Use Python 3.11/3.12 and the research dependency file.

~~~powershell
cd C:\Users\Prajwal\Desktop\python\manufacturing-copilot
.\.venv\Scripts\python.exe -m pip install -r requirements-research.txt
.\.venv\Scripts\python.exe -m real_models.verify_export
.\.venv\Scripts\python.exe -m real_models.benchmark_baselines --cv-folds 3 --cv-repeats 2
.\.venv\Scripts\python.exe -m real_models.review_diagnostics
~~~

New local JSON reports are placed under real_models/evidence. Check execution logs and report contents before including the numbers in a paper. Do not claim full export parity or a model superiority result before running the code.

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
