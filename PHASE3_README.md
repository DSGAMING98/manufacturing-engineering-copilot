# Manufacturing Copilot · Phase 3

Phase 3 contains the reproducible dataset, validation, training, and comparison
pipeline for the QLoRA experiments. Run all commands from the repository root.
Local environments, checkpoints, and generated results are excluded from Git.

## Exactly what Phase 3 includes

- Reproducible **SYNTHETIC**, programmatically verified quality-assurance examples:
  480 train, 90 validation, 120 held-out synthetic test. Balanced 3-way labels.
- Separate **36 hand-authored** numerical boundary and refusal regression cases:
  12 PASS, 12 FAIL, 12 INSUFFICIENT_DATA. These are NOT independently engineer-reviewed.
- Dataset schema, integrity, SHA256, label, duplicate, and split-isolation checks.
- CPU-only Phase 2 hybrid challenge evaluation with per-class accuracy, false accepts,
  false rejects, missing-evidence handling and abstention rate.
- Qwen3-1.7B 4-bit QLoRA **V2 training** script compatible with the working Phase 1
  Unsloth/TRL stack. Loads the same **BASE** checkpoint, does NOT continue from V1.
- Separate base, V1 and V2 **model-only** evaluation on the SAME Phase 3 split.
  Metrics are saved under `results/phase3/` with dataset hash verification.

### Research honesty

The datasets in this ZIP are synthetic (690 rule-generated rows) and author-written
(36 challenge rows). Neither is real production data, engineer-reviewed standards
material, or evidence of industrial model generalization. The Phase 2 decision
engine has not been expanded to cover GD&T, gauge uncertainty, process capability,
calibration, sampling, or unattended QA. No autonomous product acceptance.

## Run from PowerShell

Activate the project virtual environment and run these commands from the
repository root.

### 1. Offline data and integration checks

```powershell
.\.venv\Scripts\python.exe -m phase3.validate_data
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m phase3.benchmark
```

Expected: dataset schemas pass; current Phase 2 hybrid passes the 36 human-authored
regression scenarios. It is a limited local regression suite, NOT a 100% manufacturing
accuracy claim. There is no GPU load for these three commands.

### 2. Evaluate BASE model on Phase 3 validation (GPU)

```powershell
.\.venv\Scripts\python.exe -m phase3.evaluate_model --split validation --tag base
```

### 3. Evaluate your *existing* V1 adapter on the same validation split (GPU)

```powershell
.\.venv\Scripts\python.exe -m phase3.evaluate_model --split validation --adapter models/qa_qlora/adapter --tag v1
```

### 4. Check the V2 GPU training path with two optimizer steps

```powershell
.\.venv\Scripts\python.exe -m phase3.train_v2 --smoke
```

This saves to **models/qa_qlora_v2_smoke/adapter** only. If you already ran this
once, it refuses to overwrite that adapter.

### 5. Train V2 from the base foundation model (GPU)

```powershell
.\.venv\Scripts\python.exe -m phase3.train_v2
```

The configured starting run has 120 optimizer steps and saves to
**models/qa_qlora_v2/adapter**. This is intended as a first training experiment,
not a final model. It does NOT modify the Phase 1 V1 adapter. If V2 already exists,
training refuses to overwrite it to protect experiment records.

### 6. Evaluate and compare on validation (GPU)

```powershell
.\.venv\Scripts\python.exe -m phase3.evaluate_model --split validation --adapter models/qa_qlora_v2/adapter --tag v2
.\.venv\Scripts\python.exe -m phase3.compare --split validation
```

Only compare results that have the same SHA256 dataset fingerprint. Look at PASS
recall and false rejection counts, not just overall accuracy. If V2 is worse,
keep V1 and inspect predictions before tuning. Never claim that more steps always help.

### 7. One-time final test evaluation (GPU, once V2 is selected)

```powershell
.\.venv\Scripts\python.exe -m phase3.evaluate_model --split test --adapter models/qa_qlora_v2/adapter --tag v2 --confirm-final-test
```

Optional base and V1 test evaluations for a like-for-like comparison:

```powershell
.\.venv\Scripts\python.exe -m phase3.evaluate_model --split test --tag base --confirm-final-test
.\.venv\Scripts\python.exe -m phase3.evaluate_model --split test --adapter models/qa_qlora/adapter --tag v1 --confirm-final-test
.\.venv\Scripts\python.exe -m phase3.compare --split test
```

**Avoid using the final test results to select hyperparameters.** If you want to
improve performance after seeing test errors, collect a fresh untouched test set.

### Regenerate the exact synthetic dataset (only if necessary)

The dataset is already included; you do NOT need to regenerate it. Rebuild the
same source records and SHA256 fingerprints with:

```powershell
.\.venv\Scripts\python.exe -m phase3.generate_data --force
.\.venv\Scripts\python.exe -m phase3.validate_data
```

Regeneration is deterministic given code and config, but modifying code or
configuration may change data hashes and invalidate comparisons.

## Roadmap after this package

- Gather authorized, provenance-tracked real QA inspection cases (not simulated).
- Have subject-matter experts verify drawings, tolerances, outcomes and references.
- Create an independently held-out evaluation set split by manufacturing source,
  product and time, not merely by random rows.
- Build approved-document RAG with page-level citations and refusal for unsupported standards.
- Extend beyond single-dimension QA only after trustworthy evaluation.

For the curation process, see `phase3/REAL_DATA_GUIDE.md`.

## Tool-routing adapter improvement

The promoted local adapter now solves a safer and broader task: select one of
seven bounded capabilities without performing the calculation itself. This
aligns the model with the six-domain project statement while keeping engineering
arithmetic in deterministic code.

```powershell
.\.venv\Scripts\python.exe -m phase3.generate_router_data
.\.venv\Scripts\python.exe -m phase3.train_router --max-steps 100 --output-dir models/router_qlora_v2
.\.venv\Scripts\python.exe -m phase3.evaluate_router --adapter models/router_qlora_v2/adapter --split validation --tag router_v2
.\.venv\Scripts\python.exe -m phase3.evaluate_router --adapter models/router_qlora_v2/adapter --split test --tag router_v2_final --confirm-final-test
.\.venv\Scripts\python.exe -m phase3.build_router_challenge
.\.venv\Scripts\python.exe -m phase3.evaluate_router --adapter models/router_qlora_v2/adapter --split manual_challenge --tag router_v2_challenge
```

Observed results: 93.57% validation, 100% locked synthetic test, and 85.71%
on the post-training manual challenge. The perfect template test is not an
industrial claim; challenge knowledge-search recall was only 40%. See
`phase6/evidence/router_v2_evaluation.json` for fingerprints and per-class
metrics. Adapter weights remain local and gitignored.

### Clean-data follow-up (V5 candidate)

The follow-up dataset contains 1,050 train, 140 validation, 210 test, 35 manual
development-challenge, and 49 second-challenge records. Run the fail-closed
validator before training:

```powershell
.\.venv\Scripts\python.exe -m phase3.validate_router_data
.\.venv\Scripts\python.exe -m phase3.train_router --max-steps 140 --output-dir models/router_qlora_v5_unique
.\.venv\Scripts\python.exe -m phase3.evaluate_router --adapter models/router_qlora_v5_unique/adapter --split validation --tag router_v5_unique
```

Observed V5 results were 140/140 synthetic validation, 208/210 once-only
synthetic test, and 32/35 on the already tuning-exposed manual development
challenge. The second manually written challenge was frozen before evaluation;
a broader-language V3 candidate scored 44/49 (89.80%). Do not tune on that score
and continue calling the set untouched. Full evidence is in
`phase6/evidence/router_v5_evaluation.json`.
