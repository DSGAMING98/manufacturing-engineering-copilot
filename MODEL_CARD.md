# Model Card: Qwen3-1.7B QLoRA Manufacturing Copilot Research Adapters

## Status

Several locally trained research adapters were produced using an NVIDIA RTX
4060 Laptop GPU. The source repository contains **training code and public metric
summaries, not weights**. The original QA-decision adapters remain documented
because their failure modes motivated a safer tool-routing objective.

## Foundation and adaptation

- Base: `unsloth/Qwen3-1.7B-unsloth-bnb-4bit`.
- Method: 4-bit QLoRA supervised fine-tuning, r=8, alpha=16.
- V1: initial 72/18/24 synthetic train/validation/test examples, short 24-step pilot.
- V2: independent training from the foundation on 480/90/120 synthetic train/validation/test examples, configured 120 steps.
- Data: rule-generated single-dimensional inspection scenarios with PASS, FAIL, and INSUFFICIENT_DATA labels; not collected from an industrial plant.
- Learning objective: structured-format reasoning/explanation for laboratory QA scenarios, **not** unrestricted engineering authorization.

### Promoted routing adapter

- Task: select `design`, `process`, `production`, `quality`, `maintenance`,
  `documentation`, or `knowledge`; it does not calculate.
- Data: 700 balanced synthetic training requests, 140 validation requests, and a
  locked 210-request synthetic test using split-specific templates.
- Training: QLoRA from the same Qwen3-1.7B foundation, r=8, alpha=16, 100 steps.
- Validation: 131/140 (93.57%), with 90%–100% recall in every class.
- Locked synthetic test: 210/210 (100%; Wilson 95% interval 98.20%–100%).
- Post-training manual challenge: 30/35 (85.71%; Wilson 95% interval
  70.62%–93.74%). Knowledge-search recall was only 40% on this small challenge.

The perfect synthetic test indicates that the adapter learned the bounded
templates. It is not industrial accuracy. The manual challenge is the more
realistic warning that generalization remains incomplete. Full evidence and
dataset fingerprints are in `phase6/evidence/router_v2_evaluation.json`.

### Clean unique-data routing run (V5 candidate)

The follow-up run expanded training to 1,050 balanced requests and regenerated
140 validation and 210 test requests with zero duplicate user prompts across
all router files. A fail-closed validator checks 1,484/1,484 records for schema,
labels, completion agreement, balance, identities, prompt uniqueness, manifest
counts, hashes, and review metadata. This is **100% structural/provenance data
validation**, not proof that every synthetic statement is factually correct.

V5 used 4-bit QLoRA (r=8, alpha=16) for 140 optimizer steps. It scored 140/140
on the unique synthetic validation split and 208/210 (99.05%) on the once-only
synthetic test. Its harder 35-request development challenge score was 32/35
(91.43%) with the explicit production routing prompt. Because that challenge
influenced development, it is not a blind final test. A broader candidate was
evaluated once against a second, frozen 49-request manually written set and
scored 44/49 (89.80%); knowledge and quality wording remained the weak areas.

Adding challenge answers to training could manufacture 35/35, but would measure
memorization rather than generalization. The complete protocol and hashes are
in `phase6/evidence/router_v5_evaluation.json`. Weights remain local and
gitignored.

## Observed model-only validation: Phase 3 (same 90 synthetic examples)

| Model | Correct | Accuracy | False PASS | False FAIL |
|---|---:|---:|---:|---:|
| Base | 40 | 44.44% | 8 | 11 |
| V1 | 38 | 42.22% | 6 | 3 |
| V2 | 59 | 65.56% | 1 | 24 |

Source: recorded Phase 3 evaluation output with matching dataset fingerprint `593151a2bff088f15507f3aa839bc276fa13cb8b53c92e05df3852952933c7ea`. These numbers describe synthetic validation, **not** real-world machine/quality reliability. V2's 24 false rejections are substantial, and the standalone model must not decide whether parts are accepted or rejected.

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

Use `phase5.web_app` for tool-first six-domain workflows. The hosted assistant
uses a deterministic conservative router because model weights are not deployed.
The local routing adapter may select a tool, but may **not** change computed
decisions, manufacture input values, or fabricate standards. Numeric answers
come from `src.tolerance_engine` and `phase5.calculators`.

## Known failure modes

- Standalone SLM gave `FAIL` for `nominal=20.00, tolerance=±0.05, measured=20.03`, when the correct dimensional answer is `PASS`.
- Unsupported ISO standards citations can be hallucinated by standalone generation.
- Synthetic training templates may teach brittle patterns and bias toward rejecting valid measurements.
- No verified cross-domain engineering reasoning, procedural compliance, live MES/SCADA data, calibrated measurement devices, or operator approval.
- Tool-routing knowledge-search recall fell to 40% on the 35-prompt manual challenge.

## Intended and prohibited use

**Intended:** Education, demonstration, synthetic model comparison, deterministic arithmetic and extraction from permission-cleared documents in a local environment.

**Prohibited without independent validation and human approval:** Product release, automated machining, equipment control, maintenance-safety decisions, standards certification, worker-safety decisions, or use as sole engineering decision-maker.

## Reproducibility and disclosures

See `configs/phase3_v2.json`, `phase3/REAL_DATA_GUIDE.md`, `phase3/validate_data.py`, `phase6/evidence/`, `docs/PAPER_FIGURE_NOTES.md`, and `PHASE6_README.md`. Any adapter publication must comply with the foundation-model license and the applicable dataset terms.
