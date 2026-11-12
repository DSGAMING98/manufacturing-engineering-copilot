# Manufacturing Copilot Phase 2B: safe hybrid chat

## Why

The trained Qwen3-1.7B adapter produced false FAIL results for real PASS measurements. The numeric decision must come from the **Phase 2 Python Decimal tolerance engine**, not the language model.

This ZIP is a **drop-in overlay**, not a new standalone project. Extract these new files into the **existing** `manufacturing-copilot` project root. All files in this ZIP are *new*, so no existing code, config, results, `.venv`, or adapter is overwritten. Do not extract a nested folder inside the project.

### Architecture and important honesty

The input is accepted only when a conservative parser can reliably identify **one** nominal, one measurement, a tolerance or both signed deviations, and a consistent unit. The engine then computes the result. The existing trained Qwen model is **loaded**, but its sole role in this safety-first version is to **select a presentation style** (technical, plain, or operator) from a strict whitelist. The system renders all decisions, numeric facts, reasoning and next steps from tested templates. Raw model text is *never shown*. A bad, contradictory, fabricated, or unparseable model response cannot alter the decision or inject unsupported standards references. An invalid model response falls back to technical style.

The hybrid is an integrated GPU model workflow, but it **does not yet use free-form model-generated technical explanations**. That would require a stronger claim-by-claim verification layer. Do not present this build as fully autonomous agentic engineering or as an end-to-end accurate natural language interpretation system.

### PyCharm PowerShell commands

```powershell
# Check all existing Phase 1, Phase 2 and new Phase 2B tests (CPU only)
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Quick check WITHOUT the GPU model
.\.venv\Scripts\python.exe -m src.hybrid_chat --no-model --once "nominal=20.00 measured=20.03 tolerance=0.05 unit=mm"

# Original natural language example WITHOUT the GPU model
.\.venv\Scripts\python.exe -m src.hybrid_chat --no-model --once "A shaft has nominal diameter 20.00 mm with tolerance ±0.05 mm. Measured diameter is 20.03 mm."

# Launch hybrid chat WITH your trained adapter (GPU)
.\.venv\Scripts\python.exe -m src.hybrid_chat --adapter models/qa_qlora/adapter
```

You may alternatively double-click `RUN_10_HYBRID_CHAT.bat`. Run `RUN_11_HYBRID_TESTS.bat` for tests.

### Example chat prompts

Supported **structured** single-dimension format (recommended):

```
nominal=20.00 measured=20.03 tolerance=0.05 unit=mm
nominal=20.00 measured=20.09 tolerance=0.05 unit=mm
nominal=10 measured=10.04 lower_dev=0 upper_dev=0.1 unit=mm
```

Supported **narrow natural language** format:

```
A shaft has nominal diameter 20.00 mm with tolerance ±0.05 mm. Measured diameter is 20.03 mm. Determine whether the part passes inspection.
Nominal diameter 10 mm, lower deviation -0.1 mm, upper deviation +0.2 mm, measured diameter 10.2 mm.
```

Result of first prompt: `PASS`, lower `19.95 mm`, upper `20.05 mm`.
Result of second prompt: `FAIL`, because `20.09 mm` > `20.05 mm`.

You can use `--style plain` or `--style operator` to force a style. This skips GPU inference because an explicit style leaves no model role.

### Scope / safety limitations

- Handles one scalar dimensional inspection with inclusive acceptance limits; `mm` and `in` accepted as separate units, not converted.
- Does not assess calibration, uncertainty, measurement capability, GD&T, sampling plans, drawings, surface finish, or full product conformity.
- Input interpretation is intentionally strict; unsupported or ambiguous language returns `INSUFFICIENT_DATA` rather than guessing. Prefer structured fields.
- No fake ISO references; output explicitly says calculations are from supplied user values and does not claim standards compliance.
- Not authorized for product-release, certification, or unattended factory actions.
- **Phase 1 standalone SLM evaluation numbers are not hybrid accuracy numbers.** Do not compare the 91.67% synthetic benchmark directly with the programmatic boundary tests.
- Existing `src.chat`, `src.evaluate`, and training artifacts remain unchanged for reproducibility.

### Next milestone

Build a parser for more industrial phrasing using a human-reviewed schema and a verified provenance layer for standards/documents. Then add independently sourced, non-template QA evaluation cases, and report hybrid coverage, refusal rates, and correctness **separately** from model-only metrics.
