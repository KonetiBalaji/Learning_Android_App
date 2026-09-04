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
process boundary. POSIX workers request a 1 GiB address-space ceiling. Windows
workers create a private Job Object before parsing, apply a 1 GiB per-process
memory limit, set kill-on-job-close, and assign the parser process. Failure to
create, configure or join that job fails parsing closed. Child exceptions and parser details never cross
the boundary. Time/output violations return stable
`document_processing_limit` recovery guidance and save no document or upload.
All API worker processes that share the runtime database jointly admit at most
`LEARNING_MAX_CONCURRENT_DOCUMENT_PARSERS` parser children (2 by default). A
thread-local bounded semaphore provides an immediate first guard, while atomic
SQLite leases enforce the host-wide total across workers. Leases last ten seconds
longer than the configured parser timeout and expired leases are removed during
the next admission, so a terminated API worker cannot permanently consume a slot.
When all slots are occupied, uploads and PDF page indexing fail immediately with 503,
`X-Learning-Error: document_processing_busy`, and `Retry-After: 2`; no new upload
or selection is saved. All workers on a host must use the same runtime database
and configured limit; separate deployments need independent host budgets.
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

On 2026-09-04, focused Windows tests proved a spawned worker can create and join the
configured Job Object, normal isolated PDF extraction/page selection still works,
and a child capped at 256 MiB receives `MemoryError` instead of completing a 512 MiB
allocation. Six isolation tests and sixteen combined isolation/PDF-page tests pass.
The complete backend regression passes **533 tests with one existing Windows
symlink-privilege skip** and the known Starlette/httpx deprecation warning.

On 2026-09-04, the per-process admission gate was verified at its capacity and
configuration boundaries, through upload cleanup and isolated PDF page parsing.
Android verified the retryable 503 recovery code without exposing a response
body. The complete backend regression passes **540 tests with one existing
Windows symlink-privilege skip**; Android unit tests, lint, and debug APK assembly
pass.

Remaining production controls: deeper PDF object-expansion adversarial coverage,
reverse-proxy ingress limits, sustained hostile-parser load tests and retained-data policy. Preflight is not
a complete hostile-document sandbox or proof of production readiness.
