# Phase 3 research-data curation checklist

**Status:** No validated real manufacturing records are bundled in this ZIP.

1. Obtain legitimate authorization and licensing for any internal drawings,
   metrology records, quality-control manuals, standard excerpts, or vendor documents.
   Do not use confidential customer data without permission.
2. Record origin, source license, document version, date, facility/product family,
   and an immutable `sha256` fingerprint for each source item. Avoid personal data.
3. Require verification of the nominal dimension, lower/upper specification bounds,
   measured value, unit, reference document, gauge/calibration status and uncertainty
   where relevant; **do not** infer missing measurements from a document title.
4. Have an authorized engineer or QA reviewer independently confirm each gold
   decision and rationale. Track reviewer initials/role and review date privately.
5. Ensure train/validation/test separation by source drawing, part family,
   production batch, equipment, and time to reduce near-duplicate leakage.
6. Freeze the final test dataset **before** model selection, record its SHA256 hash,
   and avoid repeatedly tuning against its results.
7. Report raw error counts, false acceptances (dangerous PASS on actual FAIL),
   false rejections (FAIL on actual PASS), refusals, and performance by feature type.
8. Explain the system's limits: current numerical engine accepts one scalar dimension
   with supplied numeric limits, not calibration validation, uncertainty, GD&T,
   sampling plans, full-product conformity or release authorization.
9. Only cite standards if you have licensed/authorized, version-verified sources
   with traceable page/section references; no generated ISO number is evidence.
10. Keep synthetic data labeled synthetic and never promote its metrics into
    industrial effectiveness claims.

Suggested private curation CSV fields (template provided as `review_template.csv`):
`case_id,source_id,source_license,source_sha256,product_family,feature_type,nominal,lower_deviation,upper_deviation,measured,unit,gauge_id,uncertainty,engineer_reviewed,review_date,gold_decision,source_section,notes`.

No reviewed records are supplied. The template is intentionally blank.
