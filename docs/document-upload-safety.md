# Bounded Android document upload

Android no longer calls `readBytes()` for selected documents. It rejects known
oversize/empty metadata before opening the network request, then copies with a
16 KiB buffer and a hard 50 MiB payload ceiling. Unknown, negative or incorrectly
small provider sizes cannot bypass the stream limit. At most one byte beyond the
limit is read to detect oversize input. HTTP chunked mode avoids the connection's
default whole-body buffering. Streams and connections close on failures.

Multipart filenames lose paths, CR/LF, other ASCII controls and quotes. The MIME
header comes from the allowlisted PDF/DOCX/TXT extension, not arbitrary provider
metadata. Server extraction and validation remain authoritative. Local errors are
shown with client-owned messages. An over-limit stream does not write the closing
multipart boundary and is not a completed document submission.

## Evidence, 2026-09-03

- Android build/lint and **19 JVM tests passed**. Five new upload tests cover an
  exact limit, unknown/false sizes, empty/oversize metadata, one-byte over-limit
  detection on an infinite synthetic stream, and safe names/media types.
- Backend **45 tests passed**. New API test submits streamed multipart chunks:
  unfinished multipart returns 422 with no stored file/database document; the
  same material with a closing boundary succeeds with one saved document.
- These are bounded-copy and in-process API tests, not Android document-picker
  end-to-end evidence or proof of production reverse-proxy streaming behavior.

Remaining: device tests with local/cloud content providers, revoked URI access,
50 MiB boundary files, cancellation/offline recovery; backend compressed-archive
resource limits; reverse-proxy request size/time limits; durable document session
recovery. No full DOC-01 acceptance or production security claim is made here.
