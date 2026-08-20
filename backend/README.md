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

