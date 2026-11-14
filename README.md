# MFG Copilot

Manufacturing engineering prototype for design checks, process calculations,
production metrics, quality analysis, maintenance metrics, technical records,
document evidence, and observed-data machine learning.

[Live prototype](https://manufacturing-engineering-copilot.vercel.app/) ·
[Model evidence](real_models/evidence/real_model_report.json) ·
[Data sources](real_models/DATA_SOURCES.md) ·
[Research readiness](IEEE_READINESS.md)

![MFG Copilot logo](phase5/web/mfg-copilot-logo.png)

## Current research claim

The active prototype contains two models trained on **3,508 observed public
manufacturing records**:

| Model | Dataset | Records | Locked-test result |
|---|---|---:|---|
| Steel surface-fault classifier | UCI Steel Plates Faults | 1,941 | 80.21% accuracy (95% CI 75.84–84.07%); 80.39% macro-F1 (74.72–84.78%), `n=389` |
| Semiconductor failure-risk model | UCI SECOM | 1,567 | 79.64% ROC-AUC (95% CI 70.06–87.27%); 73.60% balanced accuracy (63.09–83.10%); `n=314` |

The scores are not combined into one misleading percentage. The steel task is
seven-class classification; SECOM is a strongly imbalanced binary risk task.
Each therefore uses task-appropriate metrics and its own locked test partition.

Only the two cited observed manufacturing datasets are used by the active
model-training pipeline and reported as research evidence.

## What the prototype does

The system is hybrid rather than a single unrestricted language model:

```text
Engineering request
        |
        +-- deterministic router and field extraction
        |
        +-- design/process/production/quality/maintenance calculators
        |
        +-- evidence retrieval from registered documents
        |
        +-- observed-data ML classifier (steel faults)
        |
        `-- traceable response with inputs, equations, status and citation
```

This design keeps arithmetic and acceptance limits in auditable code. A local
small language model can later be added for explanation and drafting, but it
must not replace the calculation engines or invent missing measurements.

### Engineering workspaces

| Workspace | Method | Output |
|---|---|---|
| Design | Worst-case limit arithmetic | minimum/maximum clearance and fit class |
| Process | Turning equations | spindle speed, feed rate and ideal cutting time |
| Production | ISO-style OEE factors | availability, performance, quality and OEE |
| Dimensional quality | Inclusive specification-limit comparison | pass/fail/insufficient-data result |
| Observed-data model | Random forest trained on real steel measurements | one of seven surface-fault classes and probabilities |
| Maintenance | Historical reliability equations | MTBF, MTTR and observed availability |
| Documentation | Structured record builder | traceable inspection-record draft |
| Evidence | Lexical retrieval with source hashes and line ranges | exact local excerpts or explicit no-source response |

## Real datasets and licenses

### Steel Plates Faults

- Source: UCI Machine Learning Repository
- DOI: `10.24432/C5J88N`
- License: CC BY 4.0
- Contents: 1,941 observed examples, 27 measured features, seven fault labels
- Use here: deployed quality classifier

### SECOM

- Source: UCI Machine Learning Repository
- DOI: `10.24432/C54305`
- License: CC BY 4.0
- Contents: 1,567 semiconductor-process examples, 590 anonymized sensor/process
  columns, pass/fail label
- Use here: local failure-risk research model

The original archives are downloaded directly from UCI. Their SHA-256 hashes
are recorded in the evidence report. Raw files stay in `data/raw/public_real/`
and are excluded from Git to avoid silently republishing changing archives.

## Training and validation design

Both tasks use a fixed, stratified 60/20/20 division with seed 42:

1. The training partition fits candidate models.
2. The validation partition selects hyperparameters. SECOM's decision threshold
   is also selected only on this partition.
3. The test partition remains untouched until the configuration is locked.
4. Per-class metrics and confusion matrices are written to the evidence report.
5. Locked-test uncertainty is estimated with 1,000 deterministic percentile
   bootstrap resamples.
6. Source URL, DOI, license and download hash are recorded with the run.

### Algorithms

The steel model is a 300-tree random forest. Each tree learns recursive feature
thresholds from bootstrap samples; the final class probability is the mean of
tree probabilities. `class_weight="balanced_subsample"` reduces majority-class
dominance. Maximum tree depth is selected by validation macro-F1 from
`{12, 18, unlimited}`. The selected forest is exported to a compressed,
dependency-free format used by the website.

The SECOM model is an Extra Trees ensemble. Missing sensor readings are replaced
with training-partition medians. Trees use randomized thresholds, balanced class
weights and 600 estimators. The feature-subsampling setting is selected by
validation ROC-AUC; the operating threshold is selected by validation failure
F1. Accuracy is intentionally not the headline metric because only 104 of 1,567
records are failures.

The engineering calculators use `Decimal` arithmetic where exact decimal
behavior matters. Retrieval uses normalized lexical matching over registered
document chunks and returns file hashes plus source line ranges.

## Reproduce the models

Python 3.11 or 3.12 is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-research.txt
.\.venv\Scripts\python.exe -m real_models.train_real_models
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Training writes:

- `real_models/evidence/real_model_report.json` — committed metrics and provenance;
- `phase5/model/steel_fault_forest.json.gz` — deployed forest;
- `real_models/artifacts/secom_failure_model.joblib` — local-only model;
- `data/raw/public_real/` — local-only original archives and extracted files.

## Run the prototype

```powershell
.\.venv\Scripts\python.exe -m phase5.web_app
```

Open `http://127.0.0.1:8765`. The public deployment runs the same dependency-free
steel model through `/api/run`.

Example request for the observed-data endpoint:

```json
{
  "domain": "real_quality",
  "fields": {
    "measurements": "42,50,270900,270944,267,17,44,24220,76,108,1687,1,0,80,0.0498,0.2415,0.1818,0.0047,0.4706,1,1,2.4265,0.9031,1.6435,0.8182,-0.2913,0.5822"
  }
}
```

## Repository map

```text
api/                 Vercel function
phase4/              document ingestion and retrieval
phase5/              engineering tools, router and web interface
phase6/              release checks and stress tests
phase7/              private industrial-data governance pipeline
real_models/         observed-data training, inference, artifacts and evidence
tests/               offline regression and security tests
```

## Scope and limitations

- The public datasets are authentic observations, but they are not from the
  intended deployment plant.
- The random split measures within-dataset generalization, not future-lot,
  future-time, cross-machine or cross-plant transfer.
- SECOM column names are anonymized, limiting causal and physical interpretation.
- The steel model accepts a fixed 27-feature schema and is not an image model.
- The language interface is currently a conservative router, not a generally
  capable fine-tuned LLM.
- No model result authorizes machine control, product release, maintenance
  deferral or a drawing change.

The next credible research step is a site-separated or time-separated evaluation
using permission-cleared plant data and frozen preprocessing. The Phase 7 pipeline
already supports manifests, de-identification checks, group-isolated splits,
dual annotations, agreement measurement and a local SQLite research store.

## Citation

If these datasets are used in a paper, cite the original dataset records:

- M. Buscema, S. Terzi and W. Tastle, “Steel Plates Faults,” UCI Machine
  Learning Repository, 2010, doi:10.24432/C5J88N.
- M. McCann and A. Johnston, “SECOM,” UCI Machine Learning Repository, 2008,
  doi:10.24432/C54305.

## License

Project code is released under the [MIT License](LICENSE). Dataset licenses and
required attribution remain separate and are documented above.
