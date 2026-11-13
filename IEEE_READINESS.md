# IEEE Submission Readiness

This checklist covers the general research-integrity and reproducibility items
implemented by the repository. The selected IEEE journal or conference may have
additional page, template, anonymization, artifact, or review requirements.

## Implemented repository evidence

- Source code and exact algorithm descriptions are public.
- Dataset and evaluation generators are deterministic where applicable.
- Synthetic and real-data claims are explicitly separated.
- Model, dataset, and result limitations are recorded in the model card.
- Real-data ingestion fails when permission, ethics determination, provenance,
  de-identification, or independent annotation is missing.
- Group-isolated splitting prevents product/site/machine groups from leaking
  across train, validation, and test.
- Accuracy, Wilson interval, macro-F1, per-class metrics, abstentions, and a
  confusion matrix are produced for real-data routing evaluation.
- Unit, regression, numerical stress, HTTP security, and release audits run in
  GitHub Actions.
- Private manufacturing data, model weights, and generated databases are
  excluded from Git.

## Required before making a real-data paper claim

- [ ] Written data-owner authorization is on file.
- [ ] Ethics/IRB or equivalent determination is complete, where applicable.
- [ ] Consent is documented or the reason it is not required is recorded.
- [ ] The dataset is de-identified and independently checked.
- [ ] Two qualified reviewers label each evaluated routing record.
- [ ] Reviewer agreement and adjudication are reported.
- [ ] Split groups are chosen before model selection.
- [ ] The external or prospective test set is frozen and hashed.
- [ ] Baselines, ablations, confidence intervals, and error analysis are reported.
- [ ] The data-availability statement matches actual permissions.
- [ ] All sources, reused figures, data, and code are cited.
- [ ] The manuscript is original and not simultaneously submitted elsewhere.
- [ ] Any use of generated content in the manuscript is disclosed as required by
      the selected IEEE publication's current policy.
- [ ] The exact venue template, page limit, anonymization rule, and submission
      checklist have been checked on the venue website.

## Suggested data-availability statements

### Restricted industrial data

> The industrial records used in this study are subject to organizational and
> contractual restrictions and cannot be published. The repository provides the
> schema, validation pipeline, group-splitting procedure, evaluation code,
> dataset fingerprints, and aggregate results required to inspect the method.

### De-identified dataset approved for release

> The de-identified dataset and immutable version used in this study are
> available at [repository/DOI]. The repository contains the corresponding code,
> configuration, and dataset fingerprint.

## Paper evidence table

| Paper claim | Required repository evidence |
|---|---|
| Real manufacturing dataset | Passing Phase 7 validation report and permission reference |
| Independent expert labels | Reviewer agreement, roles, and adjudication counts |
| Generalization | Group-isolated or prospective test result |
| Reproducibility | Commit SHA, configuration, data fingerprint, and commands |
| Routing improvement | Same-split baselines, confidence intervals, and per-class metrics |
| Grounded retrieval | Verified question/passage benchmark and citation metrics |
| Operational usefulness | Shadow-mode protocol, latency, correction rate, and user study |

## Official policy references

- [IEEE submission and peer-review policies](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/)
- [IEEE research reproducibility guidance](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/research-reproducibility/)
- [IEEE conference authoring tools and templates](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/)
- [IEEE Author Ethics Guidelines](https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/IEEE-Author-Ethics-Guidelines.pdf)
