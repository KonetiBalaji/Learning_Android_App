# Quiz creation retries

`POST /v1/documents/{document_id}/quizzes` accepts optional `request_id`, a UUID.
Omission/null preserves legacy behavior: every call may create a separate quiz.
Malformed IDs return 422. Android has not yet been wired to send this field.

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

Remaining: Android durable request identity and recovery, device lost-response
injection, in-progress generation coordination, and deployment verification.
