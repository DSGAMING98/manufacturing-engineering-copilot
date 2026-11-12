# Manufacturing Copilot · Phase 4: Document RAG with traceable excerpts

**Goal:** make the existing Phase 2 verified dimensional engine and Phase 3 fine-tuned Qwen adapter useful with **retrievable, locally registered document excerpts**, without fabricated standards citations.

## Why this architecture

The user's Phase 3 validation comparison (90 synthetic examples) was:

| Model | Accurate | False PASS | False FAIL |
|---|---:|---:|---:|
| Base Qwen | 40/90 (44.44%) | 8 | 11 |
| V1 adapter | 38/90 (42.22%) | 6 | 3 |
| V2 adapter | 59/90 (65.56%) | 1 | 24 |

**V2 improved headline accuracy but still falsely rejected 24 valid cases.** None of these numbers establishes industrial performance. Consequently, no model receives numerical acceptance/release authority.

Phase 4 comprises three separate mechanisms:

1. **Exact arithmetic:** existing `src.hybrid_qa` + `src.tolerance_engine` do single-dimensional calculation with Python `Decimal`. It rejects unsupported or ambiguous cases.
2. **Document retrieval:** `phase4.retrieval` searches your **locally registered `.md` or `.txt` documents** using a transparent BM25-like lexical scorer. It returns **verbatim paragraph excerpts with line-numbered source IDs, revision and a SHA-256 integrity check**.
3. **Optional LoRA SLM:** Qwen3 selects **only one of the retrieved numbered excerpts**. Its output is strictly checked; unsupported responses fall back to retrieval rank. **It cannot write the facts, change the calculated inspection result, or invent citations.** This is a conservative *extractive RAG foundation*, not free-form generative document QA.

There is no external standards library, vector database, search API, background indexing service, or new dependency. Do not call demo excerpts “approved industrial knowledge.”

## Installing into your working PyCharm folder

Extract the ZIP contents directly inside `C:\Users\Prajwal\Desktop\python\manufacturing-copilot` (the project root shown in your log). Merge new folders but **do not remove or overwrite** `.venv/`, `models/`, `results/`, `src/`, `phase3/`, existing tests or saved adapters. Phase 4 ships new files only.

Run from the PyCharm terminal:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m phase4.benchmark
```

Try the document demo **without loading the GPU**:

```powershell
.\.venv\Scripts\python.exe -m phase4.rag_chat --include-demo
```

Ask:

- `How do I handle a dimensional discrepancy and preserve the record?`
- `What identifiers belong in an inspection record for traceability?`
- `nominal=20.00 measured=20.03 tolerance=0.05 unit=mm`
- `What does ISO 9001:2015 require for product release?` (must abstain)

Try the **actual trained V2 adapter** on your RTX 4060 for guarded selection of evidence excerpts:

```powershell
.\.venv\Scripts\python.exe -m phase4.rag_chat --include-demo --adapter models/qa_qlora_v2/adapter
```

If your V2 adapter is missing, omit `--adapter` or use the existing V1 `models/qa_qlora/adapter`. Both use the same safe retrieval/extractive output policy. You may see `max_new_tokens` warnings from Transformers: those are not calculation failures.

## Document approval and citation controls

**By default the only bundled sources are FICTIONAL DEMO documents and are excluded.** This is intentional. Without a registered reviewed source, a document question returns `NO VERIFIED DOCUMENT ANSWER`.

Add your own authorized UTF-8 `.md` or `.txt` files (no PDF parser is included). Example of registering a draft:

```powershell
.\.venv\Scripts\python.exe -m phase4.add_document --source "C:\path\to\your\procedure.md" --id LOCAL-QA-001 --title "Dimensional QA Procedure" --revision "A" --status draft
```

A **draft is not used** to answer questions. After an actual human reviews the approved and permission-cleared document, register it as approved with explicit review metadata (use a **new ID** if a draft was previously registered):

```powershell
.\.venv\Scripts\python.exe -m phase4.add_document --source "C:\path\to\reviewed_procedure.md" --id LOCAL-QA-002 --title "Reviewed Dimensional QA Procedure" --revision "B" --status approved --reviewer "Real Reviewer Name" --approved-date 2026-11-13 --confirm-reviewed
```

Then run without the demo flag:

```powershell
.\.venv\Scripts\python.exe -m phase4.rag_chat
```

**Approval and reviewer identity are operator-provided metadata**. This software cannot verify that review happened. Document source SHA-256 checks only detect file changes after registration, not malicious or inaccurate document contents. Source text and retrieved excerpts are treated as untrusted, not as operational instructions to the system.

Never commit private drawings, plant procedures, customer records or real industrial secrets to a public GitHub/Hugging Face repository. Only process material you have rights to use. PDF manuals need a separately reviewed extraction workflow, not renaming them `.txt`.

## What citations actually mean

Sample demo output includes e.g. `DEMO-NCR-001:L5-L5` with the matching file path and exact excerpt. The cited text genuinely exists at those local line numbers, **but the document itself is deliberately fictional**. The system does **not** claim ISO/ASME/ASTM standards compliance. For credible engineering research, use authorized source versions, human review, and separate independent evaluation.

The retrieval benchmark is a small **toy challenge** over these demo documents. It is intended to detect broken indexing, abstention, and citation behavior, **not to estimate manufacturing accuracy**. On real documents, report retrieval recall@k, citation faithfulness, expert-reviewed answer quality, abstention on unsupported questions, and unsafe recommendations separately from the Phase 3 model-only metrics.

## Phase 4 commands

| Command | What it checks |
|---|---|
| `python -m unittest discover -s tests -v` | All existing + new regression tests, CPU |
| `python -m phase4.benchmark` | Demo retrieval, grounding, refusals, CPU |
| `python -m phase4.rag_chat --include-demo` | Live exact document citations and verified calculations, CPU |
| `python -m phase4.rag_chat --include-demo --adapter models/qa_qlora_v2/adapter` | Same, with Qwen selecting excerpts, GPU |
| `python -m phase4.rag_chat` | Approved-only sources; currently abstains until you add approved files |
| `python -m phase4.add_document --help` | Add a permission-cleared text/markdown source |

**Next milestone:** evaluate with truly independent, human-reviewed manufacturing documents and questions, then build a full document permission/workflow layer before expanding to other manufacturing domains. This phase does not retrain or modify V1/V2 LoRA weights.
