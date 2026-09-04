# Owner-scoped document storage quota

Each learner may retain at most 100 uploaded documents and 2 GiB of original file
bytes by default. The individual upload ceiling remains 50 MiB. Operators may set
`LEARNING_MAX_DOCUMENTS_PER_OWNER`, `LEARNING_MAX_DOCUMENT_BYTES_PER_OWNER` and
`LEARNING_MAX_UPLOAD_BYTES`; invalid, inverted or extreme values fail startup.

After format, extraction and content validation, the server begins an immediate
SQLite write transaction, reads that owner's active document count and stored-byte
sum, checks the incoming file, and inserts its document row with the measured file
size. This serialization prevents two concurrent uploads from both observing one
remaining slot. Any losing/rejected upload removes its uncommitted file through the
existing safe cleanup path. Deleting a document releases its count and byte usage.
Other owners have independent capacity.

Count and byte exhaustion return HTTP 422 with stable `document_count_limit` or
`document_bytes_limit` headers. Android maps only those exact codes to client-owned
instructions to delete unused material; response bodies and configured quota values
are not displayed. Unknown or misplaced headers retain the generic safe message.

Existing databases are migrated with a non-negative `stored_bytes` column. Startup
backfills rows from actual files. Missing legacy files remain zero until existing
cleanup/reconciliation resolves them; this is conservative for availability but can
temporarily undercount a broken legacy row.

This is an adaptation of OpenMAIC's owner-scoped material quota pattern; exact
provenance and architectural differences are in `openmaic-provenance.md`. It limits
retained application storage, not request rate, OpenAI spending, filesystem free
space, backup size or hostile decompression resources. Production quota values,
alerts and capacity still require host/budget decisions.

Verification on 2026-09-04: 444 backend tests passed with one existing Windows
skip. Android passed 126 JVM tests, lint and debug APK assembly. These are automated
engineering checks; quota recovery has not yet been accepted on a physical device
or in user UAT.
