# Real Manufacturing Data Protocol

## Purpose

This protocol converts authorized manufacturing records into a defensible
research dataset without placing confidential source material in Git. It applies
to engineering requests, inspection exports, MES data, CMMS events, process
plans, drawing reviews, NCR records, and approved-document questions.

## Non-negotiable entry conditions

1. The data owner has provided written permission for the stated research use.
2. An ethics or human-subjects determination is recorded as `approved`, `exempt`,
   or `not_human_subjects`; `pending` blocks validation.
3. Direct personal, customer, supplier, and raw equipment identifiers have been
   removed or replaced with irreversible research identifiers.
4. Every row can be traced to an authorized source through hashes and controlled
   internal records.
5. Two independent qualified reviewers label every routing request.
6. Reviewer identities are represented only by salted SHA-256 identifiers.
7. Confidential data remains under `phase7/private_data/`, which is gitignored.

## Collection plan

Collect requests from design, process planning, production, quality,
maintenance, technical documentation, and document-evidence workflows. Preserve
the natural class distribution and record the source system and event time.

Recommended pilot minimum:

- 500 total real requests;
- 50 or more requests in each of the seven domains;
- five or more independent product, machine, site, or time groups;
- at least 200 records reserved for validation and test combined;
- at least one external or prospective group never used during tuning.

## De-identification

Remove names, email addresses, telephone numbers, addresses, employee IDs,
customer names, supplier names, raw part serial numbers, and free-text comments
that identify a person or organization. Replace source-record identifiers with
salted hashes maintained by the data owner. Do not publish the salt or lookup
table.

Retain only context needed by the research question. Generalize exact site,
machine, and product identities into stable research groups such as `SITE_03`,
`LATHE_FAMILY_02`, or `PRODUCT_GROUP_05`.

## Annotation

Each reviewer independently selects one of:

`design`, `process`, `production`, `quality`, `maintenance`, `documentation`,
or `knowledge`.

Reviewers also identify required input fields and missing evidence. They must
not see model predictions during initial annotation. Disagreements are resolved
by a third qualified role and recorded in `adjudication_role`.

The pipeline reports exact reviewer agreement and Cohen's kappa. A pilot target
of kappa >= 0.80 is used as a readiness threshold, not as a universal standard.

## Leakage-resistant splitting

Choose `split_group` before model training. It should identify the unit that
must not cross splits: product family, machine family, site, customer group, or
time period. The pipeline assigns whole groups to train, validation, and test.
No request or group may appear in more than one split.

After the test set has been evaluated, it is no longer an untouched set. Further
model changes require a new external or prospective test group.

## Execution

Store the real JSONL file and completed manifest under the ignored private-data
directory, then run:

```powershell
.\.venv\Scripts\python.exe -m phase7.real_data_pipeline convert-csv `
  --csv phase7/private_data/annotations.csv `
  --output phase7/private_data/records.jsonl

.\.venv\Scripts\python.exe -m phase7.real_data_pipeline fingerprint `
  --data phase7/private_data/records.jsonl

.\.venv\Scripts\python.exe -m phase7.real_data_pipeline validate `
  --data phase7/private_data/records.jsonl `
  --manifest phase7/private_data/manifest.json

.\.venv\Scripts\python.exe -m phase7.real_data_pipeline split `
  --data phase7/private_data/records.jsonl `
  --manifest phase7/private_data/manifest.json `
  --output-dir phase7/output/splits

.\.venv\Scripts\python.exe -m phase7.real_data_pipeline ingest `
  --data phase7/private_data/records.jsonl `
  --manifest phase7/private_data/manifest.json `
  --database phase7/output/research.sqlite3

.\.venv\Scripts\python.exe -m phase7.real_data_pipeline readiness `
  --data phase7/private_data/records.jsonl `
  --manifest phase7/private_data/manifest.json
```

## Publication outputs

Publish only code, schemas, aggregate counts, evaluation metrics, dataset hashes,
and a data-availability statement unless the data owner authorizes release of a
de-identified dataset. Never publish the private SQLite database, raw exports,
reviewer lookup information, or confidential document text.
