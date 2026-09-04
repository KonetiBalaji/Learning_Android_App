# DOCX admission limits

Before python-docx parses an upload, archive preflight enforces:

- 2,048 ZIP members maximum;
- 20 MiB uncompressed per member and 100 MiB total;
- maximum declared compression ratio of 1,000:1;
- stored/deflate compression only, no encrypted members;
- no duplicate, absolute, parent-traversal, backslash, drive-qualified or NUL paths;
- required content-types and main document parts;
- bounded reads of each member to validate readable length and CRC.

These are conservative processing ceilings, distinct from the 50 MiB upload
limit. A legitimately complex document can exceed them and be rejected. No archive
members are extracted to the filesystem. Corrupt, protected or over-limit uploads
receive a generic 422 response, without parser errors/internal member names. The
already-written temporary upload is removed on extraction rejection.

## Verification, 2026-09-03

`uv run pytest -q`: **58 passed**. New tests cover a normal DOCX, malformed paths,
duplicate members, member-count/size/total/ratio limits, corrupt CRC, unsupported
compression, sanitized failure responses and no saved file/database document on
rejection. Limits are lowered in small synthetic fixtures; tests do not allocate
huge hostile archives. Existing real PDF/DOCX upload tests continue to pass.

An initial Windows path test exposed normalization of ZIP member names. The guard
now also checks the original archive name, and the regression crafts that raw
name in both ZIP headers. No weakened assertion was used to accept normalization.

## Isolated extraction

Upload parsing now runs in a fresh spawned process rather than the API process.
The parent waits at most `LEARNING_DOCUMENT_PARSE_TIMEOUT_SECONDS` (15 seconds by
default, configurable from 1 to 120), then terminates and, if necessary, kills the
child. Extracted text is capped at 2,000,000 characters before it crosses the
process boundary. POSIX workers also request a 1 GiB address-space ceiling;
Windows lacks Python's portable `resource` limit but still receives process,
wall-time and output isolation. Child exceptions and parser details never cross
the boundary. Time/output violations return stable
`document_processing_limit` recovery guidance and save no document or upload.
Original-PDF page indexing uses the same spawned-process timeout and memory helper
when it re-extracts a stored source. A timeout returns the same fixed recovery code
without changing the document or any saved selection.

DOCX archive admission and ZIP central-directory inspection now occur only inside
the bounded child before python-docx runs. Focused PDF, DOCX, corruption,
output-bound, real timeout/termination, HTTP cleanup and configuration checks pass.
The complete backend regression passes **515 tests with one Windows symlink
privilege skip**. Android's client-owned processing-limit recovery message passes
as part of **141 JVM tests**, lint and debug APK assembly. No live learner document
or external provider was used.

Remaining production controls: PDF object expansion limits, Windows job-object memory caps,
reverse-proxy ingress limits, load tests and retained-data policy. Preflight is not
a complete hostile-document sandbox or proof of production readiness.
