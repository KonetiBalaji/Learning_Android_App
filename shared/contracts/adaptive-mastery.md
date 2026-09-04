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

Rewrite results additionally return nullable `assessment_points` (0–4),
`assessment_max_points`, and `assessment_feedback`. These describe the learner's
latest explanation, separately from resolved-item `mastery_score`. Resume returns
the last saved explanation's points/feedback. Explicit deterministic testing mode
does not fabricate rubric points. A live evaluator failure returns HTTP 503 and
does not record an attempt or advance phase, so the client can retry its draft.
Scores below full credit receive server-authored hints; the provider's unchecked
comment is not shown. See `docs/openmaic-provenance.md` for upstream attribution.

A successful rewrite demonstrates the current concept only. Its `next_action`
is `next_question` until every assessment item has been resolved. Only then is
`mastery_achieved` true and `next_action` is `mastery`. `next_chapter_unlocked`
is true only when the mastered chapter is an actual prerequisite for another
chapter in the current catalog; mastering an unrelated or terminal chapter does
not claim that a next chapter was unlocked. The authoritative dashboard still
returns the concrete grade-scoped `unlocked_chapter_ids`.
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

Weekly reports return `period_start` and `period_end` in UTC and use the half-open
interval `[period_start, period_end)` spanning exactly seven days. Responses are
dated by attempt time, not by the parent session start. `questions_answered` is
retained for API compatibility but counts diagnostic, practice and rewrite
responses; clients should label it **Learning responses**, not unique questions.
`mastered_chapters` counts unique `(grade, subject_id, chapter_id)` completions
inside the window, including sessions started earlier. A completed status alone
does not qualify unless every stored assessment item has been resolved.
The active-chapter denominator includes starts, responses and completions in the
window. Repeated sessions of one chapter do not multiply this denominator.
`readiness_is_calibrated` is false: the indicator remains a 60% response-accuracy /
40% active-chapter-completion heuristic, not an exam-performance prediction.
No responses produces `insufficient_evidence`. Strongest concepts must have at
least 70% observed response accuracy; weak concepts are below that threshold.
All-time current chapter progress is a separate dashboard metric.

## Adaptive mutation preconditions

Start, resume, diagnostic-answer, practice and rewrite responses include
`state_token`. Treat it as an opaque, session-scoped precondition. Updated clients
send it as `expected_state` in each diagnostic-answer, practice or rewrite body.
Every committed transition changes the token, including incorrect practice and
unsuccessful rewrite attempts. A mismatch returns 409 before provider work or
attempt insertion. Concurrent requests that initially match still compete under
the existing transactional snapshot check; only one may commit.

On an unknown response outcome, retain the original token. A retry must not fetch
a fresh token and silently reapply the old answer. The backend durably keys each
diagnostic-answer, practice and rewrite result by session, operation and the
pre-transition token. An identical retry returns the exact saved response without
another attempt or provider call. Reusing that token with different content returns
409. A genuinely stale token with no matching saved result also returns 409, after
which the client GETs the session and presents its current state. A new intentional
attempt requires the newly observed state token.

The replay row stores a SHA-256 request fingerprint and the learner-visible result
inside the same transaction as the attempt and session update. It is owner-reachable
only through the owning session and cascades on account/session deletion. It belongs
in the same protected backup and retention boundary as learner attempts.

The field is required. Requests omitting it, explicitly sending null, or sending
an empty/oversized value fail validation before endpoint mutation. Current Android
always requires a cached token from start/resume before submitting and clears the
cache on sign-out. All bundled QA callers now follow the same contract. Because an
older APK cannot submit to this backend, distribute the current private APK as the
only candidate when the service is deployed; no production legacy deployment exists.

Simultaneous identical requests commit one attempt and both receive the winning
saved response, but both may begin provider computation before one transaction
wins; provider-work coalescing remains an operational optimization. Broader device
security failure tests and evaluation calibration remain outstanding.
