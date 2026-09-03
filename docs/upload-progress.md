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
