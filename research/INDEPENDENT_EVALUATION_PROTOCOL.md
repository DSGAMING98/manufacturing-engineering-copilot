# Independent Workbench Evaluation Protocol (UNEXECUTED)

This is a pre-registration template, **not** evidence that a study has been completed. Do not report results until authorized and independently collected data exist.

## Research objective

Evaluate the deployed deterministic MFG Workbench router, refusal behavior, and retrieval. This protocol does **not** study a deployed generative language model.

## Sample and reviewer process

- Collect at least 100 real, naturally written engineering requests from consenting engineers/students who have not developed the router.
- Obtain two qualified independent reviewers, blinded to all system outputs, to assign exactly one expected label: design, process, production, quality, maintenance, documentation, knowledge, or UNSUPPORTED_OR_AMBIGUOUS.
- Record missing inputs separately from expected route. Include ambiguity and unsupported requests.
- Adjudicate disagreements with another qualified person. Calculate raw agreement and Cohen kappa before resolving.
- Freeze the repository commit and evaluation rows before running the system. Do not rewrite prompts based on observed errors.
- Keep confidential documents and personal details out of the public repository.

## Annotation CSV schema

request_id,prompt,expert1_route,expert2_route,adjudicated_route,contains_required_inputs,source_group,notes

Store the completed file in permission-controlled storage. The source_group can be an anonymized participant or industrial-task group.

## Required routing results

Report exact-match routing accuracy, per-class precision/recall/F1, confusion matrix, abstention sensitivity on unsupported requests, supported-request coverage, and false-route rate. If multiple requests come from the same participant, calculate uncertainty with participant-level rather than naively independent row-level resampling.

The existing 125 developer-authored probes (114 correct) are **development diagnostics only** and must stay separate from independently labelled results.

## Retrieval relevance

Create an approved, permission-cleared corpus, with exact document revision and SHA-256. Independent qualified reviewers must annotate query-to-relevant-document mappings before seeing search output. Report hit@1, hit@3, citation validity and refusal rate for unsupported questions. Do not claim representative industrial retrieval accuracy from a tiny public metadata index.

## Optional usability study

With consent and institutional approval, invite 5–10 actual users to attempt identical scenarios. Measure task completion and errors and administer the original 10-item System Usability Scale. Report sample size and variance; do not invent responses or imply that a convenience sample represents factory operators.

## Publication audit trail

Keep immutable study date, ethics/permission decision, reviewer role, frozen code SHA, de-identified question IDs, data hashes, counts, error examples, and analysis scripts. Report source and training limitations.

**Current study status: not conducted.**
