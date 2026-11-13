# Observed manufacturing data sources

The active research models use public measurements, not generated operating records.

| Source | What was observed | Records | License | Citation |
|---|---|---:|---|---|
| UCI Steel Plates Faults | Twenty-seven geometric and luminosity measurements for seven surface-fault classes | 1,941 | CC BY 4.0 | M. Buscema, S. Terzi and W. Tastle, 2010, DOI: 10.24432/C5J88N |
| UCI SECOM | Anonymized sensor and process measurements from semiconductor manufacturing with pass/fail labels | 1,567 | CC BY 4.0 | M. McCann and A. Johnston, 2008, DOI: 10.24432/C54305 |

The training command downloads the original ZIP archives from UCI, records their
SHA-256 hashes, and keeps the raw files under `data/raw/public_real/` (gitignored).
The repository contains a deployable forest export and the complete locked-test
report. The SECOM model remains local because its 590 anonymous inputs are not a
useful public form.

```powershell
.\.venv\Scripts\python.exe -m real_models.train_real_models
```

These datasets support bounded quality and process-monitoring experiments. They
do not validate design advice, production scheduling, documentation generation,
or performance at a different plant.
