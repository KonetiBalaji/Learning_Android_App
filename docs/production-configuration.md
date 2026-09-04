# Backend production configuration gate

Status: startup validation implemented and automated locally. No production host,
TLS proxy, persistent volume, secret manager or deployed instance is configured.

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

Optional Google sign-in and throttle settings remain as documented elsewhere.
Never place the JWT secret or provider key in Git, the Android APK, a deployment
manifest, command-line arguments, logs or health-check output.

Production startup refuses the development JWT secret, missing/relative runtime
storage, missing or malformed release revision, deterministic AI mode, or a missing
provider key. Staging enforces explicit storage, secret and revision but permits the
deterministic provider for pre-provider exercises. Unknown environment names fail.

Provider-backed document generation, diagnostics, explanations, tutor questions,
fresh practice and rewrite assessment share an atomic UTC-day counter per account.
Admission happens before provider work. Replays that return an already-committed
quiz or tutor turn do not consume another operation; provider attempts do, including
attempts that later fail validation, because they incur cost. At the configured cap,
the backend returns 429 with seconds-until-next-UTC-day and a fixed non-sensitive
error code. Android shows accurate next-day guidance and preserves existing state.
Deterministic QA does not consume this quota. Account deletion cascades its counters.
This bounds request count, not tokens or currency; host-level spend alerts and a
provider project budget remain production requirements.

Each HTTP completion also emits a privacy-safe structured event with a bounded
correlation UUID, route template, method, status and duration. The same request ID
is returned to the caller. Raw paths, queries, headers, bodies, identities, content
and exception text are excluded; see `operational-observability.md`. The production
host must still provide a protected log sink, retention, metrics and alerts.

`GET /health` returns only safe deployment identity: status, environment, revision,
provider name and model. A deployment verifier must compare its revision to the
private APK candidate manifest and expected Git commit before testing. A healthy
response proves process readiness only; it does not prove migrations, model quality,
storage durability, backup/restore, TLS routing or capacity.

Configuration and quota tests cover the valid production profile, each required
input, invalid limits, UTC rollover, owner isolation, pre-provider rejection and
deterministic bypass. Real production acceptance still
requires the user-confirmed host/domain, TLS and proxy configuration, encrypted
persistent storage, secret manager, backup/restore drill, retention decision,
monitoring/alerts, provider project-budget alerts, rollback and UAT-approved APK.
