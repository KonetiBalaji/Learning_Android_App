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

## Bounded regeneration after strict rejection

Physical-device UAT on candidate v15 reproduced two consecutive 503 responses
while requesting five Medium True/False questions from a valid, previously used
synthetic Grade 8 source. The upload, selection and earlier 10-question quiz were
healthy; both failures occurred after 46–52 seconds inside live generation or its
strict reviews.

The server now regenerates a completed but validation-rejected document-question
batch once within the same user operation. Transport failures and timeouts are not
repeated, because doing so only doubles the learner's wait and provider exposure.
A second validation failure still returns 503, writes no quiz, and exposes no
provider detail. This is deliberately bounded: it improves recovery from a single
malformed, ambiguous or review-rejected model response without weakening grounding,
answer review, quality review, storage atomicity, or user-level AI quotas.

The initial structured-generation call has a 90-second provider boundary, raised
from 60 seconds after the controlled synthetic diagnostic identified
`APITimeoutError`. Blind answer and quality reviews retain their separate 30-second
ceilings. Android permits 135 seconds for the reviewed operation; timeout failures
return immediately rather than entering the validation-only regeneration path.

Regression evidence on 2026-09-08: focused provider/retry tests passed 39/39 and
the full backend suite passed 721 tests with one skip. The controlled live
Medium True/False diagnostic then generated five synthetic questions in about
71 seconds and passed grounding, blind-answer review and quality review.

Signed candidate `0.3.0-uat.15` (version code 17, commit `82477a8`) then passed
the physical-device retest on a Xiaomi 21091116I running Android 13. With all
three chapters selected, custom count 5, Medium difficulty and True/False format,
the staging request returned HTTP 201 in 68.664 seconds. Android presented five
distinct questions with exact chapter and character-range sources, accepted all
five responses, and displayed `5 / 5 correct`. The candidate-bound private UAT
record closes the v16 binary-generation issue. This proves the corrected DOC-03
journey for this candidate and synthetic source; it does not establish broad
provider availability, curriculum approval or production acceptance.

## Audit-guided regeneration

Candidate v19 later reproduced two bounded 503 responses for the same five-question
Medium True/False journey while health remained ready. A privacy-safe controlled
probe established that transport, credentials and quota were healthy: the completed
bank was rejected by the independent quality audit. The former retry discarded that
information and submitted the identical generation request again.

Provider failures now log only a bounded pipeline stage and exception class. Quality
rejections additionally expose only the failed boolean category names, never model
text, source passages, prompts, answers or provider messages. A validation-rejected
retry receives those server-generated category names and explicitly corrects them;
blind answer review and quality review still receive no retry metadata, all original
grounding and demand checks remain fail-closed, and transport errors remain
non-retriable. A controlled live reproduction subsequently produced five reviewed
Medium True/False questions. Focused regression passed 38 tests and the full backend
suite passed 726 tests with one platform skip.

The first signed-candidate retest showed the guided retry correcting assumptions but
still failing Medium demand. Generation now requires every Medium binary item to use
a short source-grounded scenario or relationship; direct restatements and synonym
swaps remain Easy. Candidate `0.3.0-uat.19` (version code 21, commit `2f50da1`)
returned HTTP 201 in 76.011 seconds on the physical Xiaomi device. Android displayed
five distinct Medium True/False application questions with exact source ranges,
accepted all five answers, showed grounded feedback after each, and finished at
`5 / 5 correct`. The duplicate document was deleted while the original remained.
This closes DOC-01 and DOC-03 for that exact synthetic-source candidate; broader
content, provider availability and educator acceptance remain.
