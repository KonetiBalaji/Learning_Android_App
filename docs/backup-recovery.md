# Offline local backup and recovery

`backend/app/runtime_backup.py` provides `backup`, `verify` and `restore` commands
for the current SQLite/upload runtime. It does not deploy infrastructure, contact
an AI provider, read `.env.local`, manage credentials, schedule backups or switch
the running service. Use only trusted bundles on operator-controlled storage.

## Required operating conditions

- Stop **all** API workers, upload requests and cleanup jobs before backup or
  restore. `--offline-confirmed` is an operator acknowledgement, not automatic
  process detection or a cross-service lock. SQLite gives a consistent database
  snapshot, but concurrent filesystem changes cannot be made atomic with it.
- Keep the source, bundle and destination immutable to other processes throughout
  copying and verification. Symlink/junction checks are not protection against an
  adversary who can swap local paths during the operation.
- Use encrypted, access-controlled storage. These bundles are **not encrypted by
  the tool**: they contain emails, password hashes, source text, learner answers,
  assessment history and uploads. SQLite free pages can contain historical data.
  POSIX directory mode requests do not establish Windows ACLs. Do not commit,
  publicly share or upload bundles to unapproved storage.
- Use the same application revision and compatible OS/path conventions for the
  first recovery drill. Absolute stored paths are normalized at backup creation;
  bundle paths are portable, but cross-OS recovery is not yet tested. Database
  schema migration compatibility must be tested separately before upgrades.
- Choose a destination that does not exist, with an existing parent directory,
  outside the source directory. Existing destinations and overlapping trees are
  rejected. There is no overwrite option and no automatic deletion/cleanup.

## Commands

From the repository's `backend` directory, replace each example path with an
explicit operator-approved path. The example drive is not a configured host.

```powershell
uv run python -m app.runtime_backup backup 'D:\secure\runtime' --destination 'D:\secure\backup-001' --offline-confirmed
uv run python -m app.runtime_backup verify 'D:\secure\backup-001'
uv run python -m app.runtime_backup restore 'D:\secure\backup-001' --destination 'D:\secure\restore-drill-001' --offline-confirmed
```

Success exits 0; failure exits 1 with a generic message that avoids printing
learner content or secret values. Failure may leave a partial destination for
operator inspection. Never start the application against a partial restore or
retry into that directory; select a new destination after resolving the cause.
`RESTORE_COMPLETE` is written only after the restore checks finish. It is an
operator marker, not a startup guard or production acceptance certificate.

## What is preserved and checked

- SQLite's backup API includes committed WAL data. Integrity and foreign-key
  checks must pass. All tables are retained, including authentication hashes,
  mastery/coaching, answer history, idempotency keys and study intervals.
- Only uploads referenced by live document rows are copied. Missing referenced
  files, paths outside configured uploads, unsafe filenames, links, path
  collisions and live files simultaneously queued for deletion fail closed.
- Deleted/unreferenced file bytes and environment/configuration files are not
  copied. Pending deletion rows remain, with remapped paths; restoration does not
  bring their deleted files back. This does not erase historical database pages.
- Stored upload paths are rewritten to `uploads/<filename>` in the snapshot and
  to absolute destination paths during restore. Source data is not rewritten.
- A versioned format-2 manifest is written last, with a timezone-aware creation
  time, SHA-256 and byte counts for the database and each upload. Restore remains
  compatible with format 1, but retention pruning rejects those legacy bundles
  because they have no enforceable creation timestamp. Verification rejects changed/missing/unlisted files,
  unsafe paths and inventory mismatches against the database. Checksums detect
  accidental corruption, **not malicious modification of the bundle/manifest**.

## Recovery and release gates

After a successful restore, configure an isolated service with the restored
`LEARNING_RUNTIME_DIR`, a separately managed test JWT secret and deterministic AI
mode. Do not expose production learner data in a public drill. Verify login,
owner isolation, document/quiz resume, mastery state, reports and deletion, then
stop the drill service. Actual cutover, DNS, JWT-secret handling, rollback and
retention/deletion propagation require a production runbook and user-confirmed
host. Rotating the JWT secret invalidates existing bearer tokens, not passwords.

Restoring an older backup can reintroduce accounts/data deleted after its snapshot.
Before any production cutover, reconcile post-snapshot deletion requests. New
bundles can be previewed and explicitly pruned with `runtime_backup prune` and the
configured 1–365 day retention; see `docs/data-retention.md`. Automated scheduling,
encrypted/offsite storage,
restore timings/data-loss targets, disk-full/crash drills, alerts and operator
UAT are still open. This tool does not satisfy the full SEC-02 or PROD-01 gate.

## Local QA

`uv run pytest tests/test_runtime_backup.py -q` covers table preservation, path
remapping, WAL commits, overwrite/overlap rejection, corrupt/incomplete bundles,
traversal, missing files and broken foreign keys. Its API recovery drill stops the
source app, backs up/restores synthetic data, starts the restored app, verifies
password login, unchanged quiz/tutor state, other-owner denial and deletion of the
restored upload while retaining the original runtime and bundle. No live AI calls
or real learner backups are used. The symlink creation test is skipped on Windows
hosts without that privilege; this is a remaining verification gap, not a pass.

On 2026-09-03 the full backend regression suite passed: **212 passed, 1 skipped**
(the symlink privilege check), with one existing Starlette/httpx deprecation
warning. This includes successful CLI backup/verify/restore, safe CLI failure
output and the restored-app drill above. Android and real-host recovery were not
tested in this change; no existing runtime was backed up, restored or stopped.
