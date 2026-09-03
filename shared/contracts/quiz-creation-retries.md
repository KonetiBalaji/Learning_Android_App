# Quiz creation retries

`POST /v1/documents/{document_id}/quizzes` accepts optional `request_id`, a UUID.
Omission/null preserves legacy behavior: every call may create a separate quiz.
Malformed IDs return 422. Android now sends this field; the matching backend
must be deployed before relying on retry protection.

A request ID is scoped to the authenticated account and tied to the document,
ordered chapter IDs, count, difficulty and question type after request-model
defaults are applied. The identity stores a hash, not source text or credentials.

- After a successful commit, an identical retry returns the original creation
  summary (201), including the same quiz ID and first question, without generation.
- Changed settings with the same committed ID return 409 before generation.
- Ownership is checked first. Another account cannot recover a quiz by guessing
  its request ID. Different accounts may use the same UUID independently.
- A serialized commit rechecks the ID, so concurrent identical requests persist
  only one quiz and return that quiz. Concurrent generation itself is NOT deduplicated:
  both requests can incur provider work before the first commit.
- Failures before commit do not consume the ID. The request record and quiz are
  committed atomically. Account/document deletion cascades to the request record;
  retrying a deleted document remains 404 and does not resurrect it.

Replay does not rewind answers. Clients should GET the saved quiz state after
recovery rather than assume the creation summary's first question is still pending.
A client must persist the request ID before posting, reuse it for the same pending
creation, and use a new ID for a deliberate new quiz or changed settings.

158 backend tests passed; 35 creation/provider tests passed again after final
conflict coverage and error wording changes. Tests cover committed replay without
generation, preserved answers, count/difficulty/type/chapter conflicts, malformed
IDs, simultaneous generation/one commit, owner isolation, deletion, failed-attempt
retry and legacy distinct creation. No live calls were needed.

## Android integration

Android stores a UUID and settings fingerprint in account-scoped preferences with
a synchronous commit before posting. Chapter IDs are sorted both for the local
fingerprint and the outgoing request. The same pending settings reuse the UUID;
changed settings allocate a new one. Failed storage prevents posting. Corrupted
pending identity fails closed rather than silently creating another quiz.

After POST, Android GETs the quiz state, checks its document/count/format and
loads results if already complete. Only then does one preferences commit replace
the upload pointer with the quiz pointer and remove pending identity. Errors before
that point retain identity for retry, including process restart. Explicitly
starting another document or deleting the active document clears the pending key;
account deletion clears all preferences. Corrupted-pending-data recovery UX still
needs improvement; it must not silently discard uncertain server work.

Build/lint/58 JVM tests passed for Android, including identity reconstruction,
chapter-order stability, changed settings, write failure and corrupt identity.
These tests do not simulate an actual post-commit network loss or process death.
Remaining: device lost-response injection, account-switch verification, in-progress
generation coordination, and deployment verification.
