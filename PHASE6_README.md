# Phase 6: Reproducibility, release hardening, and publication figures

Phase 6 provides reproducibility checks, release hardening, publication figures,
and source-release auditing. LoRA adapters, virtual environments, generated
results, and independent local documents are excluded from Git.

## Quick commands

```powershell
.\.venv\Scripts\python.exe -m phase6.reproduce
.\.venv\Scripts\python.exe -m pip install -r requirements-phase6.txt
.\.venv\Scripts\python.exe -m phase6.plot_results
.\.venv\Scripts\python.exe -m phase5.web_app
```

Outputs: `results/phase6/reproducibility.json` (private; gitignored) and
`paper_figures/` (published figures, provenance JSON and synthetic validation CSV).

The test harness checks all existing CPU unit tests, Phase 3 dataset labels and
SHA-256, Phase 4 demo retrieval regressions, Phase 5 six-domain tool regressions,
529 inclusive-boundary tolerance cases and release path exclusions. **These are
software checks, not a production certification or an SLM-quality guarantee.**

## Model comparison and graphs

Figure 1 and Figure 2 use all three model-only Phase 3 validations on the same
90 example split. They prefer `results/phase3/{base,v1,v2}_validation.json`,
and enforce matching fingerprints and full split. If those are absent, the
explicitly labelled recorded evaluation summary is used. The pipeline never
mix datasets. Figure 3 uses 24 real V1 loss points from the terminal log.
Figure 4 is generated from real V2 `trainer_state.json` only when present.
See `docs/PAPER_FIGURE_NOTES.md` for exact caption text, data provenance and
claim boundaries. All Phase 3 examples are rule-generated synthetic cases.

## Publishing checklist

1. Review the source tree for personal names, credentials, external licenses,
   confidential machine data and customer procedures.
2. Ensure generated `.venv`, model weights, dataset annotations from customers,
   and raw model predictions stay local. `models/`, `results/`,
   `phase4/docs/local/` and `data/raw/` are gitignored.
3. Run `python -m phase6.release_checks` and inspect `git status --short`.
4. Review the staged diff before committing and push through authenticated Git.
5. Do not publish the trained `.safetensors` adapter in GitHub. If eventually
   sharing an adapter via Hugging Face, review model license, dataset usage and
   release safety separately.

## Critical limitations

- Six-domain calculators are useful demonstrators, not certified industrial tools.
- Model-only V2 validation: 65.56% on 90 synthetic examples, with 24 false FAIL.
- Phase 4 documents are fictional demos, not ISO text or approved plant procedures.
- Dashboard binds to loopback and has no authentication, operator roles,
  manufacturing-controller access, immutable record log, or telemetry.
- On-demand training/quantization is GPU-specific; CPU GitHub CI does not run it.
- Human-in-the-loop approval remains mandatory for real manufacturing decisions.
