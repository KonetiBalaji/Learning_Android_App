# Android upload progress

The original brief requires visible upload progress. The upload path previously
used the generic learning-session spinner. It now publishes byte progress while
writing the multipart request, then switches to a separate indeterminate
"Waiting for document analysis" phase after the request stream closes. Chapters
are shown only after a successful decoded server response and local persistence.

The percentage is explicitly estimated from the document provider's declared
size, capped at 99% while writing, and omitted when size is missing, nonpositive
or smaller than bytes observed. Displayed bytes measure writes to the buffered
request stream, not server acknowledgements. This is not server-side parsing or
AI progress. Updates are coalesced at 256 KiB intervals or the declared size;
small/fast uploads may reach the analysis phase before a transfer frame is drawn.
The existing 50 MiB streaming limit still applies even if metadata is false.

Progress is kept in ViewModel state for ordinary activity recreation and cleared
in a `finally` block on success, exception or cancellation. It is not persisted as
a resumable transfer. Process death during picker recovery, upload cancellation
controls and background transfer are separate unfinished work. The study-space
back and upload/library controls are disabled
while the operation is in flight. Error presentation continues using safe
client-owned messages.

On 2026-09-03 Android assembleDebug, lintDebug and 109 JVM tests passed. Five new
tests cover estimated progress, unknown/incorrect sizes, the analysis-wait phase,
write-before-progress ordering, output failures and invalid counters. Existing
bounded-stream upload tests also passed. On-device slow-network behavior, failure
recovery, rotation, large text and TalkBack announcements for this new overlay
remain unverified. This implementation evidence does not close DOC-01 or UX-01.

## Analysis-wait device verification

On 2026-09-03 the API 36 dedicated emulator passed
`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyUploadProgress` against
`uv run python scripts/serve_qa.py --qa-only --upload-response-delay 20`.
The script reset only the dedicated emulator app's disposable QA data, registered
a synthetic learner, selected Grade 8, used the real Android file picker to upload
the repository TXT fixture, verified the analysis-wait title and explanation, then
confirmed that the overlay cleared and both chapters could be selected.

Screenshots `artifacts/qa-upload-analysis-wait.png` and
`artifacts/qa-upload-analysis-complete.png` were visually inspected: the wait copy
is readable and unclipped at the tested font scale, and chapter controls appear
after success. This small fixture transfers too quickly to prove transfer-stage
percentages. Failure, slow-transfer, rotation, large-text and TalkBack coverage
remain open. This is agent-run QA, not user acceptance.

The delay is a bounded 1–20 second fixture installed only by the explicit
localhost QA runner. Production imports no delay middleware. Two added tests
verify route-specific delay and production exclusion; the full backend suite
passed **287 tests, 1 existing Windows symlink-privilege skip**, with the existing
Starlette/httpx warning. The QA server was returned to its normal no-delay mode
after the device run. As usual, restarting this disposable runner rotates its
session secret; subsequent device tests must reauthenticate their synthetic user.

## Uncertain upload responses

Upload HTTP 5xx, transport exceptions and malformed JSON now produce a
client-owned message directing the learner to **My uploaded documents before
retrying**, because the server may have saved the file. Existing 4xx session and
validation handling remains intact. Progress still clears in `finally`; no upload
is automatically replayed. This is recovery guidance, not upload idempotency.
The existing error dialog's "Try again" control dismisses the message only.

The opted-in QA runner supports `--fail-saved-upload-response` together with
`--upload-response-delay 20`. It substitutes 503 only after a 201 upload response,
leaving the committed document intact; validation failures keep their original
status. Production does not install this fixture. A unit test verifies the save
occurs before the substituted failure. Android build/lint and 110 JVM tests passed;
the full backend suite passed 288 tests with one existing Windows privilege skip
and the existing Starlette/httpx warning on 2026-09-03.

The dedicated API 36 emulator passed `-ResetTestAppData -VerifySavedUploadFailure`
using the actual picker and TXT fixture. It verified wait-overlay removal, the
library-first error message, reopening the saved file and exactly one document
in the synthetic user's server library. The screenshot
`artifacts/qa-upload-uncertain-error.png` was visually inspected and is readable
without clipping at the tested scale. An initial QA-script target used the filename
label instead of its Open button; that run was stopped and not counted. The corrected
run passed, recovering a transient null automation root via the existing retry.
The server was restored to normal no-fault mode afterward. This proves the injected
post-save 503 path, not real connection-loss/malformed-response recovery, cancellation,
process death, automatic deduplication or user acceptance.

## Idempotent upload retry

Uploads now carry an owner-scoped UUID in `X-Upload-Request-ID`. After validating
and storing the temporary file, the backend fingerprints the normalized filename,
media type and exact bytes. The document and request mapping commit in the same
`BEGIN IMMEDIATE` transaction. An identical retry returns the original document;
the temporary retry file is removed or durably queued, and quota is not charged
twice. Reusing the UUID for different content returns `409`. Requests without the
header remain compatible but do not gain replay protection.

Android saves an account-scoped request identity before opening the connection.
Selecting the same filename and declared size reuses it after an uncertain response;
different metadata allocates a new identity. The backend fingerprint remains
authoritative if metadata stayed the same while bytes changed. A confirmed decoded
success clears the pending identity; failures retain it.

Backend verification covers identical replay, changed-content conflict, separate
owners, invalid UUIDs and concurrent identical requests. The full suite passed
473 tests with one existing Windows privilege skip. Android build, lint and 138 JVM
tests passed. API 36 fault injection replaced the first committed response with 503;
the UI retained its pending identity, the learner reselected the same document, and
the retry opened the original server document. The identity then cleared and the
library contained exactly one document. This closes duplicate prevention for
explicit same-document retries, but not background/resumable transfer, picker
process-death recovery, cancellation, real network loss, physical-device UAT or
production deployment.
