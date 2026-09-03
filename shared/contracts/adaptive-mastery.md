# Adaptive mastery API contract

All routes require the bearer token returned by registration or login. Provider credentials remain on the backend.

| Route | Purpose | Important result |
| --- | --- | --- |
| `POST /v1/mastery/diagnostics` | Start a grade, subject, and chapter session | Session id and first question, without the answer |
| `POST /v1/mastery/sessions/{id}/diagnostic-answer` | Record one diagnostic answer | Correctness plus `next_question`, `tutor`, or `mastery` action |
| `POST /v1/mastery/sessions/{id}/practice` | Evaluate a guided practice response | Retry hint or rewrite action |
| `POST /v1/mastery/sessions/{id}/rewrite` | Evaluate the learner's own explanation | Mastery evidence, confidence, coaching, and unlock signal |
| `GET /v1/progress/dashboard` | Aggregate owner-scoped learning evidence | Subject scores, chapter progress, weak areas, recommendations |

The OpenAI provider generates grade-aware curricula using strict Structured Outputs. Every diagnostic is validated for exactly three unique questions, four unique choices, a matching correct answer, complete teaching support, and concept-specific reinforcement answers before it is stored. The deterministic offline provider supports Mathematics/Fractions; unsupported offline curriculum returns HTTP 422 rather than inventing content.
