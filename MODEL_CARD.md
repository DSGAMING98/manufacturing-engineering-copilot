# Model Card: Qwen3-1.7B QLoRA Manufacturing QA Research Adapters

## Status

Two locally trained research adapters, **V1** and **V2**, were produced by an operator using an NVIDIA RTX 4060 Laptop GPU. The source archive contains **training code**, not weights. This card documents limited, synthetic evaluation evidence and cannot substitute for model inspection, hardware audit, or industrial validation.

## Foundation and adaptation

- Base: `unsloth/Qwen3-1.7B-unsloth-bnb-4bit`.
- Method: 4-bit QLoRA supervised fine-tuning, r=8, alpha=16.
- V1: initial 72/18/24 synthetic train/validation/test examples, short 24-step pilot.
- V2: independent training from the foundation on 480/90/120 synthetic train/validation/test examples, configured 120 steps.
- Data: rule-generated single-dimensional inspection scenarios with PASS, FAIL, and INSUFFICIENT_DATA labels; not collected from an industrial plant.
- Learning objective: structured-format reasoning/explanation for laboratory QA scenarios, **not** unrestricted engineering authorization.

## Observed model-only validation: Phase 3 (same 90 synthetic examples)

| Model | Correct | Accuracy | False PASS | False FAIL |
|---|---:|---:|---:|---:|
| Base | 40 | 44.44% | 8 | 11 |
| V1 | 38 | 42.22% | 6 | 3 |
| V2 | 59 | 65.56% | 1 | 24 |

Source: operator's shared Phase 3 console comparison, with matching dataset fingerprint `593151a2bff088f15507f3aa839bc276fa13cb8b53c92e05df3852952933c7ea`. These numbers describe synthetic validation, **not** real-world machine/quality reliability. V2's 24 false rejections are substantial, and the standalone model must not decide whether parts are accepted or rejected.

V1 Phase 1 validation on a *different* 18-example synthetic split was 16/18 after tuning vs 15/18 before tuning. V1 Phase 1 test was 22/24. These are **not comparable** with the Phase 3 values without accounting for changed datasets and templates.

## Final held-out synthetic test

After model selection was frozen, V2 was evaluated once on the 120-case Phase 3
test split. It correctly classified 79/120 cases (65.83%; Wilson 95% interval
56.97%–73.71%). Recall was 10.00% for PASS, 87.50% for FAIL and 100.00% for
INSUFFICIENT_DATA, with 3 false acceptances and 22 false rejections. The close
validation/test headline accuracy does not offset the severe PASS-class failure.
See `phase6/evidence/v2_final_test.json`.

Two subsequent local experiments—longer four-line report training and a
label-only classifier objective—did not exceed V2 validation accuracy and were
not promoted.

## Recommended inference configuration

Use `phase5.web_app` for tool-first six-domain workflows. If Qwen is enabled in the Phase 4/5 CLI, it may select among retrieved document excerpts but may **not** change computed decisions or fabricate standards. Preferred verified numeric answer is from `src.tolerance_engine` and `phase5.calculators`.

## Known failure modes

- Standalone SLM gave `FAIL` for `nominal=20.00, tolerance=±0.05, measured=20.03`, when the correct dimensional answer is `PASS`.
- Unsupported ISO standards citations can be hallucinated by standalone generation.
- Synthetic training templates may teach brittle patterns and bias toward rejecting valid measurements.
- No verified cross-domain engineering reasoning, procedural compliance, live MES/SCADA data, calibrated measurement devices, or operator approval.

## Intended and prohibited use

**Intended:** Education, demonstration, synthetic model comparison, deterministic arithmetic and extraction from permission-cleared documents in a local environment.

**Prohibited without independent validation and human approval:** Product release, automated machining, equipment control, maintenance-safety decisions, standards certification, worker-safety decisions, or use as sole engineering decision-maker.

## Reproducibility and disclosures

See `configs/phase3_v2.json`, `phase3/REAL_DATA_GUIDE.md`, `phase3/validate_data.py`, `phase6/evidence/`, `docs/PAPER_FIGURE_NOTES.md`, and `PHASE6_README.md`. Operators must respect the foundation-model license and validate any data before publishing adapters. Cite AI assistance as required by the target venue.
