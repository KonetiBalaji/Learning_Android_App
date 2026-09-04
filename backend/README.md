# Learning API

This is the local-development backend for the Android MVP. It owns accounts, document files, extracted text, chapter structure, generated quiz sessions, answer evaluation, and progress records. It deliberately does not contain an LLM provider key. When no approved provider is configured, it creates deterministic, source-grounded multiple-choice questions from the selected material so the whole learning loop can be exercised safely.

## Run locally

```powershell
cd backend
uv sync --group dev
$env:LEARNING_JWT_SECRET = "replace-with-a-long-random-development-secret"
uv run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API.

The backend automatically loads `backend/.env.local`. To enable live tutoring, keep these values only in that ignored file:

```dotenv
OPENAI_API_KEY=your-project-key
OPENAI_MODEL=gpt-5-mini
```

Live calls use the OpenAI Responses API with strict structured output and `store=false`. OpenAI generates grade-aware diagnostic banks for the selected subject and chapter, and each validated bank is frozen with its session so questions cannot drift between answers. If the provider is temporarily unavailable or returns invalid output, the validated deterministic Fractions tutor remains available. Tests always force deterministic mode and never consume API credits.

## Test

```powershell
uv run pytest
```

## Security boundary

- Passwords are salted and hashed with PBKDF2-HMAC-SHA256.
- Access tokens are signed JWTs with an expiry.
- Every document and quiz lookup verifies ownership.
- Uploads are limited to PDF, DOCX, and TXT and capped at 50 MB.
- Uploaded material and the SQLite database stay under `backend/.runtime/`, which is ignored by Git.

This is a local MVP. Before any public deployment, replace the local file store with managed encrypted storage, move the signing secret to a secret manager, introduce rate limiting, and configure retention/deletion operations for the deployed environment.

## Staging and production startup

Non-development startup is fail-closed. Configure an explicit absolute durable
runtime directory, a random JWT secret of at least 32 characters and the exact
40-character Git revision. Production additionally requires
`LEARNING_AI_MODE=openai` and a server-side `OPENAI_API_KEY`. See
`../docs/production-configuration.md` for the complete gate and remaining host
requirements. `/health` exposes the safe environment/revision identity needed to
match a backend to a private APK candidate; it never returns secret values.

Provider-backed operations are limited per authenticated account and UTC day with
`LEARNING_MAX_AI_OPERATIONS_PER_OWNER_PER_DAY` (default 200). The counter is stored
in the runtime database and applies before external provider work; configure
provider-side project budgets and alerts as an independent production backstop.
