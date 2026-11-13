# Phase 2: Deterministic engineering QA

Phase 2 adds the verified dimensional-inspection workflow without deleting or
retraining an existing adapter. Run commands from the repository root.

## Run in PyCharm PowerShell

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m src.verified_qa --nominal 20.00 --measured 20.03 --tolerance 0.05
.\.venv\Scripts\python.exe -m src.verified_qa --nominal 20.00 --measured 20.09 --tolerance 0.05
.\.venv\Scripts\python.exe -m src.verified_qa --nominal 10 --measured 10.04 --low-dev 0 --high-dev 0.1
.\.venv\Scripts\python.exe -m src.verified_qa --text "A shaft has nominal diameter 20.00 mm with tolerance ±0.05 mm. Measured diameter is 20.03 mm."
```

The verified CLI intentionally does **not** ask the SLM to calculate or override
a decision. `src.chat` remains an **unverified model-only demo**, not a validated
inspection workflow. Use `src.verified_qa` for deterministic dimensional checks.

Limits: single scalar measurement; all values in same specified unit; inclusive bounds; no measurement uncertainty, GD&T, calibration, or ISO compliance inference; no automated product-release authorization. The natural-language parser is intentionally narrow and refuses unsupported input rather than guessing. For reliable use, prefer structured CLI flags.

Next integration milestone: route user requests through structured validated forms and supply the deterministic result as immutable context to the SLM for explanatory text, then validate the final output against the calculated result. Until implemented, do not treat SLM answers as verified.
