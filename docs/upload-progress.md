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
a resumable transfer. Process death, upload cancellation controls, server-side
idempotency and background transfer are separate unfinished work. No automatic
upload retry is added, since an uncertain response could otherwise create a
duplicate document. The study-space back and upload/library controls are disabled
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
