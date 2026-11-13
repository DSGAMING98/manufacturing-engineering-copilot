# Manufacturing Engineering Copilot · Phase 5: Six-domain workbench

**Version:** research prototype. Phase 5 adds the six-domain workbench, browser
interface, regression suite, and deterministic engineering tools. Model weights,
virtual environments, and generated results are not stored in Git.

## Purpose and honest scope

Phase 3's model-only validation on 90 synthetic examples showed base 44.44%, V1 42.22%, and V2 65.56%. V2 also made **24 false-FAIL decisions**. Phase 5 therefore makes no claim that the model can safely calculate inspection results. The six-domain workbench is **tool-first**, with transparent Python calculations; Phase 4 supplies traceable document excerpts. Qwen is optional and **only selects among available document excerpts** in the CLI when `--adapter` is provided. The web UI uses deterministic tools and offline local retrieval; it deliberately does not run an open-ended Qwen chatbot.

| Domain | Implemented working slice | Not implemented/guaranteed |
|---|---|---|
| **Design** | Worst-case hole/shaft clearance interval and clearance/transition/interference classification | CAD, FEA, full tolerance-stack analysis, material selection, ISO fit certification |
| **Process planning** | Ideal single-pass turning RPM, feed rate and nominal cutting-time estimate | Validated feeds/speeds, NC/G-code, operation sequencing, machine limits, tool selection |
| **Production** | Historical availability, performance, quality and OEE from supplied totals | Live MES integration, scheduling optimizer, throughput forecast |
| **Quality** | Existing Phase 2 Decimal inclusive dimensional inspection, bilateral or asymmetric deviations | Calibration validation, sampling plans, final disposition, certified compliance |
| **Maintenance** | Historical MTBF, MTTR, and observed availability, including no-failure handling | Predictive maintenance, RUL, automated work orders or repair recommendations |
| **Documentation** | Structured inspection record **draft** with mandatory identifiers, timezone, measured value and a verified dimensional check | Signatures, audit-trail database, actual review or automated batch release |
| **Cross-domain RAG** | Phase 4 indexed, verbatim citations from registered `.md/.txt` docs, approval metadata and SHA-256 checks | Copyrighted standards library, PDF parsing, neural semantic retrieval, autonomous standards answers |

The supplied regression examples and fictional demonstration docs are **not independent industrial validation**.

## Run the workbench

From PowerShell at the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m phase5.benchmark
.\.venv\Scripts\python.exe -m phase5.web_app
```

4. Open **http://127.0.0.1:8765/** in your normal browser, select a domain, edit example fields, and click **RUN CHECK**.
5. Press **Ctrl+C** in the terminal to stop the local server. Port conflict? Use `--port 8766`, then open `http://127.0.0.1:8766/`.

For fictional Phase 4 excerpts (marked DEMO in citations), run `python -m phase5.web_app --include-demo`. By default demo sources are **excluded**; real document answers require permission-cleared, genuinely reviewed files registered through `phase4.add_document` per `PHASE4_README.md`. Their approval claims are provided by the operator, not independently validated by software.

## Alternative: One unified CLI

```powershell
.\.venv\Scripts\python.exe -m phase5.cli
```

Type `examples` in the chat to view all six example commands. Try:

```text
quality nominal=20.00 measured=20.03 tolerance=0.05 unit=mm
design hole_min=20.00 hole_max=20.04 shaft_min=19.97 shaft_max=20.01 unit=mm
process diameter_mm=20 cutting_speed_m_per_min=100 feed_mm_per_rev=0.2 length_mm=80
production planned_min=480 run_min=420 ideal_cycle_min_per_part=1 total_parts=350 good_parts=335
maintenance operating_hours=800 repair_hours=20 failures=4
documentation record_id=IR-001 feature_id=SHAFT-1 drawing_id=DR-001 revision=A nominal=20 measured=20.03 tolerance=0.05 unit=mm equipment_id=GAUGE-7 timestamp=2026-11-13T09:30:00+05:30
knowledge What identifiers belong in an inspection record for traceability?
```

For demonstrator evidence, start with `--include-demo`. For optional **GPU-backed evidence selection**, start the CLI with:

```powershell
.\.venv\Scripts\python.exe -m phase5.cli --include-demo --adapter models/qa_qlora_v2/adapter
```

This uses the V2 LoRA solely to select a numbered excerpt already retrieved by Phase 4; the model never issues numeric conclusions, standards claims, or final release decisions. **No GPU needed for the web dashboard or calculator CLI.**

## Engineering formulas

### Design (mm only)

- `minimum clearance = hole_min - shaft_max`
- `maximum clearance = hole_max - shaft_min`
- If minimum clearance > 0: **CLEARANCE**; if maximum clearance < 0: **INTERFERENCE**; otherwise **TRANSITION**, including exact zero-clearance boundary.
- These are one-dimensional worst-case checks, not ISO fit-system letters/classes.

### Process planning: ideal turning estimate

- `rpm = 1000 * cutting_speed_m_per_min / (π * diameter_mm)`
- `feed_mm_per_min = rpm * feed_mm_per_rev`
- `cutting_time_min = length_mm / feed_mm_per_min`
- No approach, rapid moves, tool wear, machine limitation, chip-load optimization, or material constraints are included. **Do not copy these RPMs into machine control without engineering validation.**

### Production: OEE

- `availability = run_time / planned_time`
- `performance = ideal_cycle_time * total_parts / run_time`
- `quality = good_parts / total_parts`
- `OEE = availability * performance * quality`, shown as a percentage.
- Rejects nonsensical values (`good > total`, `run > planned`, calculated performance > 1) instead of silently claiming valid OEE.

### Quality

- Symmetric: `[nominal - tolerance, nominal + tolerance]`, limits inclusive.
- Alternative lower and upper deviations are supported by the CLI, e.g. `lower_dev=-0.02 upper_dev=0.04` (do not supply `tolerance` simultaneously).
- `20.00 ± 0.05 mm` measured `20.03 mm` = **PASS** for that single dimensional check.
- Calculation delegated to existing `src.tolerance_engine.inspect` and Phase 2 report formatting.

### Maintenance

- `observed MTBF = operating_hours / failures` if `failures > 0`
- `observed MTTR = repair_hours / failures` if `failures > 0`
- `observed availability = operating_hours / (operating_hours + repair_hours)`
- When there were no failures, **MTBF and MTTR are undefined**, not infinite or magically reliable. Metrics are retrospective and depend on event definitions. Never use as remaining-life predictions.

### Documentation

- `record_id`, `feature_id`, `drawing_id`, `revision`, `equipment_id`, timezone-aware ISO-8601 `timestamp`, plus nominal/measured/tolerance/unit are mandatory.
- The output is marked `DRAFT` with `PENDING_COMPLETION` workflow status, even
  when the single-dimensional check passes.
- No digital signature, immutable storage, user authentication or verified gauge calibration is implemented.

## Local UI/API security and privacy

- Standard-library HTTP server binds **only** to `127.0.0.1` by default. The browser points at your own machine.
- It is an ephemeral demonstration service with basic origin, content-type and payload-length restrictions, *not* an authenticated production server.
- No file upload, remote model inference, external APIs, telemetry, database, manufacturing-device connection or automatic network tunnel exists in Phase 5.
- The browser sends only values you enter to the local process. **Still do not use confidential industrial drawings or customer data unless your organization authorizes local processing**. Do not share real industrial secrets in a public GitHub/Hugging Face repo.
- Never expose port 8765 to the internet, port-forward it to other users or treat the local interface as secure for multiuser work.
- Numeric inputs are validated; unsupported units and incomplete cases are rejected. Document claims come from cited excerpts, not generative paraphrases.

## Testing and next research steps

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m phase5.benchmark --output results/phase5_benchmark.json
```

The benchmark is a small hand-authored arithmetic and refusal **regression test**, *not* a statistically powered industrial study. Keep these outcomes separate from Phase 3 SLM-only validation scores.

To progress toward a credible industrial copilot, obtain human-validated and permission-cleared test examples per domain; add uncertainty analyses, traceable revisioned source documents, human sign-off, security hardening, and independently designed test sets. Phase 6 should evaluate **tool accuracy, abstention, evidence quality, and operator usability** separately from neural model performance.
