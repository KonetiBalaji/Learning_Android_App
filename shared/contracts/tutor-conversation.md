# Lesson-scoped tutor questions (server implementation)

This adds follow-up conversation, separate from diagnostic/practice/rewrite
assessment. Android text/voice controls, reply read-aloud and device QA are pending.

Authenticated routes:

- `POST /v1/mastery/sessions/{id}/tutor-questions`: body `request_id` (UUID),
  `expected_state` (current mastery state token), `question` (1–1000 characters,
  not whitespace). Extra fields are rejected.
- `GET /v1/mastery/sessions/{id}/tutor-questions`: current-state history in creation
  order. Other owners receive 404. Questions are accepted only in tutor/practice.

A turn contains `request_id`, `question`, `status` (`pending`, `complete`, `failed`)
and nullable `reply`. A complete reply contains nonblank `answer` (at most 1800
characters) and strict boolean `supported`. That flag is a model judgment about
the supplied lesson, not verified factual confidence. Failure returns no raw
provider error or partial response. No grade, assessment attempt, mastery score,
unlock or coaching round is changed by conversation.

## Persistence and retries

An atomic database reservation precedes provider work. Reusing an ID with the same
question/state returns its stored turn, including pending or failed, without a new
provider call. Reusing it with different content/state returns 409. Only one pending
turn per session is allowed, and all attempts (including failed) count against a
20-turn session limit. This is not an account/monthly quota: new sessions remain
possible and production abuse/cost controls still need work.

Pending reservations older than three minutes become failed on the next POST,
allowing recovery after server process loss. GET does not mutate stale pending
rows. Clients can replay the same POST to resolve stale pending status. Retry of
a failed turn is an explicit new request ID, not automatic retry. Late provider
results cannot overwrite expired requests. The lesson state is rechecked after
provider work; if it changed or was deleted, the reply is discarded.

History is scoped to the exact mastery state token (phase, question, score and
coaching round), so moving phase or changing practice starts a new displayed
conversation. At most six completed prior turns from that state go to the provider.
Persisted turns cascade on session/account deletion. Questions/replies remain in
the local database until deletion; production retention and consent need decisions.
Clients must disclose sending the learner's question to the AI service and should
discourage sharing personal information.

## Provider boundary

The provider gets grade, current concept/explanation/worked example/hint, the
question and bounded history. It does not receive account identity, the diagnostic
answer key, practice key, other chapters or another learner's content. Instructions
require lesson grounding, age-appropriate language, clarification/redirect for
unsupported questions, no requests for personal data, and hints rather than writing
assessed answers. These are model instructions, not a guarantee; jailbreak,
out-of-topic, answer-leakage, factual and age-appropriate live evaluations remain.
`store=False` is used. The deterministic provider reports failure, not a fabricated
conversation. Existing OpenAI timeouts/retries apply; no extra provider calls run
under a database lock.

## Verification boundary

HTTP/provider tests cover ownership, state checks, blank/malformed responses,
unchanged mastery, stable replay, history, concurrent pending work, stale reservation
recovery, late state changes, session limits, cascade deletion and withheld fields.
No live conversation quality or Android user journey is verified yet. This is the
server foundation for TUT-06, not completion of conversational/animated teaching.

Full backend command `uv run pytest -q --tb=short`: 401 passed, one existing
Windows symlink-privilege skip, and the existing Starlette/httpx warning. No live
provider calls were made for this implementation slice; the existing authorized
key remains server-only under the API-key skill safeguards.
