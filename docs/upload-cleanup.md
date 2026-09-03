# Recoverable upload cleanup

Document/account deletion now records each stored upload path in
`pending_file_deletions` in the same SQLite transaction that removes document
access and dependent records. The queue has no account foreign key, so deleting
an account cannot erase its pending cleanup jobs.

After commit, cleanup attempts up to 100 queued files. Startup also drains one
batch, then the application worker retries a batch every 60 seconds while the
server is running. Jobs are ordered by attempt count to avoid repeatedly blocked
files preventing new jobs from running. Missing files count as successful cleanup.
A failed unlink retains the job with a generic error category and attempt count.
No raw exception text or file paths are logged; a warning reports the pending count.

Targets must resolve directly inside the configured uploads directory. Outside
paths and paths still referenced by documents remain queued without deletion.
Each job is checked and removed within an immediate SQLite transaction; concurrent
workers tolerate jobs already removed by another worker. There are no recursive
deletions or directory scans. Upload storage must remain service-owned; hostile
filesystem replacement and aliasing are not addressed by this application check.

The unchanged 204 API response means access removal and a durable cleanup request,
not a guarantee that every physical byte was removed synchronously. Normal file
removal is immediate; persistent permissions/storage failures require operator
repair. Operators can inspect aggregate pending work using:

```sql
SELECT last_error, COUNT(*), MAX(attempts)
FROM pending_file_deletions GROUP BY last_error;
```

Verification: **81 backend tests passed** on 2026-09-03. Failure injection covers
document and account unlink failures followed by actual application startup
recovery, transactional rollback, missing files, live-reference protection,
outside-path rejection, and periodic-worker retry/cancellation under simulated
database contention. Existing deletion/cascade/isolation tests continue to pass.
The worker scheduling test uses a controlled clock, not a minute-long live test.

Production acceptance still requires real permission/disk-failure drills, backlog
alerting and deletion SLAs, deployment/restart checks, and backup retention policy.
Legacy orphan files created before this queue are not automatically discovered.
This does not erase provider records or backups, or establish a retention policy.

## Failed uploads

Extraction and minimum-text validation now finish before the source file is
written. A partial filesystem write or failed document persistence triggers
cleanup of the uncommitted upload. Cleanup first takes a database write lock and
checks for a live document reference, preserving the file if a commit outcome
was uncertain but the record exists. An unreferenced file is removed immediately;
if locked, its path is queued for retry. Storage/database failures return a safe
503 message without raw filesystem or database details.

If the database cannot be accessed to establish whether a file is referenced,
cleanup preserves the file and emits a generic critical operator log. It does
not guess and delete a potentially live file. This condition needs operator repair.
A hard process crash between file creation and database commit is still an
unreconciled window; no claim of universally orphan-free storage is made.

On 2026-09-03, **85 backend tests passed**. New failure injections cover commit
rollback with normal/locked files, eventual queued cleanup, partial writes,
invalid content never written to upload storage, sanitized error responses and
preservation of live referenced files. Real disk-full/permission drills and
process-crash reconciliation remain production gates.
