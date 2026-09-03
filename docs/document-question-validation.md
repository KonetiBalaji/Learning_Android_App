# Document question generation and review

The user confirmed reuse of the existing server-side OpenAI key. No credential
was created, moved or printed. The API-key skill's confirmation gate is resolved
for this work.

OpenAI mode now generates structured Grade 8 questions from selected chapter
passages, validates exact source quotes, choice uniqueness, count and duplicate
prompts, then submits questions to a separate blind answer-review call. The review
does not receive proposed answer keys or explanations. Any ambiguity, disagreement,
malformed output or provider failure rejects the batch with 503 before quiz writes.
Source offsets are computed by the server from verbatim quotes. Option order is
shuffled server-side after review to avoid a fixed answer-position pattern.

Both calls use `store=False`; selected source text is still sent to the provider.
Requests are limited to 40,000 selected characters and require a smaller selection
above that ceiling. There is no silent fallback from failed OpenAI generation.
Explicit deterministic mode now uses exact-source-word recall for credential-free
QA rather than the ambiguous "which statement is supported" questions. It is not
equivalent to the model-generated learning assessment.

Evidence: live `scripts/evaluate_document_quiz.py --live` generated and reviewed
five synthetic cell-biology questions successfully. Inspected the prompts, answers
and source offsets; each question targeted one fact. The initial generation put
every correct answer first, so server-side shuffling was added after this run.
Automated tests cover grounding, blind review, reviewer rejection/count mismatch,
and failed-generation persistence. No real learner documents were used for the
live test.

Backend regression suite: **66 tests passed** on 2026-09-03. These tests use mocked
API responses or deterministic QA and do not spend credits.

Limitations: same-model review can share errors with generation and is not a
guarantee of correctness. Broad adversarial/domain evaluation, explanation accuracy,
curriculum alignment, legacy quiz remediation and device end-to-end testing remain.
This addresses the known generator defect, not full DOC-01/UAT/production acceptance.
