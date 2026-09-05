# Grade 8 catalog diagnostic evaluation

Status: production quality gate strengthened; catalog-wide live quality is not
accepted. This evaluation is synthetic and curriculum-neutral. It does not prove
CBSE/NCERT alignment, educator approval, student outcomes or UAT.

## Source-bounded generation follow-up (2026-09-05)

The earlier all-chapter run repeatedly rejected otherwise plausible teaching text
because it introduced facts that were not established by the generated question.
Generation now explicitly requires the model to solve every diagnostic and practice
item before returning it, put all necessary factual premises in the question or
options, confine the explanation to those premises and the verified solution, and
make each worked example self-contained. The independent review remains unchanged
and fail-closed; this is an availability improvement, not weaker validation.

A single live targeted run covered the three chapters whose earlier results most
directly showed `teaching_source` failures:

- Civics passed all three items and teaching checks.
- Matter no longer had a teaching-source failure, but item 1 was rejected as
  ambiguous with invalid practice.
- Decimals reached the fixed 30-second provider timeout and remained unavailable.

Evidence: `artifacts/catalog-diagnostic-eval-20260905T025032292688Z.json` (ignored
runtime artifact). The run was not repeated to select a favorable sample. It is
1/3 bounded evidence that the prompt reaches the intended review path, not proof of
catalog-wide availability or curriculum correctness.

## Reproducible evaluator

`backend/scripts/evaluate_catalog_diagnostics.py` enumerates every chapter exposed by
the server catalog and calls the same diagnostic generation plus independent blind
review path used in production. It refuses to run without `--live`, uses no retries,
does not print credentials, and writes ignored JSON evidence under `artifacts/`.
`--chapters` supports a declared bounded follow-up without rerunning unrelated cases.

The evaluator covers all 17 unique Grade 8 catalog chapters across Mathematics,
Science, English and Social Studies. A complete run requires two metered provider
requests per chapter when generation returns a valid schema.

## 2026-09-04 observations

The first catalog-wide run accepted 0 of 17 at the harness boundary:

- three provider timeouts;
- three generated-schema validation failures;
- six banks rejected by the independent runtime review for fixed accuracy, teaching
  or practice-answer reasons;
- five otherwise accepted banks lost to an evaluator-only serialization error because
  the script treated a dataclass as a Pydantic model.

The saved evidence is
`artifacts/catalog-diagnostic-eval-20260905T013446997818Z.json`. The harness defect did
not affect the production API, which uses the existing dataclass serializer.

After replacing the faulty serializer, a bounded follow-up reran only the five affected
chapters. Cells and English Writing passed the existing runtime gate; Percentages and
History were rejected, and Algebra timed out. Manual inspection then found that the
accepted Writing bank reused one subject-identification practice prompt for three
different diagnostic concepts. Evidence:
`artifacts/catalog-diagnostic-eval-20260905T013736753591Z.json`.

That observation produced two production changes:

- deterministic bank validation now requires three distinct practice prompts;
- the blind reviewer receives each declared concept and must explicitly confirm that
  its practice prompt reinforces that specific concept, not merely the broad subject.

The first post-hardening Writing sample timed out and is recorded at
`artifacts/catalog-diagnostic-eval-20260905T014316531369Z.json`. It is not counted as a
pass or rejection of the new semantic decision. The new deterministic and mocked-review
checks pass, including direct duplicate rejection and fail-closed concept disagreement.
The focused suite passed 55 tests and the complete backend suite passed 633 with one
existing Windows privilege skip.

## 2026-09-05 catalog run and adapter repair

A new predeclared catalog-wide run exercised all 17 chapters after the concept-specific
practice gate. Five banks passed and twelve failed closed. The evidence is
`artifacts/catalog-diagnostic-eval-20260905T023721671105Z.json`. Failures included
genuine ambiguity, key disagreement, concept/source review rejection, one malformed
schema and one timeout. Eight item-level failures, however, used
`practice_numeric_parse`, including all three Grammar items. This exposed an adapter
availability defect: a reviewer `none` format classification forced numeric parsing
even when the independently reviewed answer variants were clearly textual.

The adapter now enables rational-number equivalence only when the reviewer selects
`none`, the prompt has no explicit exact-format constraint, and every independently
reviewed answer actually parses as a number. Otherwise it stores exact matching.
This does not trust generated keys, weaken explicit format constraints, or accept a
review disagreement. A regression locks the observed nonnumeric misclassification.

A bounded follow-up reran only Algebra, Geometry, Grammar and Economics. Algebra,
Geometry and Grammar passed; Economics remained rejected for an independent practice
key disagreement. Evidence:
`artifacts/catalog-diagnostic-eval-20260905T023952615002Z.json`. This is evidence that
the adapter false rejection was repaired, not permission to resample Economics until
it passes or a claim of catalog-wide content acceptance. The focused adapter suite
passed 100 tests and the complete backend regression passed 635 with one existing
Windows privilege skip.

## Remaining acceptance work

Run a predeclared multi-sample holdout after reviewing provider timeout/cost limits,
then have a qualified educator evaluate accepted wording against the approved current
curriculum. Do not repeatedly sample a failing chapter until one output passes. Runtime
rejection is a safety success but also evidence that availability and first-attempt
generation quality are not yet release-accepted.
