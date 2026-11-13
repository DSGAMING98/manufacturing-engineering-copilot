# Manufacturing Engineering Copilot — Detailed Project Report

## 1. Project overview

**Project title:** LLM-Based Manufacturing Engineering Copilot for Design,
Production, Quality, and Maintenance

**Objective:** Build a domain-focused assistant that accepts manufacturing
engineering requests in natural language, routes them to a suitable engineering
workflow, performs reproducible calculations, retrieves registered documentary
evidence, and produces traceable results.

The implemented system is a hybrid architecture. Language-model experiments are
used for bounded intent classification and document-excerpt selection. Exact
engineering calculations are implemented as deterministic Python functions.
This separation prevents a probabilistic model from changing numerical limits,
inspection decisions, or source citations.

## 2. Problem statement

Manufacturing engineers work across design calculations, machining estimates,
production monitoring, dimensional inspection, equipment reliability,
documentation, and procedure lookup. These tasks are usually distributed across
separate spreadsheets, calculators, documents, and software systems. A useful
copilot must understand the request, select the correct workflow, validate the
inputs, produce a reproducible result, and expose the evidence behind it.

General-purpose language models can interpret varied wording but may produce
incorrect arithmetic or unsupported technical statements. The project therefore
uses an LLM/SLM only where language interpretation is useful and uses verified
code for calculations and validation.

## 3. Implemented capabilities

| Workspace | Implemented capability | Principal output |
|---|---|---|
| Copilot Assistant | Natural-language intent routing and labelled-value extraction | Selected workspace, clarification, or tool result |
| Design Engineering | One-dimensional worst-case hole/shaft fit analysis | Clearance, transition, or interference classification |
| Process Planning | Ideal turning speed, feed, and cutting-time estimate | RPM, feed rate, and theoretical machining time |
| Production Engineering | Overall equipment effectiveness calculation | Availability, performance, quality, and OEE |
| Quality Assurance | Inclusive dimensional-tolerance evaluation | PASS, FAIL, or INSUFFICIENT_DATA |
| Maintenance Analytics | Historical reliability calculation | MTBF, MTTR, and observed availability |
| Technical Documentation | Inspection-record draft generation | Structured traceability record and dimensional result |
| Document Evidence | Registered-document retrieval | Exact excerpt, source identifier, hash, and line range |

## 4. System architecture

```text
Browser / CLI
      |
      v
Natural-language assistant or direct workspace selection
      |
      +-- conservative intent router
      |
      +-- deterministic design calculator
      +-- deterministic process calculator
      +-- deterministic production calculator
      +-- Decimal-based quality engine
      +-- deterministic maintenance calculator
      +-- structured documentation generator
      +-- registered-document BM25 retrieval
      |
      v
Traceable report with status, calculations, evidence, and citations
```

The hosted Vercel application runs the CPU-safe deterministic workflows and the
fictional demonstration document corpus. Local execution can additionally load
the Qwen3 LoRA adapters for model evaluation and bounded routing experiments.

## 5. Algorithms

### 5.1 Worst-case fit analysis

For hole limits `Hmin`, `Hmax` and shaft limits `Smin`, `Smax`:

```text
minimum clearance = Hmin - Smax
maximum clearance = Hmax - Smin
```

- Minimum clearance greater than zero: clearance fit.
- Maximum clearance less than zero: interference fit.
- Otherwise: transition fit.

The calculator validates ordering, numeric format, finite values, and units
before returning a classification.

### 5.2 Turning-process estimate

For cutting speed `Vc` in metres per minute, diameter `D` in millimetres, feed
per revolution `f`, and cut length `L`:

```text
RPM = (1000 × Vc) / (π × D)
feed rate = RPM × f
ideal cutting time = L / feed rate
```

The result is a theoretical single-pass estimate. Inputs that are zero,
negative, non-finite, or internally invalid are rejected.

### 5.3 Overall equipment effectiveness

```text
availability = operating time / planned production time
performance = ideal cycle time × total parts / operating time
quality = good parts / total parts
OEE = availability × performance × quality
```

The implementation rejects impossible states such as negative time, operating
time greater than planned time, good quantity greater than total quantity, or
reported performance above 100 percent.

### 5.4 Dimensional tolerance evaluation

Python `Decimal` is used instead of binary floating point for limit decisions.
For nominal size `N`, symmetric tolerance `t`, and measurement `M`:

```text
lower limit = N - t
upper limit = N + t
PASS when lower limit <= M <= upper limit
FAIL otherwise
```

Asymmetric deviations are also supported. Specification boundaries are
inclusive. Ambiguous fields, duplicate values, mixed tolerance forms,
unsupported units, and non-finite numbers return `INSUFFICIENT_DATA`.

### 5.5 Maintenance indicators

For operating hours `OH`, repair hours `RH`, and recorded failures `F`:

```text
MTBF = OH / F
MTTR = RH / F
observed availability = OH / (OH + RH)
```

When no failures are recorded, MTBF and MTTR are reported as undefined rather
than inventing a value.

### 5.6 Document retrieval

The retrieval pipeline:

1. Loads only manifest-registered UTF-8 `.md` and `.txt` documents.
2. Verifies file path, size, revision metadata, status, and SHA-256 hash.
3. Splits documents into paragraph chunks while retaining line ranges.
4. Tokenizes normalized alphanumeric terms and removes a fixed stop-word list.
5. Ranks chunks with BM25 using `k1 = 1.2` and `b = 0.75`.
6. Requires term overlap, query coverage, and a minimum score.
7. Returns the exact excerpt with source and line references or abstains.

### 5.7 Tool routing

The routing task has seven labels: `design`, `process`, `production`, `quality`,
`maintenance`, `documentation`, and `knowledge`. The model must return exactly
one allowlisted line such as `Tool: quality`. It is not trained to perform the
engineering calculation itself.

## 6. Model development

### 6.1 Foundation and adaptation

- Foundation: `unsloth/Qwen3-1.7B-unsloth-bnb-4bit`
- Quantization: 4-bit
- Adaptation: QLoRA supervised fine-tuning
- LoRA rank: 8
- LoRA alpha: 16
- Adapted components: attention and MLP projection layers
- Training hardware: NVIDIA RTX 4060 Laptop GPU, 8 GB VRAM
- Optimizer family: 8-bit AdamW
- Training objective: completion-only causal language-model loss

### 6.2 Original inspection-classification experiment

The original task classified synthetic single-dimensional inspection cases as
PASS, FAIL, or INSUFFICIENT_DATA. On the 90-case comparison split:

| Model | Correct | Accuracy | False PASS | False FAIL |
|---|---:|---:|---:|---:|
| Base Qwen3 | 40/90 | 44.44% | 8 | 11 |
| QLoRA V1 | 38/90 | 42.22% | 6 | 3 |
| QLoRA V2 | 59/90 | 65.56% | 1 | 24 |

The once-only V2 test result was 79/120 (65.83%). PASS recall was only 10%, so
the standalone classifier was not used for numerical inspection decisions.
This result directly motivated the deterministic quality engine.

### 6.3 Seven-way routing experiment

The clean routing dataset contains:

| Split | Records | Per class |
|---|---:|---:|
| Training | 1,050 | 150 |
| Validation | 140 | 20 |
| Synthetic test | 210 | 30 |
| Manual development challenge | 35 | 5 |
| Second manually written challenge | 49 | 7 |
| **Total** | **1,484** | — |

The V5 candidate was trained for 140 optimizer steps. Results:

| Evaluation | Correct | Accuracy | Format parse rate |
|---|---:|---:|---:|
| Unique synthetic validation | 140/140 | 100.00% | 100.00% |
| Once-only synthetic test | 208/210 | 99.05% | 100.00% |
| Manual development challenge | 32/35 | 91.43% | 100.00% |
| Frozen second challenge, broader-language candidate | 44/49 | 89.80% | 95.92% |

The manual development challenge had influenced iteration and is therefore not
described as a blind final test. The second challenge was frozen and hashed
before its first evaluation. Knowledge-search wording remained the largest
routing weakness.

## 7. Data validation

The fail-closed router-data validator checks:

- required fields and three-message conversation structure;
- allowlisted gold labels and completion-label agreement;
- balanced label counts in every split;
- non-empty string content;
- unique label/identifier combinations;
- normalized prompt uniqueness across all five files;
- manifest counts and SHA-256 fingerprints;
- provenance fields and engineer-review metadata.

Result: **1,484/1,484 records passed**, with zero normalized duplicate prompts
across the five router files. This is a structural and provenance result. The
synthetic records are not a replacement for independently reviewed plant data.

## 8. Software verification results

| Verification suite | Result |
|---|---:|
| Automated unit and integration tests | 126/126 passed |
| Six-domain hand-authored workflow regressions | 30/30 passed |
| Fictional retrieval regression cases | 16/16 passed |
| Generated tolerance boundary stress cases | 529/529 passed |
| Router-data structural/provenance records | 1,484/1,484 passed |
| Release path audit | Passed |
| GitHub Actions CPU workflow | Passed |

The HTTP suite also tests trusted-host enforcement, origin checks, JSON content
type, request-size limits, security headers, logo delivery, and the hosted API
contract.

## 9. User interface and deployment

The responsive MFG Copilot workbench provides:

- branded navigation for the seven engineering workspaces;
- a natural-language assistant entry point;
- pre-filled examples and example-request shortcuts;
- validated input fields for direct workflow execution;
- calculation state and result status;
- traceability and citation display;
- responsive desktop and mobile layouts;
- a serverless API with deterministic CPU execution.

Production deployment:
[manufacturing-engineering-copilot.vercel.app](https://manufacturing-engineering-copilot.vercel.app/)

Source repository:
[github.com/DSGAMING98/manufacturing-engineering-copilot](https://github.com/DSGAMING98/manufacturing-engineering-copilot)

## 10. Storage and database status

The prototype processes requests in memory. It does not persist user inputs,
inspection records, accounts, or audit history. Registered document metadata is
stored in repository manifests, and integrity is checked with SHA-256.

A production implementation would require an authenticated database with
role-based access, immutable audit events, document revision history, retention
rules, record ownership, backup, recovery, and organization-specific data
governance.

## 11. Current limitations

- Training and evaluation language is primarily synthetic.
- No independent plant dataset or external engineering review is included.
- Fit analysis is one-dimensional and does not implement complete tolerance
  stacks, GD&T, FEA, or official ISO fit selection.
- Turning output is an ideal estimate and does not incorporate machine, tool,
  material, coolant, or safety constraints.
- Quality evaluation covers one stated characteristic and does not include
  measurement uncertainty, calibration status, sampling plans, or batch release.
- Maintenance calculations are retrospective, not predictive remaining-life
  models.
- The hosted evidence corpus is fictional and intended for demonstration.
- Local QLoRA weights are not committed to GitHub or loaded by the hosted app.

## 12. Recommended next development phase

1. Collect authorized and de-identified engineering requests from each domain.
2. Establish subject-matter-expert annotation and disagreement resolution.
3. Split evaluation by source, product family, and time to reduce leakage.
4. Build a new independently controlled manual challenge after model selection.
5. Improve knowledge/documentation routing with more diverse negative examples.
6. Evaluate macro-F1, per-class precision/recall, calibration, and abstention.
7. Introduce authenticated document management and audit storage.
8. Add organization-specific retrieval sources with revision approval workflow.
9. Conduct usability testing with design, production, quality, and maintenance
   engineers.
10. Define acceptance criteria separately for each workflow before any pilot.

## 13. Conclusion

The project demonstrates a complete manufacturing engineering copilot
architecture rather than a standalone chatbot. It combines bounded language
understanding, deterministic calculations, strict input validation, traceable
document retrieval, responsive web delivery, reproducible testing, and honest
model evaluation. The strongest result is the system design: probabilistic
language interpretation is separated from calculations and evidence that must
remain reproducible.
