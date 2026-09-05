# Grade 8 catalog diagnostic evaluation

Status: production quality gate strengthened; catalog-wide live quality is not
accepted. This evaluation is synthetic and curriculum-neutral. It does not prove
CBSE/NCERT alignment, educator approval, student outcomes or UAT.

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

## Remaining acceptance work

Run a predeclared multi-sample holdout after reviewing provider timeout/cost limits,
then have a qualified educator evaluate accepted wording against the approved current
curriculum. Do not repeatedly sample a failing chapter until one output passes. Runtime
rejection is a safety success but also evidence that availability and first-attempt
generation quality are not yet release-accepted.
