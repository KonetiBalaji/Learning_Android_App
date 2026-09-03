# Lesson-scoped tutor questions (server implementation)

## Repeatable Android conversation workflow QA

Start the isolated backend with `uv run python scripts/serve_qa.py --qa-only`,
then run `scripts/qa-mastery-resume.ps1 -ResetTestAppData -VerifyTutorConversation`.
This requires the dedicated LearnSmart_API36 emulator and resets only its app's
synthetic local test state. It installs the current debug APK and creates a fresh
test account. The QA provider returns a visibly labelled scripted reply; the
question `QA unavailable` deliberately fails. Production provider code does not
import this fixture and no external AI requests are made.

The script checks typed question/reply, process restart and saved history,
unavailable reply UI, filling a retry draft without auto-sending, exactly one
completed and one failed persisted turn, and unchanged tutor/mastery state.
Screenshots are local generated artifacts. The first execution reached the
failure/retry UI but its final assertion incorrectly wrapped PowerShell's JSON
array; read-only database inspection confirmed the expected two turns. That run
was not counted as an end-to-end pass, and the array handling was corrected.

The corrected fresh-account run passed on API 36 using the debug APK from
`a2517b8`. Exactly two turns (one complete, one failed) remained after choosing
the draft-only retry control; the learning session stayed `tutor` with score 0.
`artifacts/qa-tutor-conversation.png` and
`artifacts/qa-tutor-conversation-failure.png` were visually inspected: disclosure,
question/reply, failure guidance and retry draft are readable at the tested size.
These generated screenshots are not committed. Transient UI null-root errors
were retried using fresh hierarchies. The isolated QA server was refreshed for
the new routes/fixture; no production host or credentials were changed.

Full backend regression with the two QA-fixture tests: 403 passed, one existing
Windows symlink-privilege skip, and the existing Starlette/httpx warning. These
checks do not establish live answer quality, real dictation, voice cancellation,
pending/network-loss recovery, playback quality or user acceptance.

This adds follow-up conversation, separate from diagnostic/practice/rewrite
assessment. Android text/voice controls and reply read-aloud are implemented;
focused typed-conversation device QA passed as recorded above. Broader device QA
and live conversational-answer evaluation remain pending.

## Android integration

The tutor lesson offers **Ask the tutor a question**, opening a separate conversation
screen with saved current-state history. Learners can type or dictate a bounded
question, review it, and explicitly send. The screen discloses AI transmission,
storage and fallibility, discourages private information, distinguishes unsupported
answers from provider failure, and offers read-aloud for the latest complete reply.

During an uncertain/pending response, the question is locked and **Check reply**
reuses the same UUID. In-process navigation back/reopen preserves that UUID if
history has not yet acknowledged it; a different lesson context clears it.
Completed/failed replies replace their pending row rather than duplicating it.
An acknowledged failure offers **Use this question again**, which fills the draft
for review, not automatic sending; sending again uses a new request. No polling
or automatic provider retry is added by Android.

Drafts and uncertain requests live in the ViewModel, surviving configuration
changes but not process death. After process restart, resume the lesson and reopen
conversation to reload server history, including reserved pending turns. An
unacknowledged request that never reached server reservation cannot be reconstructed
from history. No plaintext chat draft is written to Android preferences. Full
process-loss/transport timing, account changes, voice cancellation, large text,
TalkBack and spoken reply QA remain to be exercised on-device.

Only the tutor screen exposes entry initially; the backend also accepts questions
during practice. Conversation itself cannot move assessment state. Device speech
may use an online service, with the existing disclosure and review-before-send.
New policy/model tests cover pending identity, merge behavior, invalid reply shapes
and Unicode-safe question limits; they are not end-to-end HTTP/device proof.

Android verification: `:app:assembleDebug :app:testDebugUnitTest :app:lintDebug`
passed with 120 JVM tests. No live provider request was made for this Android
implementation slice. API-key skill safeguards keep the previously authorized
key on the server; the Android app contains no provider credential.

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
