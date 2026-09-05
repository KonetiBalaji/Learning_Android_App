# Malformed parser stress smoke

`backend/scripts/parser_stress_smoke.py` exercises the real asynchronous upload
validation boundary with four synthetic truncated/corrupt PDF and DOCX byte
patterns. Each attempt must end as a stable validation rejection or fail-fast busy
response. Unexpected acceptance, timeout, status, stored file or remaining parser
lease fails the run. After stress, an ordinary TXT source must parse byte-for-byte
to prove capacity and worker recovery.

The command is bounded to 20–500 attempts, 2–32 caller threads, a one-to-fifteen
second parser timeout and the production parser capacity of two. It uses a new
temporary SQLite database/upload directory and deletes them after every run. It
prints only aggregate synthetic outcomes.

On 2026-09-04, two complementary Windows runs passed:

- 100 attempts at concurrency 12: 2 isolated-parser rejections, 98 immediate busy
  rejections, zero timeouts, zero leases/files left, exact valid-source recovery.
- 100 attempts at concurrency 2: all 100 inputs reached isolated parsing and were
  rejected, zero busy responses/timeouts/leases/files, exact valid-source recovery;
  duration 39.083 seconds.

The first harness version incorrectly treated a malformed PDF that PyMuPDF opened
as empty text as low-level acceptance; testing the actual upload validation boundary
proved that it is rejected for insufficient extractable text. A second harness-only
failure found an explicitly unclosed verification connection on Windows; cleanup now
closes it and collects completed-future exception cycles before deleting the runtime.

This is bounded local synthetic stress, not a long-duration soak, malformed-format
fuzzing campaign, memory-pressure benchmark, production-host capacity result or
proof against unknown parser vulnerabilities. Those remain separate security and
deployment gates.
