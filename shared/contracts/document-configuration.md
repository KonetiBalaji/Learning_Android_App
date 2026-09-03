# Document quiz configuration

`POST /v1/documents/{id}/quizzes` accepts `chapter_ids`, `question_count` (5–20,
default 10) and optional `difficulty`: `easy`, `medium`, `hard`, `mixed`, or null.
Unknown difficulty strings return 422. Omission/null preserves legacy behavior.
Creation and `GET /v1/quizzes/{id}` return the saved requested difficulty.
Existing quizzes migrate to null, meaning unspecified, not inferred Easy.

`question_type` selects one format for the quiz: `multiple_choice` (default),
`true_false`, or `yes_no`. Unknown values and explicit null return 422. Creation,
resume and individual question payloads expose the saved type; existing records
migrate to `multiple_choice`. A mixed-format quiz is not currently supported.

Multiple choice requires four distinct options. True/False requires exactly
`["True", "False"]`; Yes/No requires exactly `["Yes", "No"]`. Binary option order
is fixed, while multiple-choice options remain shuffled. The server rejects wrong
cardinality, wrong binary labels/order and an out-of-range correct-answer index.
The same owner-scoped grading, retry, recovery and results flow applies to all
formats. False/No requires contradictory evidence, not mere absence of support.
All live formats use blind answer verification and the separate quality audit.
Offline generation currently supports multiple choice only and rejects binary
requests before saving a quiz. Android format selection and account-scoped draft
preferences are implemented. Question/results labels use the saved server format;
absent or unknown server metadata is displayed as unspecified. Deploy the updated
backend before using these controls. API 36 device checks cover binary selection
restoration/offline rejection and multiple-choice recovery after switching back.
Scripted binary device checks also cover wrong-answer submission, conflict,
feedback/next-question restart and results. Actual live binary generation plus
answering on Android remains pending.

Difficulty describes requested cognitive demand, not calibrated learner ability:

- Easy: recognize/recall one explicitly stated fact.
- Medium: explain a relationship or apply one supported principle.
- Hard: at least two dependent reasoning steps, not just one arithmetic operation.
- Mixed: distribute those demands as evenly as the question count permits.

All levels must remain source-grounded, with no outside knowledge requirement.
The live provider receives these instructions. Blind answer verification does not
receive the proposed answer or explanation. A separate quality audit then checks
actual requested demand, source assumptions, citation completeness and explanation
correctness. Every item must pass all four checks in order; missing, malformed or
negative verdicts reject the whole batch before persistence. This is fallible
model-based screening, not calibrated difficulty. Saved metadata records the
request; it is not proof that each generated item meets that demand.
Generation now receives a per-question demand plan, balanced across the three
levels for Mixed. Live evaluation still found insufficient difficulty separation
after this refinement, motivating the separate quality audit. See
`docs/difficulty-evaluation.md` for evidence and remaining limitations.

A successful live batch now uses three provider requests (generation, blind answer
review, quality audit), with no SDK retries. Generation retains a 60-second SDK
timeout; each review uses 30 seconds. These are SDK timeouts, not an end-to-end
deadline. Operational failures return the existing safe generation-unavailable
response; the server does not silently downgrade difficulty or save a partial quiz.

Generation selects inclusive, chapter-local numbered source excerpts rather than
copying a quote. The server rebuilds the exact contiguous original text between
those endpoints, including intervening whitespace, and preserves the chosen
occurrence's source offset. Out-of-range, reversed, unknown-chapter and unsupported
length selections are rejected. This prevents transcription errors, not irrelevant
evidence: blind answer verification and citation-completeness review still apply.

Deterministic mode accepts only null/Easy recall. Other explicit levels return
422 before saving a quiz; it must not label unchanged recall content as Hard.
Android now sends the selected difficulty and displays saved request metadata on
question/results screens. Easy/offline difficulty device checks have passed;
live generation with the new quality audit still needs device verification.
Deploy the updated backend before testing the updated APK.
