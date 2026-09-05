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
account deletion clears all preferences. A malformed pending record now fails closed
with an explicit choice: keep the uncertain retry record, or discard only that local
record and start a new request. The app never silently replaces it.

Build/lint/58 JVM tests passed for Android, including identity reconstruction,
chapter-order stability, changed settings, write failure and corrupt identity.
These unit tests do not simulate an actual post-commit network loss or process death.
The production recovery dialog also passed Android Accessibility Test Framework checks
and both explicit actions on the API 36 emulator as part of 14 connected tests. This
component test does not inject corrupted preferences through the full app journey.

## API 36 post-commit HTTP failure verification

`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyCreationRetry -VerifyLibrary`
passed against the isolated deterministic QA server. The explicitly installed QA
middleware replaces one successful creation response with HTTP 503 after endpoint
commit. Owner-checked QA observation confirms one saved quiz before retry.
Android retains the pending ID without accepting a quiz pointer, restores the
same identity after force-stop/restart, retries and opens that same server quiz.
The server still contains exactly one quiz, and Android removes the pending ID
after accepting recovery. Further question restart/conflict, completed results
and library reopening passed; remaining answers used API fixtures rather than
Android taps. `artifacts/qa-creation-retry.png` was visually inspected.

158 backend tests passed; the QA fault test passed again after an additional
unauthorized observation assertion. No live AI calls were made. QA routes are
not installed by normal application startup. This is HTTP response substitution,
not a TCP disconnect, partial response or kill-during-write simulation.
Remaining: real network-loss/partial-body cases, account-switch verification,
in-progress generation coordination and deployment verification.
