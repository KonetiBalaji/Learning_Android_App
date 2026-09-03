# Document quiz configuration

`POST /v1/documents/{id}/quizzes` accepts `chapter_ids`, `question_count` (5–20,
default 10) and optional `difficulty`: `easy`, `medium`, `hard`, `mixed`, or null.
Unknown difficulty strings return 422. Omission/null preserves legacy behavior.
Creation and `GET /v1/quizzes/{id}` return the saved requested difficulty.
Existing quizzes migrate to null, meaning unspecified, not inferred Easy.

Difficulty describes requested cognitive demand, not calibrated learner ability:

- Easy: recognize/recall one explicitly stated fact.
- Medium: explain a relationship or apply one supported principle.
- Hard: combine multiple supported facts for application/comparison.
- Mixed: distribute those demands as evenly as the question count permits.

All levels must remain source-grounded, with no outside knowledge requirement.
The live provider receives these instructions but existing independent review
checks answer correctness/grounding, not calibrated difficulty. Saved metadata
records the request; it is not proof that each generated item meets that demand.

Deterministic mode accepts only null/Easy recall. Other explicit levels return
422 before saving a quiz; it must not label unchanged recall content as Hard.
Android now sends the selected difficulty and displays saved request metadata on
question/results screens. Device verification and actual difficulty evaluation
remain pending. Deploy the updated backend before testing the updated APK.
