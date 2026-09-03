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

Remaining production controls: isolated extraction workers with time/memory caps,
limits before ZIP central-directory parsing, PDF page/object/text expansion limits,
reverse-proxy ingress limits, load tests and retained-data policy. Preflight is not
a complete hostile-document sandbox or proof of production readiness.
