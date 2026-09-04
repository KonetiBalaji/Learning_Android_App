# Backend production configuration gate

Status: startup validation and a locked non-root container are implemented and
automated. No production host, TLS proxy, persistent volume, secret manager or
deployed instance is configured.

Set the following through the chosen host's secret/configuration facility:

- `LEARNING_ENVIRONMENT=production`
- `LEARNING_RUNTIME_DIR`: explicit absolute path on the durable mounted volume
- `LEARNING_JWT_SECRET`: random value of at least 32 characters
- `LEARNING_RELEASE_REVISION`: exact 40-character lowercase Git commit
- `LEARNING_TOKEN_MINUTES`: 1 through 43200; default is 1440
- `LEARNING_MAX_DOCUMENTS_PER_OWNER`: default 100
- `LEARNING_MAX_DOCUMENT_BYTES_PER_OWNER`: default 2 GiB
- `LEARNING_MAX_UPLOAD_BYTES`: default 50 MiB and never greater than owner bytes
- `LEARNING_AI_MODE=openai`
- `OPENAI_API_KEY`: server-side secret
- `OPENAI_MODEL`: reviewed supported model, currently `gpt-5-mini`
- `LEARNING_MAX_AI_OPERATIONS_PER_OWNER_PER_DAY`: 1 through 100000; default 200
- `LEARNING_ORPHAN_UPLOAD_GRACE_HOURS`: 1 through 720; default 24
- `LEARNING_GUARDIAN_INVITATION_RETENTION_DAYS`: 1 through 365; default 30
- `LEARNING_BACKUP_RETENTION_DAYS`: 1 through 365; default 30; must match the scheduled verified backup-prune job
- `LEARNING_DOCUMENT_PARSE_TIMEOUT_SECONDS`: 1 through 120; default 15
- `LEARNING_MAX_CONCURRENT_DOCUMENT_PARSERS`: 1 through 16; default 2 across API workers sharing the runtime database
- `LEARNING_WEB_CONCURRENCY`: 1 through 8 in the Linux production container;
  default 1. Set from measured host CPU/memory and database contention, never from
  client input. Direct Windows development runs fail fast above one worker because
  Uvicorn shared-socket multiprocessing is not reliable there

Optional Google sign-in and throttle settings remain as documented elsewhere.
Never place the JWT secret or provider key in Git, the Android APK, a deployment
manifest, command-line arguments, logs or health-check output.

Production startup refuses the development JWT secret, missing/relative runtime
storage, missing or malformed release revision, deterministic AI mode, or a missing
provider key. Staging enforces explicit storage, secret and revision but permits the
deterministic provider for pre-provider exercises. Unknown environment names fail.
At startup, old unreferenced files matching the service-owned upload naming contract
are recoverably queued after this grace period; it does not expire valid documents.

Provider-backed document generation, diagnostics, explanations, tutor questions,
fresh practice and rewrite assessment share an atomic UTC-day counter per account.
Admission happens before provider work. Replays that return an already-committed
quiz or tutor turn do not consume another operation; provider attempts do, including
attempts that later fail validation, because they incur cost. At the configured cap,
the backend returns 429 with seconds-until-next-UTC-day and a fixed non-sensitive
error code. Android shows accurate next-day guidance and preserves existing state.
Deterministic QA does not consume this quota. Account deletion cascades its counters.
This bounds request count, not tokens or currency; host-level spend alerts and a
provider project budget remain production requirements. Every provider response
also has a code-owned maximum output-token ceiling: 2,048 for one tutor lesson,
rewrite, practice item, or conversation reply; 4,096 for an independent review;
8,192 for a three-item diagnostic bank; and 16,384 for a document quiz of up to
twenty questions. Automated source inspection fails if any provider response call
omits a ceiling. These are per-request safety bounds, not a substitute for the
provider project's currency budget and alerts.

Each HTTP completion also emits a privacy-safe structured event with a bounded
correlation UUID, route template, method, status and duration. The same request ID
is returned to the caller. Raw paths, queries, headers, bodies, identities, content
and exception text are excluded; see `operational-observability.md`. The production
host must still provide a protected log sink, retention, metrics and alerts.

Application-level body admission rejects declared and streamed requests above
`LEARNING_MAX_UPLOAD_BYTES` plus a fixed 256 KiB multipart envelope before route
handling. This protects direct/container operation from unbounded multipart spooling
and retains the correlated Support ID on rejection. The production TLS proxy must
set an equal or tighter body-size limit and a measured request timeout; this control
does not replace edge bandwidth, connection, slow-client or denial-of-service limits.

`GET /health` returns only safe deployment identity: status, environment, revision,
provider name and model. A deployment verifier must compare its revision to the
private APK candidate manifest and expected Git commit before testing. A healthy
response proves process readiness only; it does not prove migrations, model quality,
storage durability, backup/restore, TLS routing or capacity.

`GET /ready` is a stricter deployment/readiness probe. It fails with a generic 503
unless the required runtime schema exists, SQLite passes a bounded quick integrity
check, an immediate database write transaction can be acquired, and a flushed
probe file can be created and removed on the configured upload volume. Its success
payload contains only environment, revision, and the fixed check names `database`
and `upload_storage`. It does not expose paths, errors, record counts, or content.
Use health for process liveness and readiness for deployment admission.

## Reproducible backend image

Build `backend/Dockerfile` from the repository root. It installs the locked
runtime dependency set, runs as the unprivileged `learning` user, writes learner
state only below the `/runtime` volume, disables raw Uvicorn access logs, and uses
`/ready` for its container health check. The image deliberately contains no
configuration or secrets. Mount a durable volume at `/runtime` and inject all
settings through the host's protected configuration facility.

The hosted `backend-container` quality job builds the image, starts two validated
API workers with a read-only root filesystem and a dedicated shared runtime volume,
then verifies both worker processes, the exact production revision, database/upload
readiness, and bounded concurrent traffic. This is repeatable
packaging evidence only. It does not prove volume durability, encryption, TLS,
trusted-proxy behavior, provider access, long-duration capacity, monitoring, or
deployment on a user-owned host.

`uv run python -m app.release_candidate <manifest> --expected-environment
production` performs that comparison and independently rehashes the APK. It also
rejects placeholder/local endpoints and a production health response that does not
identify the reviewed OpenAI provider and model. It also requires `/ready` to prove
the matching revision's database and upload volume are currently ready. Run it from `backend`; see
`private-apk-release.md`. A pass binds an artifact to one reachable deployment but
does not replace the remaining operational or human gates.

Configuration, readiness, and quota tests cover the valid production profile, each required
input, invalid limits, UTC rollover, owner isolation, pre-provider rejection and
deterministic bypass. Real production acceptance still
requires the user-confirmed host/domain, TLS and proxy configuration, encrypted
persistent storage, secret manager, backup/restore drill, retention decision,
monitoring/alerts, provider project-budget alerts, rollback and UAT-approved APK.
