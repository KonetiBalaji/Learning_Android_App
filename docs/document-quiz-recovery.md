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

Remaining DOC-01 gaps: recovery between upload and quiz creation, unsent answer
drafts, unknown-outcome create/answer reconciliation and server concurrency rules.
The existing document generator also uses other source-supported statements as
distractors for a support question, so multiple choices can be valid. That is a
separate release-blocking quality defect; recovery tests do not validate pedagogy.
