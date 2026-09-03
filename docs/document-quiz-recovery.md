# Document quiz recovery

`GET /v1/quizzes/{id}` is owner-scoped and returns the source document summary,
actual question count, answered count, first unanswered public question, and
feedback for the last answered question. Correct options and explanations are
exposed only for that answered question, never the pending one. Missing/deleted
quizzes and another owner's IDs return 404; unauthenticated reads return 401.

Android commits an account-scoped quiz pointer after creation, records the last
learning workflow, restores that workflow on authenticated startup, and offers
"Resume document study" after reauthentication. Feedback may be replayed after a
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

Android conflict handling now opts in at the four answer submission operations:
document answers resume the document quiz; diagnostic/practice/rewrite answers
resume adaptive learning. Recovery is selected from the submitted operation, not
whichever screen happens to be visible when the response arrives. Read/resume
requests do not opt in, so a failed refresh shows an error instead of recursively
refreshing. The operation guard is released before starting the one recovery read.
Build, lint and **29 JVM tests passed**; two new policy tests cover both flow
targets, non-conflict failures and the no-recursion default. They do not exercise
the ViewModel on a device, and do not establish multi-device UAT acceptance.

Upload-stage recovery (2026-09-03): Android commits the uploaded document ID and
initial chapter before displaying chapter selection; later chapter selection is
saved. These pointers are account-scoped. Startup restores the active document
workflow, and the manual resume button also works after reauthentication. A quiz
pointer takes precedence; successful quiz creation atomically replaces upload
pointers. Starting another document clears local pointers, not server documents.
An upload failure leaves the previous saved study intact. No document contents or
device URI are persisted in these preferences.

`GET /v1/documents/{id}` returns only the owner-authorized document summary and
chapters. Missing/deleted/other-owner documents return 404; Android removes the
stale upload pointer and returns to upload. Offline failures retain the pointer.
A saved chapter absent from the restored list falls back to the first available
chapter. Backend **75 tests passed** including summary shape, owner/auth and
deletion checks. Android build/lint/**30 JVM tests passed**, including chapter
fallback policy. These checks do not prove forced-process-death/device-picker
recovery; that device test remains required.

Remaining DOC-01 gaps include unsent answer drafts and unknown-outcome upload or
quiz creation (server success before the client receives/persists the ID).
Document generation was separately
reworked after this initial recovery slice; see `document-question-validation.md`
for actual quality evidence and remaining limitations, including legacy quizzes.
