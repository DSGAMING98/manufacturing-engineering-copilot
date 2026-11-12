# Paper-ready figure notes and claim boundaries

Do **not** describe synthetic test scores as verified industrial manufacturing accuracy.
These are the *same Phase 3 synthetic validation set* for all three model-only models.
The V1 Phase 1 curves and metrics come from a **different training dataset** and
must not be conflated with the Phase 3 dataset.

## Figure 1. Three-way model-only synthetic validation accuracy

- Base Qwen3-1.7B: 40/90 = **44.44%**.
- V1 QLoRA: 38/90 = **42.22%**.
- V2 QLoRA: 59/90 = **65.56%**.
- Error bars = unpaired **Wilson 95% binomial intervals** for each model.
  They illustrate sampling uncertainty but do **not** establish a significant
  paired V2 improvement. Significance analysis needs example-level paired predictions.
- Dataset: Phase 3 rule-generated synthetic validation; `n=90`,
  SHA256 `593151a2bff088f15507f3aa839bc276fa13cb8b53c92e05df3852952933c7ea`.
- Source: operator-provided console summary; local JSON files override if available
  and only if all split/hash/count consistency checks pass.

**Suggested caption:** “Decision-label accuracy of base Qwen3-1.7B and two
QLoRA adaptations on 90 synthetic dimensional-inspection validation cases.
Intervals are Wilson 95% binomial intervals. These results do not represent
industrial deployment performance.”

## Figure 2. False PASS/FAIL tradeoffs

- False PASS counts: **8 base**, **6 V1**, **1 V2** (gold FAIL, prediction PASS).
- False FAIL counts: **11 base**, **3 V1**, **24 V2** (gold PASS, prediction FAIL).
- Other error categories are excluded from these two bars, so their sums are
  not the total model mistakes.

**Suggested caption:** “Error-mode counts on the same synthetic Phase 3 validation
set. V2 makes fewer false acceptances, but more false rejections. The deterministic
inspection engine is therefore used for numerical PASS/FAIL decisions.”

## Figure 3. V1 loss curve

- 24 optimizer-step losses and three evaluation losses extracted from the
  user-provided local 2026-11-12 Unsloth terminal log.
- This is **Phase 1**, using **72 synthetic training and 18 validation examples**.
- Loss is a fitting diagnostic, not a direct measure of engineering reliability.

**Suggested caption:** “Observed Phase 1 QLoRA training and validation losses for
Qwen3-1.7B on small synthetic dimensional-inspection data (separate from the
Phase 3 evaluation population).”

## Optional Figure 4. V2 loss curve

Run on the local PyCharm project after V2 training:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-phase6.txt
.\.venv\Scripts\python.exe -m phase6.plot_results
```

`phase6.plot_results` searches for an actual
`models/qa_qlora_v2/checkpoint-*/trainer_state.json` file and plots its
`log_history` if available. It **does not fabricate** V2 losses in its absence.
If checkpoints were deleted, obtain the actual trainer log if one was saved,
or omit the V2 learning curve.

## Technical scope and limitations (do not omit)

- Qwen3-1.7B 4-bit QLoRA is trained as a *standalone* model on rule-generated QA
  examples, not a validated industrial domain specialist.
- The six-domain Phase 5 interface uses deterministic calculators, structured
  refusal handling and extractive document search. It is not six specialized SLMs.
- RAG examples in the repository are **fictional demo documents**.
  Approved-labelled documents are operator-declared and not independently audited.
- The local dashboard has no identity/authentication, audit-log database, machine
  integrations, automated part release or production safety certification.
- Report training setup, model versions, data hashes, and verification harness;
  do not assert expert review that never happened.
- Future study: expert-designed real cases, task-wise coverage, paired sample error
  analysis, new-source RAG verification, security evaluation, and operator studies.

## Accuracy vs regression performance

A CPU-only 529-case tolerance grid checks **software arithmetic consistency**,
not AI generalization. Likewise the 30-case Phase 5 tool regression and Phase 4
fictional-document retrieval checks are developer tests, **not factory accuracy**.
