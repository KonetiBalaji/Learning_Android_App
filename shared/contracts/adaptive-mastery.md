# Adaptive mastery API contract

All routes require the bearer token returned by registration or login. Provider credentials remain on the backend.

| Route | Purpose | Important result |
| --- | --- | --- |
| `POST /v1/mastery/diagnostics` | Start a grade, subject, and chapter session | Session id and first question, without the answer |
| `POST /v1/mastery/sessions/{id}/diagnostic-answer` | Record one diagnostic answer | Correctness plus `next_question`, `tutor`, or `mastery` action |
| `POST /v1/mastery/sessions/{id}/practice` | Evaluate a guided practice response | Retry hint or rewrite action |
| `POST /v1/mastery/sessions/{id}/rewrite` | Evaluate the learner's own explanation | Mastery evidence, confidence, coaching, and unlock signal |
| `GET /v1/mastery/sessions/{id}` | Recover an owner-scoped session without generation | Grade, chapter, pending question, persisted tutor, coaching rounds and phase |
| `GET /v1/progress/dashboard` | Aggregate owner-scoped learning evidence | Subject scores, chapter progress, weak areas, recommendations |

The OpenAI provider generates grade-aware curricula using strict Structured Outputs. Every diagnostic is validated for exactly three unique questions, four unique choices, a matching correct answer, complete teaching support, and concept-specific reinforcement answers before it is stored. The deterministic offline provider supports Mathematics/Fractions; unsupported offline curriculum returns HTTP 422 rather than inventing content.

## Progression and recovery

A successful rewrite demonstrates the current concept only. Its `next_action`
is `next_question` until every assessment item has been resolved. Only then are
`mastery_achieved` and `next_chapter_unlocked` true and `next_action` is `mastery`.
The optional `next_question` uses the same public question schema as diagnostics.
`mastery_score` measures resolved assessment items / total items; it is not a
calibrated exam prediction or probability of understanding the entire curriculum.

The resume response contains no undisclosed correct options. Tutor content is
saved before committing a wrong-answer transition and replayed without another
provider request. A provider-generation failure leaves the diagnostic retryable.
The client maps explicit server phases and rejects unknown phases.

Dashboard and weekly-report routes accept `?grade=8` (valid range 1–12). Chapter
entries include `grade`. Owner and grade boundaries both apply; student UI must
not substitute static progress values. The unfiltered dashboard keeps grades as
separate chapter entries. Subject percentages summarize assessed chapters, not
an authoritative curriculum-wide completion denominator.

Still outstanding: mutation idempotency/concurrency protection, durable document
quiz recovery, full account-scoped profile/preferences, secure token storage,
server-enforced curriculum prerequisites and evaluation calibration.
