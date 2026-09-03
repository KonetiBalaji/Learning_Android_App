# Document quiz recovery

`GET /v1/quizzes/{id}` is owner-scoped and returns the source document summary,
actual question count, answered count, first unanswered public question, and
feedback for the last answered question. Correct options and explanations are
exposed only for that answered question, never the pending one. Missing/deleted
quizzes and another owner's IDs return 404; unauthenticated reads return 401.

Android commits an account-scoped quiz pointer after creation, records the last
learning workflow, restores that workflow on authenticated startup, and offers
"Resume document quiz" after reauthentication. Feedback may be replayed after a
restart; its Continue action goes to the server's next unanswered question.
Completed quizzes restore results. Deleted quiz pointers are removed on 404.
The question counter uses the actual returned total rather than a fixed ten.
No questions are regenerated during restoration.

Evidence: backend **59 tests passed**, including the new initial/answered/completed
resume, owner rejection, pending-answer protection and deletion regression.
Android build/lint and **19 JVM tests passed**; these JVM tests do not exercise
the new ViewModel recovery path. Document-picker/forced-process-death testing of
this workflow remains pending, so this is not device-QA or UAT acceptance.

Subsequent verification (2026-09-03): backend **74 tests passed**. Answer submission
now serializes competing writes and replays identical retries without rewriting
timestamps. Different choices cannot overwrite committed answers; future questions
are rejected until earlier questions are answered. Tests reproduced all three
previous defects before the fix. See `../shared/contracts/document-answers.md`.
Tests cover identical and differing concurrent submissions, sequential retry,
immutability, ordering, and owner/auth boundaries. Device network-loss/multi-device
recovery remains unverified.

Remaining DOC-01 gaps include recovery between upload and quiz creation, unsent
answer drafts and unknown-outcome quiz creation. Document generation was separately
reworked after this initial recovery slice; see `document-question-validation.md`
for actual quality evidence and remaining limitations, including legacy quizzes.
