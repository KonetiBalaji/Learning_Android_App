# API workflow

Run `scripts/start-backend.ps1` from PowerShell. The default address is `http://127.0.0.1:8000`. Interactive API documentation is at `/docs`; the machine-readable source of truth is `shared/contracts/openapi.json`, regenerated with `.venv/Scripts/python scripts/export-contract.py`.

1. `POST /auth/register` or `/auth/login` with `username` and `password` returns a bearer token. Usernames contain letters, digits, `_`, `.`, or `-`; passwords require 10–128 characters. Authentication attempts are limited to 10 per IP per minute in one server process.
2. Send `Authorization: Bearer <token>` on all document, quiz, progress, and deletion requests.
3. `POST /documents` accepts multipart field `file` and returns document metadata and detected sections. `GET /documents` lists only the owner's documents.
4. `POST /documents/{id}/quizzes` accepts, for example:

```json
{
  "count": 10,
  "question_type": "multiple_choice",
  "difficulty": "easy",
  "selection": {
    "section_ids": [],
    "page_start": null,
    "page_end": null,
    "topic": ""
  }
}
```

An empty section list selects the whole document. Page numbers are one-based PDF pages. Section, page, and topic restrictions are combined. Local mode supports Easy and treats Mixed as Easy recall practice. The Android UI offers Easy only until AI mode is configured.

5. `GET /quizzes/{id}` returns only the current question and any already-submitted feedback. `POST /quizzes/{id}/answers` accepts `question_id` and zero-based `choice`. Resubmitting the same answer returns the saved feedback; changing it returns 409.
6. `POST /quizzes/{id}/next` accepts `expected_index`, the zero-based current position. Repeating an already-applied advance returns the current snapshot without skipping another question. Advancing without answering returns 409.
7. The completed snapshot has `complete=true`. `GET /quizzes/{id}/results` returns score, accuracy, concept counts, and mistake details. `POST /quizzes/{id}/retry` starts a quiz containing only incorrect questions.
8. `GET /documents/{id}/passages/{source_id}` opens the source passage. `GET /progress` returns completed session history, chapter progress, and resumable quizzes.
9. `DELETE /documents/{id}`, `DELETE /account`, and `DELETE /auth/session` provide document deletion, account/data deletion, and sign-out.

Unauthenticated requests return 401. Another owner's identifiers return 404. Invalid uploads/selections/unsupported generation return 422, inconsistent quiz transitions return 409, and rate limiting returns 429. The health endpoint is public and reports the configured generation mode; `ai_configured` indicates configuration, not a successful live credential check.
