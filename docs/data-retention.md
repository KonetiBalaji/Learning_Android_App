# Learner data retention policy

## Active data

- Account profile, learning history, mastery evidence, quiz history and tutor
  conversations are retained until the learner deletes the account.
- Uploaded documents are retained until the learner deletes that document or the
  account. There is no silent inactivity expiry for active study material.
- A learner deletion request removes database ownership records transactionally.
  Document bytes are queued for immediate filesystem cleanup and retried by the
  service when deletion cannot complete at once.
- Untracked upload files left by a crash are eligible for reconciliation after the
  configured grace period, 24 hours by default.
- Expired guardian invitations are retained only for the configured cleanup period,
  30 days by default. Active guardian links remain until either party revokes them
  or an account is deleted.

The authenticated `GET /v1/privacy/retention` endpoint reports these policies and
the current numeric periods. Android validates the fixed policy vocabulary and safe
ranges before showing it under Settings. The disclosure therefore comes from the
same deployment that stores the learner's data rather than stale APK copy.

## Backups

New offline backup manifests use format 2 and include a timezone-aware creation
timestamp. `LEARNING_BACKUP_RETENTION_DAYS` configures the disclosed service policy
from 1 to 365 days, default 30. Operators must schedule the retention command against
the approved backup root:

```powershell
uv run python -m app.runtime_backup prune 'D:\secure\backups' --retention-days 30
uv run python -m app.runtime_backup prune 'D:\secure\backups' --retention-days 30 --delete-confirmed
```

The first command is a non-destructive preview. The second deletes only direct child
bundles whose valid format-2 manifest timestamp is at or before the cutoff. Every
bundle is fully verified first. Linked paths, corrupt bundles, unsafe retention
ranges and legacy manifests without enforceable timestamps fail the operation. The
command never scans or deletes the runtime itself.

Because backups can restore data deleted after a snapshot, production operations
must run this command on schedule and reconcile any restore against later deletion
requests. Repository implementation is not proof that a future host is scheduled.

## Verification

Automated tests cover authenticated policy disclosure, environment bounds, backup
timestamps, preview, explicit deletion and preservation of a non-expired bundle.
The existing account/document deletion, owner-isolation and recovery suites remain
the evidence for active data. Android tests, lint and debug assembly pass.

The API 36 authentication/profile journey verifies the server-configured 30-day
invitation/backup and 24-hour crash-file disclosure after registration, password
failure/recovery and persisted-session restart. The screenshot is
`artifacts/qa-auth-profile.png`. Production scheduler execution, storage-provider
version deletion, legal/organizational review and user acceptance remain open.
