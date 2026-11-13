# Submission and Demonstration Guide

## 1. Project statement

**Title:** LLM-Based Manufacturing Engineering Copilot for Design, Production,
Quality, and Maintenance

**Description:** A domain-specific LLM assistant providing intelligent support
for engineering design, process planning, production, quality assurance,
maintenance, and technical documentation.

## 2. What was built

The prototype combines three mechanisms rather than relying on an LLM alone:

1. **Natural-language routing** identifies the intended engineering workspace.
2. **Deterministic engineering tools** calculate fit, turning estimates, OEE,
   dimensional inspection results, and maintenance indicators.
3. **Evidence retrieval** returns excerpts from registered documents with file,
   hash, and line references. The hosted demonstration corpus is fictional and
   clearly labelled.

The six application domains are design engineering, process planning,
production engineering, quality assurance, maintenance analytics, and technical
documentation. Document evidence search is a shared supporting capability.

## 3. Why the architecture is hybrid

A language model is useful for understanding wording and selecting tools, but it
is not a trustworthy calculator or approval authority. Therefore:

- the Qwen3-1.7B LoRA model is used only for bounded classification/routing;
- Python `Decimal` arithmetic is used where exact decimal limits matter;
- all missing or invalid inputs cause a clarification or refusal;
- no workflow can release a product, operate equipment, or claim certification;
- final decisions remain with qualified engineers and authorized QA staff.

This is the central engineering decision in the project: use an LLM for language
understanding and deterministic software for facts that must be reproducible.

## 4. Algorithms implemented

### Design engineering

Worst-case one-dimensional hole/shaft fit:

- minimum clearance = hole minimum − shaft maximum
- maximum clearance = hole maximum − shaft minimum
- both positive: clearance; both negative: interference; otherwise: transition

### Process planning

Idealized turning estimates:

- spindle speed: `RPM = 1000 × cutting speed / (π × diameter)`
- feed rate: `feed per revolution × RPM`
- cutting time: `cut length / feed rate`

The result is an estimate, not a machine-ready parameter set.

### Production engineering

Overall equipment effectiveness:

- availability = run time / planned production time
- performance = ideal cycle time × total parts / run time
- quality = good parts / total parts
- OEE = availability × performance × quality

Impossible combinations, such as good parts greater than total parts, are
rejected.

### Quality assurance

Inclusive dimensional limits:

- symmetric: lower = nominal − tolerance; upper = nominal + tolerance
- asymmetric: lower = nominal + lower deviation; upper = nominal + upper deviation
- PASS when lower ≤ measurement ≤ upper; otherwise FAIL

The result covers one stated dimension only, not full part or lot release.

### Maintenance analytics

Historical reliability indicators:

- MTBF = operating hours / recorded failures
- MTTR = repair hours / recorded failures
- observed availability = MTBF / (MTBF + MTTR)

These are retrospective indicators, not remaining-useful-life predictions.

### Technical documentation

The system validates identifiers and timestamps, runs the dimensional check,
and creates a `DRAFT` inspection record containing traceability fields and a
`PENDING_COMPLETION` workflow status.

### Document evidence

The retrieval pipeline verifies registered document hashes, chunks approved text
with line ranges, scores query/chunk token overlap, and returns extractive
evidence with citations. If no supported source is found, it abstains.

## 5. Data and model training

- Foundation model: Qwen3-1.7B, loaded in 4-bit form for local training.
- Adaptation method: QLoRA with low-rank adapters.
- Original experiment: single-dimensional PASS/FAIL/INSUFFICIENT_DATA reporting.
- Improved experiment: seven-way tool routing across the six domains plus
  evidence search.
- Training data: deterministic synthetic templates with balanced labels.
- Split policy: separate prompt templates for training, validation, and test.
- Model weights are intentionally not committed to GitHub because they are large.

Synthetic accuracy demonstrates software behavior on the defined task. It does
not establish industrial validity; plant data and independent engineering review
are still required.

Observed routing results are 131/140 (93.57%) on validation, 210/210 on the
locked synthetic test, and 30/35 (85.71%) on a separately written challenge.
The challenge exposed only 40% recall for knowledge-search routing, so that area
remains a documented improvement target. Present all three results together;
do not describe the 100% synthetic score as industrial accuracy.

The clean-data follow-up removed duplicate prompts and verifies 1,484/1,484
records structurally, including hashes and cross-split isolation. V5 scored
140/140 on its unique synthetic validation split, 208/210 on its once-only
synthetic test, and 32/35 on the manual challenge already used during
development. A broader candidate scored 44/49 on a second manually written set
frozen before evaluation. For the presentation, call 100% the **data integrity
check and bounded synthetic validation result**, never 100% real-world model
accuracy. The manually written result is the more important generalization
warning.

## 6. Validation strategy

The repository contains unit, regression, HTTP, retrieval, routing, and release
tests. Validation checks include:

- correct calculations and inclusive boundary cases;
- refusal of missing, malformed, non-finite, or contradictory values;
- balanced per-class model metrics, not only overall accuracy;
- false-acceptance and false-rejection counts;
- fixed held-out test data evaluated only after validation selection;
- document integrity and citation provenance;
- live deployment page, assets, health endpoint, and calculation endpoint.

### Real manufacturing data path

Phase 7 implements the real-data transition without committing industrial
records. It validates written permission references, completed ethics status,
de-identification, source and dataset hashes, two independent reviewer labels,
adjudication, duplicate requests, and product/site/machine/time grouping. It
then creates group-isolated splits, a private SQLite research store, and routing
metrics with confidence intervals and confusion matrices.

The committed readiness status is `REAL_DATA_REQUIRED` because no authorized
plant records have been supplied. Until the readiness report is regenerated
from such records, present the current numerical model results as synthetic
research results, not industrial validation. See
`phase7/REAL_DATA_PROTOCOL.md` and `IEEE_READINESS.md`.

## 7. Recommended live demonstration

Open the [live workbench](https://manufacturing-engineering-copilot.vercel.app/).

1. In **Copilot Assistant**, submit:
   `Check quality: nominal=20, measured=20.03, tolerance=0.05, unit=mm`
2. Show that it routes to quality and produces PASS with exact limits.
3. Change the measurement to `20.09` and show FAIL.
4. Submit `Calculate OEE with planned time=480 and run time=420` and show that
   the assistant requests the missing cycle time, total parts, and good parts.
5. Open **Document Evidence** and ask:
   `What identifiers belong in an inspection record for traceability?`
6. Explain that the hosted documents are fictional examples and the output is an
   excerpt with citations, not an invented procedure.

## 8. What to say if asked “Is this production-ready?”

No. It is a validated research prototype. The deterministic functions and
software controls are tested, but production use requires organization-specific
requirements, approved source documents, real historical datasets, calibration
and access controls, cybersecurity review, human-factor testing, and independent
engineering validation.

## 9. Likely viva questions

**Why use an LLM at all?**  To interpret varied wording, route tasks, and help
retrieve evidence. Exact arithmetic stays outside the LLM.

**Why QLoRA?**  It trains a small number of adapter parameters on limited GPU
memory while keeping the foundation model frozen.

**Why not report only accuracy?**  A model can hide dangerous behavior behind a
good average. Per-class recall and false acceptances reveal whether it misses
FAIL or insufficient-evidence cases.

**Where is the database?**  Persistence is intentionally not part of this
prototype. Inputs and reports are processed in memory. A production system would
need an authenticated, access-controlled audit store with retention policies.

**What is the main limitation?**  Training and evaluation data are synthetic.
Independent industrial validation has not been completed.

**What is the main contribution?**  A transparent hybrid architecture that
combines language understanding, deterministic engineering tools, evidence
retrieval, fail-closed validation, and reproducible testing across six domains.
