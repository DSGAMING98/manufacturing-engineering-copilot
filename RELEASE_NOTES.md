# Research Prototype Release 0.7.0 (2026-11-13)

## Evaluation and hosted workbench update

- Added batched deterministic GPU evaluation and explicit evaluation-protocol metadata.
- Completed the once-only V2 Phase 3 held-out synthetic test: 79/120 (65.83%).
- Recorded per-class recall and error modes; PASS recall remains only 10%.
- Tested longer report training and a constrained label-only objective; neither beat V2 and neither was promoted.
- Added a serverless CPU API and deployment configuration for the deterministic workbench.
- Added hosted API regression tests and clearer hosted-mode safety labels.

## Completed

- Phases 1–3: 4-bit Qwen3-1.7B QLoRA pilot and independent V2 synthetic training/evaluation pipeline.
- Phase 2: verified decimal-dimensional inspection with strict hybrid decision separation.
- Phase 4: local extractive RAG with SHA-256 source integrity, approval metadata, source-line citations and conservative abstention.
- Phase 5: six bounded engineering workflow calculators and loopback-only browser dashboard.
- Phase 6: reproducibility runner, numerical boundary grid, HTTP security regression, publication figure generator, GitHub Actions CPU workflow, source-release audit and extensive release documentation.

## Observed evidence

- Operator-reported Phase 3 same-split standalone model validation: base 40/90; V1 38/90; V2 59/90.
- V2 false PASS: 1; false FAIL: 24. The research prototype therefore uses deterministic calculations for engineering decisions.
- 111/111 CPU unit tests, 16/16 toy demo retrieval cases, 30/30 hand-authored six-domain cases, and 529/529 generated tolerance boundary cases passed in the packaging environment.
- No GPU model benchmark was executed in the packaging environment. The original adapters and private generated prediction outputs remain on the user's laptop.

## Graphs

- `paper_figures/Fig01_model_validation_accuracy.png/.svg`: Wilson interval comparison from reported validation results.
- `paper_figures/Fig02_false_acceptance_and_rejection.png/.svg`: error type counts.
- `paper_figures/Fig03_v1_training_loss.png/.svg`: loss curve transcribed from operator's full Unsloth training log.
- `Fig04_v2_training_loss` is intentionally omitted until an actual local V2 `trainer_state.json` is available; run `python -m phase6.plot_results` in PyCharm to generate it.

## Packaging and publishing

The source ZIP contains no `.venv`, model weights, local approved documents, generated prediction logs, or local results. The GitHub app must be given access to the target repository before any connector-driven push can succeed. `PUBLISH_GITHUB.ps1` can push after an empty repository is created and authenticated Git is configured; it never force-pushes.

## Intended use and limitations

This is a teaching/research prototype, not a production-quality engineering service, validated industrial assistant, standards library, certified QA instrument, or automated product-release decision system. Source documents bundled with Phase 4 are **fictional demonstrations**.
