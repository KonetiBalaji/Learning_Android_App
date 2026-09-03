# Document quiz configuration

`POST /v1/documents/{id}/quizzes` accepts `chapter_ids`, `question_count` (5–20,
default 10) and optional `difficulty`: `easy`, `medium`, `hard`, `mixed`, or null.
Unknown difficulty strings return 422. Omission/null preserves legacy behavior.
Creation and `GET /v1/quizzes/{id}` return the saved requested difficulty.
Existing quizzes migrate to null, meaning unspecified, not inferred Easy.

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

Deterministic mode accepts only null/Easy recall. Other explicit levels return
422 before saving a quiz; it must not label unchanged recall content as Hard.
Android now sends the selected difficulty and displays saved request metadata on
question/results screens. Easy/offline difficulty device checks have passed;
live generation with the new quality audit still needs device verification.
Deploy the updated backend before testing the updated APK.
