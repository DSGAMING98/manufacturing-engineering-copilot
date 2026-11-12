# Dataset provenance and split policy

The included `train.jsonl` (72), `validation.jsonl` (18), and `test.jsonl` (24) are 114 **programmatically generated synthetic** single-dimension QA scenarios.

Each record includes its generated scenario ID, case group, user question, model target answer, and algorithmically derived class. These scenarios **do not** come from real factory records or a government-company dataset. They are used to validate the code path only. The train, validation, and test prompts come from the same small set of templates, so any score is not a valid estimate of out-of-distribution performance.

`python -m src.data_validation` checks split disjointness and response labels. The test split should stay untouched until model and hyperparameters are frozen. Research-grade evaluation additionally needs permission-cleared, independently curated, expert-labeled data not generated using these training templates.

Regenerate **only if intentionally resetting all splits**:

```powershell
python -m scripts.build_seed_data
```

Never claim these synthetic cases were independently reviewed by manufacturing experts.
