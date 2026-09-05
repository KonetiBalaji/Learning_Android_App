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

The shipping ASGI stack now rejects an HTTP request body larger than the configured
file ceiling plus a fixed 256 KiB multipart envelope. A declared oversized
`Content-Length` is rejected before endpoint dispatch; requests without a length
are counted as chunks are consumed and fail at the first over-limit chunk. Invalid
or negative length values fail closed. The rejection keeps the privacy-safe Support
ID middleware, and no route, multipart parser, document parser, database write or
upload-file write is reached for a declared oversized body. The envelope permits
normal multipart headers but does not raise the 50 MiB document-content allowance.

## Evidence, 2026-09-03

- Android build/lint and **19 JVM tests passed**. Five new upload tests cover an
  exact limit, unknown/false sizes, empty/oversize metadata, one-byte over-limit
  detection on an infinite synthetic stream, and safe names/media types.
- Backend **45 tests passed**. New API test submits streamed multipart chunks:
  unfinished multipart returns 422 with no stored file/database document; the
  same material with a closing boundary succeeds with one saved document.
- These are bounded-copy and in-process API tests, not Android document-picker
  end-to-end evidence or proof of production reverse-proxy streaming behavior.
- `parser-stress-smoke.md` records two 100-input malformed PDF/DOCX runs through
  the asynchronous upload validation boundary: all admitted files were rejected,
  overload failed fast, no timeout/file/lease remained, and valid parsing recovered.

Remaining: device tests with local/cloud content providers, revoked URI access,
50 MiB boundary files, cancellation/offline recovery; reverse-proxy request size/time
limits that agree with the application boundary; durable document session
recovery. No full DOC-01 acceptance or production security claim is made here.
