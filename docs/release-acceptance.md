# LMS delivery requirements and release gates

## Governing scope

Source of truth: the user's original Learn Smart AI brief, including the
diagnostic / tutor / practice / rewrite / mastery loop, Grades 1–12, four subjects,
parent reporting, voice, dark mode, and relevant OpenMAIC adaptations without
cloning the upstream repository. The earlier MVP completion claim is withdrawn.
Suggested technologies are not evidence of implemented features.

Status vocabulary: **partial**, **missing**, **implemented**, **QA verified**,
**UAT accepted**, **production verified**. A build pass alone cannot advance a
feature to UAT accepted or production verified. All release gates below remain open.

## Acceptance ledger

Live tutor-conversation smoke checked one lesson question and two unsupported
requests. It exposed misleading navigation/assessment guidance despite correct
scope flags; unsupported replies now use a fixed truthful recovery message.
Supported-answer quality remains model-dependent. See
`docs/tutor-conversation-live-smoke.md`; this is not teacher UAT or broad accuracy proof.

Conversational tutor server: authenticated lesson-scoped question/history routes,
bounded persisted turns, replay/pending protection and failure recovery implemented.
Replies do not grade or unlock learning. Android lesson-entry conversation screen
now supports typing/dictation, saved history, latest-reply read-aloud and explicit
pending/failed recovery. Live grounded-answer quality, device QA, animation,
consent/retention and broader cost controls remain
open. See `shared/contracts/tutor-conversation.md`; TUT-06 remains partial.

API 36 typed-conversation QA passed sending a question, restoring saved replies
after process restart, displaying unavailability, preparing an explicit retry
without sending, and confirming exactly two saved turns with unchanged mastery.
Reply/failure screenshots were inspected. Scripted QA content only; real speech,
live answer quality, actual TCP loss and UAT remain open. A separate post-commit
503 run verified that Android retained the uncertain question and recovered the
single already-saved turn by request ID without duplicating provider work. See
`docs/tutor-conversation-recovery.md`. Backend regression: 409 passed, one
existing Windows skip.

Read-aloud lifecycle repair stops queued speech when backgrounded or lesson text
changes, ignores stale callbacks, and provides completion/stop/error status with
an accessibility live region. A persistent AI teacher status bar now remains on
every screen, while a larger vector teacher reports ready, thinking and speaking
from actual request/TTS state and animates while active. API 36 verified the bar
across sign-in, grade, subject, diagnostic and tutor screens; speaking/ready frames
were inspected beside playback controls. Android build/lint and 124 JVM tests pass.
Acoustic quality, TalkBack navigation,
phoneme-level lip-sync and broader-device verification remain open; TUT-05 and
TUT-06 are partial. See `docs/voice-recovery.md`.

API 36 follow-up verified read-aloud readiness, background/return stopped state,
no automatic resume, explicit restart/stop and speech-service completion callback.
Stopped/finished screenshots were inspected and readable. Acoustic output,
TalkBack, error injection and conversational teaching remain unverified; see the
voice recovery record for the exact command and limited scope.

Practice matcher hardening: meaningful symbols/word boundaries are preserved,
with persisted opt-in rational equivalence for curated arithmetic and exact
matching for denominator-constrained exercises. Legacy banks remain exact. New
model-generated banks require blind practice-key and format-policy screening
before persistence. Regression and HTTP tests cover accepted/rejected transitions;
broad grading-quality evaluation, on-device verification and UAT remain open.
See `docs/practice-answer-matching.md` for scope and limitations.

Provider-backed non-Fractions lessons can now request fresh practice without a
fixed round cap. Every candidate is independently solved without its proposed key
or hint, fail-closed on repetition/ambiguity/topic/grade/key/hint checks, and
atomically persisted only after the learning-state guard. Fractions retain their
deterministic variants; provider failure keeps the current question. Two live
Grade 8 Cells/English samples passed after one earlier disagreement was rejected.
Backend regression: 418 passed with one existing Windows skip. Broad curriculum,
cost/latency limits, holdout quality, device coverage and UAT remain open; TUT-02
is partial. See `shared/contracts/fresh-practice.md`.

Format-policy repair: explicit review constraint categories plus a limited English
server safeguard now preserve recognized requested formats while allowing numeric
equivalence for unconstrained arithmetic. The controlled live division/denominator/
lowest-terms regression passes; backend QA is 391 passed, one existing skip.
Arbitrary generated-bank quality, multilingual constraints and device QA remain open.

Diagnostic QA now reports content-free rejection codes/indices, and deliberately
corrupted-key evaluations require disagreement at the corrupted item rather than
counting unrelated review rejection as success. This strengthens evaluation
evidence, not a broad model-accuracy or UAT claim. See `docs/diagnostic-answer-review.md`.

| ID | Requirement | Current status | Required acceptance evidence |
| --- | --- | --- | --- |
| AUTH-01 | Email registration and login | QA verified | Physical-device/user acceptance and OEM AndroidKeyStore invalidation exercise |
| AUTH-02 | Google login | Partial | Backend exchange and Android Credential Manager wiring implemented; disabled-build device QA passes. OAuth configuration, real sign-in, lifecycle recovery and user acceptance remain missing |
| CUR-01 | Grade 1–12, subject and chapter selection | Partial | Versioned server catalog and pre-provider allowlisting are API 36 verified; user-confirmed board, authoritative grade-specific coverage and UAT remain open |
| ASM-01 | Diagnostic and correct-answer progression | Partial | Exactly-once submissions, restart recovery, no answer leakage, all question transitions |
| TUT-01 | Age-appropriate tutor explanations and worked examples | Partial | Grounding, factual evaluation, age suitability, provider failure and retry tests |
| TUT-02 | Fresh practice, hints and repeated coaching | Partial | New validated practice items, misconception handling, no automatic chapter mastery after one remediated concept |
| TUT-03 | Interest-personalized examples | Partial | Profile/prompt path plus Android save/clear/restart, post-commit failure recovery and account isolation are API 36 verified; broader live example quality and educator/UAT review remain |
| TUT-04 | Written explanation assessment | Partial | Rubric/eval set, false-pass tests, helpful coaching without treating model confidence as measured reliability |
| TUT-05 | Interactive examples and visible AI teacher | Partial | Math Fractions plus Grade 8 Science Cells, English Grammar and Social Geography have native device-verified explorers; remaining concepts, TalkBack, physical-device and user acceptance are open |
| TUT-06 | Verbal questions and spoken animated explanations | Partial | Conversational tutoring, speech unavailable/cancel/error cases, real audio and animation checks |
| MAST-01 | Mastery, time spent, next chapter unlock | Partial | Durable server-owned grade/account-scoped mastery; all concepts assessed; honest time/score display |
| PROG-01 | Real student subject/chapter progress | Partial | Remove static percentages; backend-derived values survive restart/account switching |
| PROG-02 | Weak concepts and personalized learning path | QA verified | Independent recurring-error counts, remediation clearing, account/grade scope, active-session continuation and prerequisite-aware next diagnostic are backend tested and API 36 verified; educator/UAT review remains |
| PARENT-01 | Parent/teacher dashboard and weekly reports | Partial | Consent-linked separate accounts and read-only grade reports are device verified; identity/child-consent policy, retention, physical-device and UAT remain open |
| PARENT-02 | Exam readiness prediction | Partial | Explicitly labelled heuristic until calibrated against a supplied exam/curriculum dataset |
| DOC-01 | Upload/analyze/select/quiz/feedback/results | Partial | File limits/corruption/password cases, source-grounding checks, deletion, interrupted-flow recovery |
| DOC-02 | Entire document, multiple chapters, section, page range and topic selection | Partial | Backend chapter-set validation; Android multi-selection and persistence; page/section/topic retrieval boundaries and device QA |
| DOC-03 | Question count, difficulty and question-type configuration | Partial | Preset/custom count device QA; easy/medium/hard/mixed difficulty; multiple-choice, true/false and yes/no generation, grading and recovery |
| UX-01 | Mobile-first cards, badges, theme, accessibility | Partial | Both themes, large text, small screens, TalkBack, loading/empty/offline/retry states |
| DATA-01 | Durable state and account isolation | Partial | Server resume contracts, encrypted local state, account switching and forced-process-death tests |
| SEC-01 | Deletion and retention | Partial | Database cascade assertions, file removal, other-owner preservation, retention policy |
| SEC-02 | Production hardening | Partial | HTTPS release guard, offline backup checks, persistent authentication peer throttle, atomic per-account daily AI-operation caps and privacy-safe correlated request events implemented; production proxy/capacity, provider budgets, deployed log sink/alerts and deployment recovery still need verification |
| UP-01 | Traceable OpenMAIC adaptation | Partial | OA-01 grading, OA-02 owner-material quotas and OA-03 bounded native action/highlight patterns are pinned, licensed and tested; this is selective adaptation, not a port |
| QA-01 | Automated regression suite | Partial | Backend, Android unit/instrumentation, AI evals, failure/recovery and security tests |
| UAT-01 | User acceptance | Missing | Testable build, scripted user journeys, issue log, explicit user acceptance |
| PROD-01 | Production deployment | Missing | User-confirmed host/domain/distribution, staging verification, rollback, secrets and operational checks |

Private APK packaging now fails closed without a non-local HTTPS endpoint, a clean
commit and all four environment-only signing inputs. The build helper verifies the
signature and records commit, APK/certificate hashes, APK version and backend URL
without secret values. A disposable-key `assembleRelease`/APK Signature Scheme v2
check passed; this is packaging QA, not an owned production signature, reachable
backend, UAT candidate or deployment. See `private-apk-release.md`.

Backend production mode now fails startup without an explicit absolute runtime
volume, strong non-default JWT secret, full Git revision, reviewed OpenAI mode and
server-side provider key. Health reports safe environment/revision/provider identity
for APK-to-backend reconciliation. Nine configuration tests pass. This prevents
accidental development configuration but does not provide the still-unconfirmed
host, TLS proxy, durable volume, secret manager, quotas, monitoring or recovery
evidence. See `production-configuration.md`.

AUTH-01 now has API 36 evidence for two-account switching and a genuine timed token
expiry. Distinct server interests survived sign-out/sign-in and restart without
cross-account bleed. A one-minute server token then expired naturally; the real
401 cleared encrypted credentials, survived restart signed out, and allowed password
reauthentication before disposable-account deletion. This advances AUTH-01 to QA
verified, not physical-device UAT. See `authentication-recovery.md`.

API 36 authenticated-decryption QA altered a real encrypted session only inside the
dedicated app sandbox. Startup failed closed, displayed safe recovery, cleared both
credential fields across restart and allowed password reauthentication. The synthetic
account was deleted. This covers ciphertext corruption with AndroidKeyStore but not
OEM key invalidation, hardware-backed certification or user UAT; see
`android-session-security.md`. Android 126 JVM tests, lint and debug assembly pass.

OA-02 selectively adapts OpenMAIC's owner-scoped material count/byte quota and
serialized admission pattern. This implementation uses SQLite `BEGIN IMMEDIATE`,
measured file bytes, rejection cleanup and stable Android-owned recovery codes.
Tests cover count/bytes, separate owners, deletion release, a two-request race and
legacy size backfill. No TypeScript, database schema, agent runtime or repository
history was copied. Backend 444 passed with one Windows skip; Android 126 JVM tests,
lint and debug assembly passed. See `openmaic-provenance.md` and
`document-storage-quota.md`.

OA-03 selectively adapts OpenMAIC's typed action, explicit dispatch and
state-driven highlighting concepts into an allowlisted native Cells explorer. It
executes no generated HTML, JavaScript, model action payload or arbitrary coordinate
command. API 36 verified selection/highlighting and a server read proved exploration
left mastery unchanged. Android 128 JVM tests, lint and debug assembly passed;
backend regression remained 444 passing with one existing Windows skip. See
`openmaic-provenance.md` and `cell-explorer.md`. Broader interactive coverage,
curriculum review, physical-device QA and UAT remain open.

## Delivery stages and exit gates

1. **Development:** all requirements mapped; partial features repaired; OpenMAIC
   provenance ledger populated; no placeholders presented as learner evidence.
2. **QA:** repeatable automated checks and device tests, AI quality evaluation,
   failure-path tests, no unresolved release-blocking defects. Record commands,
   dates, exact commit/build, and limitations.
3. **UAT:** deliver a candidate and acceptance script, collect the user's actual
   feedback, fix defects, obtain explicit acceptance. Agent-run QA is not UAT signoff.
4. **Production:** deploy only to the confirmed destination, verify HTTPS,
   configuration, migrations, retention, backup/restore, monitoring, rollback,
   provider limits and Android release distribution. Do not equate a debug APK
   or local server with a production deployment.

## Decisions needed (not blockers for local engineering)

- Curriculum, country/education board and authoritative materials.
- Production hosting/domain (private APK distribution is confirmed).
- Google OAuth project configuration and release signing ownership.
- Parent/teacher access and consent model; retention policy for student material.
- Monthly infrastructure/provider budget and acceptable usage limits.

## Baseline evidence and known defects

- A bounded live `gpt-5-mini` Grade 8 Fractions check generated/reviewed one bank
  and rejected one deliberately incorrect key. Sampled arithmetic was independently
  checked; wording, equivalent-answer grading, production latency, broad accuracy
  and curriculum alignment remain unproven. Evaluator regression suite: 307 backend
  tests passed, 1 existing Windows skip. See `docs/diagnostic-live-smoke.md`.

- Generated diagnostic banks now require a blind answer-key review before
  persistence, with strict rejection of disagreement, ambiguity, off-topic or
  grade-unsuitable judgments and malformed/partial review output. Tests cover
  provider wiring and HTTP persistence denial. This is a model-quality filter,
  not verified curriculum coverage or a guarantee against correlated errors;
  teaching-support validation and live evaluations remain open. See
  `docs/diagnostic-answer-review.md`.

- Uncertain upload responses now direct learners to the library before retrying.
  API 36 QA injected a 503 after the file was saved, verified overlay removal,
  readable recovery copy, library reopening and a single saved document with no
  automatic replay. Android build/lint and 110 JVM tests passed; backend suite:
  288 passed, 1 existing Windows skip. Real network-loss/process-death paths and
  server upload idempotency remain open; see `docs/upload-progress.md`.

- Added Android byte-based upload progress and a distinct server-analysis wait
  phase, with unknown/incorrect-size handling and failure cleanup. Build/lint and
  109 JVM tests passed on 2026-09-03. Follow-up API 36 real-picker QA verified
  the readable analysis-wait overlay under a delayed response and its removal
  before chapter selection. Backend suite with QA fixture checks: 287 passed,
  1 existing Windows skip. Transfer-percentage/failure/accessibility checks
  remain open; see `docs/upload-progress.md`.

- Fixed DOCX body extraction omitting tables: new uploads preserve ordered table
  and nested-cell text, avoid duplicate merged-cell evidence and reject excess
  traversal limits. Existing stored source offsets remain unchanged. Eight new
  tests include a table-only upload/search offset round trip. Backend suite on
  2026-09-03: 285 passed, 1 existing Windows skip. Complex Word layout, device
  rendering and model quality on tables remain unverified; see
  `docs/docx-source-extraction.md`.

- Authentication registration/login/Google exchange now share a persistent,
  bounded peer-admission throttle with generic 429/Retry-After, digest-only records,
  concurrent SQLite enforcement and no direct trust in forwarding headers.
  2026-09-03 backend suite: 277 passed, 1 existing Windows skip, including 11
  new throttle tests. This is not full credential-stuffing/DDoS protection;
  production proxy topology and shared-network capacity remain unverified.
  See `docs/authentication-throttling.md`.

- Existing source commits: `7153b3e` and `3d50b0e`. Earlier 13 backend tests,
  Android build/lint, and selected emulator paths passed; this is not full UAT.
- Baseline student dashboards contained static percentages; current code uses
  grade-filtered backend chapter/subject results. Adaptive session recovery is
  now wired to the server; document-flow recovery is still missing. Shared local
  unlock values are no longer trusted; bearer tokens now use Keystore-backed
  encryption. Profile privacy and additional device-failure testing remain.
- Baseline defect: SQLite foreign keys were enabled during schema creation but
  not each runtime connection, allowing dependent records to survive deletion.
  Fixed with per-connection enforcement and explicit transaction rollback.
- Earlier OpenMAIC integration claims were unsupported. OA-01 now records an
  actual source-informed grading adaptation; independent features and remaining
  upstream engines must not be described as imported.

## Work log

- Added disabled-by-default Google ID-token backend exchange with configured
  audience, Google-library signature/time/issuer checks, stable-subject identity,
  no email auto-linking, Google-only password denial and deletion cascade. Full
  backend suite: 266 passed, 1 existing Windows skip; 12 new tests use real locally
  signed tokens with certificate fetching mocked. No live Google account exchange
  occurred. Android wiring now builds with 103 passing JVM tests and default-build
  disabled-button API 36 QA; OAuth configuration, release hardening and
  real-account/device/UAT evidence remain missing; AUTH-02 is partial. See
  `shared/contracts/google-sign-in.md`. Follow-up password-session audit unified
  registration/login with the verified-profile rollback path: 104 JVM tests and
  API 36 registration, normalized identity, wrong-password recovery and restart
  checks passed. Device profile-outage/Keystore-failure injection remains open.

- Replaced fixed text-control/card heights with minimum heights and made grade/
  subject grids font/width-responsive within the page scroll. Android build/lint
  and 97 JVM tests passed. Targeted API 36 font-scale 2.0 QA passed: single-column
  subject cards, wrapped parent-progress button and Grade 8 navigation; screenshots
  inspected and original font setting restored. First script navigation assumptions
  were corrected and rerun. TalkBack, other screens/devices and UAT remain open;
  UX-01 is partial. See `large-text-qa.md`.

- API 36 recovery-message QA passed against `06b4bec`: textless-page and
  insufficient-material messages were readable without clipping; dismissal and
  correction preserved selection, five-question restart/creation retry, exact
  page-2 sources, conflict recovery and final results. Remaining answers used
  the API fixture; screenshots inspected. Other error codes, large-text/TalkBack,
  network failures and UAT remain open. See `shared/contracts/document-error-codes.md`.
- Added `uat-runbook.md` with candidate identity/signing/staging prerequisites,
  tester journeys, privacy safeguards, issue/retest records and explicit user
  acceptance gates. This is preparation, not a release candidate or UAT sign-off.

- Added fixed document-recovery error codes and Android-owned guidance for
  insufficient quiz material, textless PDF pages, omitted chapter coverage and
  the 50-range limit. Arbitrary response bodies remain excluded; unknown codes
  and authentication failures keep safe fallbacks. Backend 254 tests passed,
  1 existing Windows test skipped; Android build/lint/95 JVM tests passed. Updated
  PDF device assertions have not yet been rerun. See
  `shared/contracts/document-error-codes.md`; UX and release gates remain partial.

- API 36 PDF-page QA passed against `8f11cba`: blank-only/invalid ranges, explicit
  confirmation, page-2 scope 288–591 and restart preservation, insufficient-count
  rejection then five-question recovery, committed-response 503 replay without
  duplicate quizzes, exact source references, conflict recovery and restored
  results. Remaining answers used the API fixture. Screenshots inspected; full
  backend suite 251 passed, 1 existing Windows test skipped. Generic validation
  messaging needs improvement; complex PDF/device network/accessibility and UAT
  remain open. See `shared/contracts/pdf-page-selection.md` for the initial failed
  ten-question fixture run, corrected command, evidence and limitations.

- Wired Android physical PDF-page index, inclusive range inputs, review and explicit
  replacement confirmation into account-scoped excerpt persistence. Draft reviews
  invalidate on input/document/scope changes; confirmation rechecks identity and
  bounds. Debug build/lint and 93 JVM tests passed. Device range/restart/failure QA,
  accessibility and UAT remain open; DOC-02 is partial. See the PDF-page contract.

- Added Android typed PDF-page API methods and validation for page order,
  identity, blank-page reports, requested boundaries and returned excerpt scope.
  Debug build/lint and 91 JVM tests passed. The methods are not yet wired to page
  controls; learner-facing review/confirmation, persistence and device QA remain
  open. See `shared/contracts/pdf-page-selection.md`.

- Added original physical PDF-page indexing and read-only page-range resolution
  into exact chapter/excerpt boundaries. Re-extracted text must match stored text;
  blank pages are preserved and blank-only/unsafe/omitted-source selections fail.
  Synthetic three-page rendering was inspected under the PDF skill; page-2 scope
  excludes page 1. Backend 250 tests passed, 1 existing Windows test skipped;
  eight focused tests passed after the final cross-page test addition.
  Android page controls, complex PDFs, device recovery and UAT
  remain open. See `shared/contracts/pdf-page-selection.md`.

- API 36 source-search QA passed: no-match state preserved selection; Android
  query/result confirmation selected source characters 324–927; restart and a
  committed-creation HTTP 503 retry preserved the range with exactly one quiz.
  All ten question references matched it, and conflict/feedback/results recovery
  passed (remaining answers used the API fixture). Screenshot inspected. No live
  calls. Multiple results, failure/accessibility/account-switch checks and UAT
  remain open; see `shared/contracts/source-search.md`.

- Added Android literal source search and explicit result-to-excerpt confirmation.
  Results are validated against document/query/chapter scope and Unicode bounds;
  stale results clear on relevant edits, and unconfirmed searches are not persisted.
  Debug build/lint and 85 JVM tests passed. Search/confirmation on-device, failure,
  accessibility and UAT checks remain open. See `shared/contracts/source-search.md`.

- Added owner-scoped literal source search within selected chapters. Results
  contain bounded verbatim passages and Unicode match offsets, with explicit
  truncation/more-results indicators; search neither calls AI nor changes quizzes
  or selection. Backend regression: 243 passed, 1 existing Windows test skipped.
  Android search/results controls and relevance/device/UAT evaluation
  remain open. This is not semantic topic indexing or completion of DOC-02. See
  `shared/contracts/source-search.md`.

- API 36 excerpt QA passed: Android selection/confirmation of one preview part,
  restart persistence, committed-creation HTTP 503 recovery with one saved quiz,
  exact source boundaries on resume and all ten question references within them.
  Conflict/feedback/results restoration passed; remaining answers used the API
  fixture. Screenshot inspected. Selection used Android Ctrl+A, not touch-handle
  dragging. Multiple/partial excerpts, accessibility, account switching and UAT
  remain open. See `shared/contracts/excerpt-selection.md` for exact scope.

- Android now supports explicit highlighted-source excerpts, disjoint additions,
  account/document-scoped persistence, Unicode-safe boundaries and scope-aware
  request identity. Creation and resume must confirm the requested bounds before
  accepting a new quiz. Debug build/lint and 78 JVM tests passed. Device selection,
  restart/failure/accessibility QA and UAT remain open. See the excerpt-selection
  contract; page/topic retrieval and the full DOC-02 gate remain incomplete.

- Added exact source-excerpt quiz selection to the backend: bounded Unicode
  offsets within selected chapters, no widening/omission, provider-boundary
  validation, persisted scope on resume and scope-aware creation retries without
  changing legacy fingerprints. Backend 230 tests passed, 1 existing Windows
  symlink test skipped. Android excerpt controls, page/topic retrieval,
  live quality checks and UAT remain open; DOC-02 is still partial. See
  `shared/contracts/excerpt-selection.md`.

- Added offline local backup/verify/restore tooling for SQLite and live uploads.
  It includes committed WAL data, remaps stored file paths, checks integrity and
  hashes, excludes configuration/orphan/deleted file bytes and refuses existing
  destinations. Synthetic restored-app QA covers login, saved quiz/tutor state,
  owner denial and deletion without touching the original runtime. Backend QA:
  212 passed, 1 skipped (Windows symlink creation unavailable). This is not
  encrypted/offsite backup or production recovery; host, retention/deletion
  reconciliation and operator cutover remain open. See `backup-recovery.md`.

- 2026-09-03: added explicit owner-scoped stored-structure gap repair. It keeps
  existing IDs/metadata and quiz rows, inserts low-confidence omitted-text ranges,
  and rejects unsafe structures without mutation. Backend 172 tests passed;
  seven focused repair tests rerun after final edits. Android controls/device QA
  remain pending; see `document-selection.md`. No user data was repaired in this run.
- 2026-09-03: repaired detection that silently omitted short sections and
  introductory text. New analyses preserve these exact ranges with lower
  confidence; existing stored IDs remain untouched. 164 backend tests passed,
  then seven focused coverage/upload-reopen tests passed. Safe stored-document
  reanalysis, device QA and richer selection modes remain open; see
  `document-selection.md`. DOC-02 remains partial.
- 2026-09-03: API 36 creation-retry QA passed: one quiz commits behind an
  injected HTTP 503, Android preserves the request ID across restart, and retry
  opens the same quiz with no duplicate. Pending identity clears only after
  recovery; downstream conflict/results/library checks pass. Screenshot inspected.
  Backend 158 tests passed. This is not TCP-loss simulation; no live calls.
  See `quiz-creation-retries.md` for remaining transport/deployment work.
- 2026-09-03: Android now durably saves a creation UUID before POST, reuses it
  for unchanged pending settings, and GETs authoritative state before accepting
  the quiz and clearing the pending identity. Build/lint/58 JVM tests passed.
  Device lost-response/process-death and account-switch verification remain open;
  see `quiz-creation-retries.md`. No live calls in this slice.
- 2026-09-03: added optional owner-scoped quiz creation request IDs. Committed
  retries return the original quiz without generation; settings conflicts return
  409 and concurrent commits save one quiz. Backend 158 tests passed; 35 focused
  tests rerun after final edits. Concurrent provider work can still duplicate.
  Android durable IDs and lost-response QA remain open; see the shared
  `quiz-creation-retries.md` contract. No live calls in this slice.
- 2026-09-03: hardened Android format decoding against unconfirmed binary
  creation, unknown formats and malformed/mismatched choices while retaining
  legacy four-option quizzes. Build/lint/54 JVM tests passed. No live requests.
  Malformed-response device QA and server creation-idempotency remain open; see
  `document-question-types.md`.
- 2026-09-03: both binary formats passed API 36 scripted answering/recovery:
  two choices, saved type, conflict handling, committed wrong answer, feedback
  restart, next question and completed results. Both screenshots inspected;
  remaining answers used API fixtures. Backend 154 tests passed. Explicit QA-only
  fixtures make no live calls and normal QA mode was restored. Correct-answer
  Android submission, live-provider integration and user UAT remain open; see
  `document-question-types.md`.
- 2026-09-03: API 36 QA verified both binary selections across restart, offline
  rejection with no quiz pointer, then multiple-choice generation, saved labels,
  conflict recovery, results and library reopening. Yes/No screenshot inspected;
  remaining quiz answers used the API fixture. Initial ADB connection failure
  recovered before a successful fresh run. Actual binary Android answering and
  account-switch checks remain open; see `document-question-types.md`.
- 2026-09-03: wired Android multiple-choice/True-False/Yes-No controls, scoped
  preferences, API requests and server-saved question/results labels. Debug build,
  lint and 51 JVM tests passed. No metered requests in this step. Emulator binary
  flow, restart/account-switch and offline-error QA remain pending; see
  `document-question-types.md`. DOC-03 remains partial.
- 2026-09-03: implemented backend True/False and Yes/No configuration, strict
  option validation, persisted type metadata, grading and recovery. 150 backend
  tests passed (34 relevant tests rerun after final guidance). Two live five-item
  samples passed automated checks and answer review; Easy calibration and excerpt
  labels still need work. Android controls/device QA remain pending; see
  `document-question-types.md`. DOC-03 remains partial.
- 2026-09-03: replaced model-transcribed quotes with server-reconstructed
  contiguous source-excerpt selections; repeated text retains its selected offset.
  Backend 138 tests passed. Live Mixed generation passed all three checks with
  correct arithmetic and a multi-step item; Hard was rejected by quality review.
  Internal excerpt labels in explanations and omitted shared source conditions
  remain issues. Broader generation quality, device timing and UAT remain open;
  see `difficulty-evaluation.md`.
- 2026-09-03: added a separate fail-closed document quality audit after blind
  answer verification. Checks cover demand, assumptions, cited evidence and
  explanations. Backend 129 tests passed; five live synthetic regression cases
  matched expected acceptance/rejection. This does not establish holdout accuracy,
  new full-generation/device behavior, educator approval or UAT. See
  `difficulty-evaluation.md` and the updated document configuration contract.
- 2026-09-03: reran the revised demand plan on five Hard and five Mixed items
  with four metered requests using the approved existing key. Both batches passed
  automated checks, but manual review still rejects difficulty quality and found
  a tank-drainage assumption missed by the blind reviewer. No production code
  changed; this is not a holdout, UAT or production acceptance. See
  `difficulty-evaluation.md` for item-level findings and local evidence.
- 2026-09-03: live synthetic difficulty evaluation exposed non-verbatim quote
  failures, then insufficient Hard/Mixed reasoning demand after quote guidance
  improved acceptance. Correct answers did not count as difficulty success.
  Added explicit multi-step Hard guidance and a balanced per-item Mixed plan;
  that final plan still needs live evaluation. Backend 121 tests passed. Citation
  completeness and educator review remain open; see `difficulty-evaluation.md`.

- 2026-09-03: difficulty device QA passed on API 36. Hard selection survives
  restart and offline generation rejects it; switching to Easy generates a quiz
  whose saved label restores on question/results screens. Conflict/results/library
  recovery passed; screenshot inspected. Medium/Mixed, account switching and live
  difficulty quality remain unverified. See `document-quiz-configuration.md`.

- 2026-09-03: added Android difficulty controls and account-scoped device
  preference. Generation sends the selected value; question/results screens show
  the saved server value, with legacy quizzes labelled unspecified. Offline and
  uncalibrated-demand limitations are disclosed. Build/lint/49 JVM tests passed.
  Device selection/failure/restart checks and live quality evaluation remain open.
  See `document-quiz-configuration.md`.

- 2026-09-03: added backend Easy/Medium/Hard/Mixed request metadata, generation
  guidance and persisted/resumed difficulty. Old quizzes retain unspecified
  difficulty. Deterministic mode refuses unsupported cognitive demand instead of
  falsely labelling recall questions. Backend 120 tests passed. Android controls,
  live difficulty evaluation and additional question types remain open. See
  `document-quiz-configuration.md` and the shared document-configuration contract.

- 2026-09-03: count-control API 36 QA passed. Presets update the generation action,
  invalid 21 disables generation, and custom 7 restores after restart. Android
  generated exactly seven questions; conflict/result/library recovery passed.
  Count screenshot inspected. Synthetic scripted content only; account switching,
  accessibility and live count-quality evaluation remain open. See `document-quiz-configuration.md`.

- 2026-09-03: added saved Android 5/10/15/20/custom (5–20) question count controls
  and removed the hard-coded request count. Invalid input prevents generation.
  Deterministic generation now rejects insufficient material rather than returning
  fewer questions. Backend 111 tests and Android build/lint/47 tests passed.
  Device checks and difficulty/question-type support remain open; DOC-03 makes
  the full original configuration scope explicit. See `document-quiz-configuration.md`.

- 2026-09-03: API 36 multi-chapter generation QA passed. Both independently
  selected chapter IDs survived restart; Android generated ten questions whose
  collected source references included both fixture chapters and no others.
  Conflict/restart/results/library checks also passed; screenshot inspected.
  Synthetic deterministic content only, not live quality or proportional coverage
  evidence. See `document-selection.md`.

- 2026-09-03: updated document recovery QA passed on API 36. Entire-document and
  cleared selections persist through forced restarts; empty selection disables
  generation. Plants-only selection persists and its quiz uses the selected source.
  Quiz/conflict/result/library recovery also passed; selector screenshot inspected.
  Multi-chapter generation and device migration/account-switch tests remain open.
  See `document-selection.md`.

- 2026-09-03: added Android document chapter checkboxes, Entire document, Clear
  selection and selected count. Selection persists across restart with legacy
  single-ID migration; the API receives all selected IDs and empty selection
  cannot generate. Build/lint/45 JVM tests passed. Updated recovery script still
  needs execution; page/section/topic controls remain missing. See `document-selection.md`.

- 2026-09-03: audited the original document-selection brief and added DOC-02 so
  unsupported selection modes remain explicit. Unified chapter-set validation
  across deterministic/live generators; invalid IDs are never silently dropped,
  duplicates and invalid source ranges are rejected before generation. Backend
  105 tests passed, including API 422 with no saved quiz/questions. Android
  multi-selection, page/section/topic modes and device verification remain open;
  see `document-selection.md`.

- 2026-09-02: replacement goal created and this ledger established. Production
  and curriculum decisions requested; local development and QA can proceed.
- User confirmed **private APK distribution** and **Grade 8 first**. Prioritize
  Grade 8 acceptance; do not claim Grades 1–12 coverage. Education board and
  backend hosting destination remain unspecified.
- Database-integrity regression reproduced the foreign-key defect before the
  fix (1 failing test). After the fix, `uv run pytest -q` passed **15 tests**.
  Tests verify orphan rejection on successive connections, rollback, account
  cascade through documents/quizzes/questions/mastery sessions/attempts, file
  removal, invalidation of deleted-account tokens, and another user's survival.
  This does not yet establish a production retention policy or migration cleanup
  of any orphaned records created by an older running application.
- 2026-09-03: corrected premature chapter mastery after one rewrite; successful
  remediation now continues the remaining assessment. Added owner-scoped resume
  endpoint and persisted tutor payload, grade-isolated reports, backend-derived
  student percentages and unlock evidence, Android resume and explicit phase
  navigation. Backend **18 tests passed**; Android **4 unit tests passed**,
  `assembleDebug` and `lintDebug` passed. Added repeatable emulator QA script
  `scripts/qa-mastery-resume.ps1` restricted to the dedicated test AVD and a
  deterministic backend. Device runtime evidence is recorded separately below.
- Device QA: `scripts/qa-mastery-resume.ps1 -ResetTestAppData` completed with
  exit 0 on `LearnSmart_API36`, using an isolated deterministic backend and
  synthetic account. Verified tutor recovery after forced process stop, persisted
  selected wrong answer, remediation advancing to question 2, another process
  restart recovering question 2, remaining questions before mastery, and the
  backend-derived 100% chapter display. Inspected `artifacts/qa-mastery-progress.png`.
  This is deterministic workflow QA, not provider-quality evaluation, full Grade 8
  curriculum verification, or user UAT acceptance. Existing legacy prematurely
  mastered sessions still need a data-repair strategy before production migration.
- 2026-09-03: OA-01 adapts OpenMAIC short-answer score/comment grading from pinned
  source into the rewrite workflow. MIT notice retained; provenance records what
  was ported and what was rejected. Added four-point rubric, strict validation,
  retryable evaluator errors, persisted assessment feedback, and Android display.
  Backend 41 tests and Android build/lint/4 unit tests passed. Live regression
  evaluation initially failed 1/8 score cases and leaked answers in feedback;
  revised rubric + server-owned incomplete-answer hints passed all 8 cases on
  rerun. This is limited regression evidence, not calibrated grading accuracy.
- OA-01 Android workflow QA passed using `serve_qa.py --qa-only` (scripted,
  localhost-only, isolated runtime): score/feedback display after process death,
  pending question 2, and remaining assessment before mastery. Screenshot
  inspected. This is not UAT acceptance and the fixture server is not production.
- 2026-09-03: Android bearer-token encryption, legacy migration, explicit backup
  exclusions and release HTTPS guard implemented. Build, lint and eight JVM tests
  passed; emulator restored an authenticated tutor session from encrypted storage
  after process death, with no plaintext token preference. Missing and HTTP release
  endpoints were rejected. See `android-session-security.md` for coverage limits;
  this is not a signed production APK, security certification or UAT sign-off.
- Authentication recovery: authenticated 401 resets visible learner state and
  clears saved credentials; login 401 stays on sign-in. Server error bodies are
  no longer displayed, redirects are disabled, and connections are closed.
  Backend 42 tests and Android build/lint/14 JVM tests passed. Expired-token API
  regression proves denied read/mutation/deletion and unchanged tutor state on
  reauthentication. See `authentication-recovery.md` for device scope and gaps.
- API 36 emulator QA passed the full scripted learning flow plus external deletion
  of its disposable account: authenticated progress request returned 401, Android
  showed the safe sign-in message, tokens were absent from saved preferences,
  restart stayed signed out, and invalid login displayed the credential message.
  This tests deleted-account invalidation, not timed expiry on a real device.
- Weekly report regressions reproduced out-of-window counts and unsupported
  empty-week classification. Corrected UTC boundaries, unique completed chapters,
  activity from older sessions and evidence-labelled heuristic. Backend 44 tests,
  Android build/lint and 14 JVM tests passed. Parent UI distinguishes learning
  responses from unique questions and weekly metrics from current chapter progress.
  Parent access/consent, predictive calibration and device/UAT evidence remain
  separate gates; see `weekly-report-qa.md`.
- Refreshed API 36 scripted QA passed the weekly report extension. Screenshot
  inspection confirmed 5 responses, 80% accuracy, 1 unique chapter and a clearly
  labelled 88% heuristic, with all-time progress separately described. Initial
  stale-server metadata failure was resolved by refreshing the verified fixture.
- Android upload now uses bounded streaming rather than loading the entire file,
  enforces the limit despite unknown/false metadata, and sanitizes multipart
  headers. Android build/lint/19 JVM tests and backend 45 tests passed. Streamed
  incomplete multipart was rejected without stored documents; complete multipart
  succeeded. Device provider and proxy checks remain; see `document-upload-safety.md`.
- DOCX extraction now has archive entry/expanded-size/ratio/path/compression
  admission checks and bounded CRC verification before parsing. Parser details
  are not returned to clients. Backend **58 tests passed**, including ordinary
  DOCX acceptance and rejected-upload cleanup. Worker isolation and PDF resource
  limits remain; see `document-processing-limits.md`.
- Document quiz resume endpoint and Android account-scoped pointer/manual resume
  implemented; completed quizzes restore results and question totals are no longer
  hardcoded. Backend 59 tests and Android build/lint/19 JVM tests passed. Device
  recovery verification remains pending. Audit also found source-supported
  distractors in the document generator; question ambiguity is a release blocker.
  See `document-quiz-recovery.md`; DOC-01 is still partial.
- User explicitly approved existing API-key reuse. Added source-quoted structured
  document-question generation plus blind model review; rejected batches are not
  saved. Replaced ambiguous deterministic questions with explicit source-word
  recall for QA. Live synthetic five-question generation/review passed; this is
  narrow evidence, not calibrated reliability. Legacy ambiguous quizzes and broad
  validation remain open; see `document-question-validation.md`.
- Voice input handles cancellation/empty/missing-service cases without replacing
  typed text. Read-aloud waits for initialization, checks language support, offers
  Stop and splits long inputs. Android build/lint/22 JVM tests passed. Real speech
  engine/microphone/animation and background lifecycle checks remain; this is not
  full conversational tutoring acceptance. See `voice-recovery.md`.
- Added interactive same-denominator fraction bars/sliders with simplified sum,
  whole/remainder display and reset. Exploration does not submit learner answers
  or award mastery. Native implementation, not an OpenMAIC import. Android
  build/lint/27 JVM tests passed; TUT-05 remains partial across other concepts and
  the visible/conversational teacher. See `fraction-explorer.md`.
- API 36 scripted QA passed the new fraction-slider/reset interaction and the
  remaining tutor/practice/rewrite flow through all questions before mastery.
  Fraction-model screenshot inspected. Broader accessibility and other concepts
  remain unverified; the initial missed test tap was corrected, not waived.
- Adaptive concurrency regressions reproduced duplicate commits for diagnostic,
  practice and rewrite snapshots. Added transactional snapshot checks; competing
  stale writes now return 409 without another attempt. Backend 69 tests passed;
  Android build/lint/27 tests passed with conflict-triggered session refresh.
  Delayed retries/idempotency and device conflict injection remain open. See
  `mastery-concurrency.md`; ASM-01 is still partial.
- Current weak-area recommendations now clear after successful independent
  assessment, persist through guided practice, and reactivate on a later mistake.
  Android keeps these separate from historical weekly response metrics. Backend
  70 tests and Android build/lint/27 JVM tests passed; dashboard device acceptance
  and retention calibration remain pending. See `current-weak-areas.md`.
- Document answer tests reproduced concurrent overwrite, rejected identical
  retries and out-of-order acceptance. Submission is now transactional, replays
  identical answers and rejects conflicting choices or skipped questions.
  Backend 74 tests passed. Device network-loss/multi-device recovery and production
  contention remain unverified; see `document-quiz-recovery.md` and the document
  answer contract. No UAT or production acceptance is claimed.
- Android document-answer conflicts now trigger saved-quiz recovery. Adaptive
  recovery is also explicitly tied to answer operations; read/refresh failures
  cannot recursively refresh. Android build/lint/29 JVM tests passed, including
  routing-policy tests. Device conflict injection remains pending.
- Added upload-to-chapter-selection recovery through an owner-scoped document
  summary endpoint and account-scoped Android document/chapter pointers. Quiz
  creation replaces upload pointers, and missing documents clear stale pointers.
  Backend 75 tests and Android build/lint/30 JVM tests passed. Process-death/device
  picker verification and unknown-outcome upload/create reconciliation remain
  open; see `document-quiz-recovery.md`.
- API 36 document recovery QA now passed actual file-picker upload, selected
  chapter persistence, restart before/after quiz creation, a confirmed stale
  answer 409 followed by automatic saved-feedback recovery, question 2 continuation
  and completed-results restoration. Synthetic fixture only; remaining answers
  were API-driven. Screenshots inspected. Network loss, physical-device coverage,
  status-bar contrast and UAT remain open. See `document-quiz-recovery.md`.
- Corrected system-bar icon appearance for the app theme, replaced fixed pale
  highlight backgrounds and text accents with theme colors, and moved error
  dialogs inside the theme. Build/lint/32 JVM tests passed, including selected
  4.5:1 text-pair checks in both themes. API 36 settings-toggle/restart QA passed;
  light/dark settings screenshots inspected. Full-screen accessibility coverage
  remains open; see `theme-readability.md`.
- Added an authenticated uploaded-document library with empty/loading/refresh
  states and reopening without re-upload. Backend 75 tests and Android
  build/lint/32 JVM tests passed. API 36 QA verified empty/populated library,
  reopening after clearing local pointers, process restart, no duplicate upload
  and preservation of the previous quiz; screenshot inspected. Offline/library
  scale, prior-quiz browsing and individual deletion UI remain open. See
  `document-library.md`.
- Added named, confirmed document deletion in the Android library and back
  navigation from chapter selection. Backend 76 tests and Android build/lint/35
  JVM tests passed. API 36 QA verified Cancel, actual deletion, empty library and
  restart cleanup; screenshot inspected. Regression checks cover file removal,
  quiz/question cascade and unrelated-material preservation. Filesystem cleanup
  failure/retry and production backup retention remain open; see the deletion
  section in `document-library.md`.
- Added a transactional file-cleanup queue for document/account deletion, bounded
  immediate/startup retries and a periodic worker. Failed unlinks retain a job;
  outside-upload paths and live references are preserved. Backend 81 tests passed,
  including failure injection and actual startup cleanup. Production failure
  drills, legacy orphan reconciliation, alerts and backup retention remain open.
  See `upload-cleanup.md`.
- Upload validation now precedes file creation, and partial-write/persistence
  failures clean unreferenced files or queue locked files. Live references are
  protected when commit outcomes are uncertain. Backend 85 tests passed with
  failure injection. Process-crash reconciliation and real storage-failure drills
  remain open; see `upload-cleanup.md`.
- Added owner-scoped optional interest preferences with constrained choices and
  save/read/clear/delete behavior. New tutor explanation prompts receive saved
  interests; practice questions and grading are unchanged. Backend 88 tests passed
  with mocked prompt checks. Android UI, device tests and live example-quality
  evaluation remain open; see `learner-interests.md`.
- Added Android interest selection with provider-use disclosure, three-choice
  limit, explicit save and clearing. Build/lint/38 JVM tests passed. API 36 QA
  verified save-to-server, restart restoration and durable clearing with a
  disposable account; screenshot inspected. Follow-up API 36 QA injected a
  post-commit 503, verified the server-side choices, preserved the draft and retried
  idempotently before restart/clear checks. Separate two-account QA verified
  interest isolation across sign-out/sign-in and restart. Broader live example
  quality and educator/UAT review remain open; see `learner-interests.md`.
- Evaluated nine synthetic interest-framed fraction explanations across three
  prompt revisions using the existing approved key. Initial tone, unit and
  whole/part errors were rejected; final three cases passed development-agent
  review. All practice prompts were preserved. Backend 88 tests passed, with
  three interest tests rerun after final guidance changes. This reused sample is
  not a holdout, educator review, UAT or production sign-off. Broader evaluation
  remains open; see `learner-interest-evaluation.md`.
- Added adaptive state tokens and Android submission preconditions so delayed
  retries can be rejected rather than applied to a later question or practice
  attempt. Backend checks precede provider work and retain the atomic commit
  guard. Backend 92 tests and Android build/lint/40 JVM tests passed. Legacy clients remain compatible
  but unprotected against delayed retries; mandatory migration and Android
  lost-response device QA remain open. See `adaptive-submission-preconditions.md`.
- API 36 device QA now verifies adaptive stale-screen recovery: a second client
  advances question 2, Android receives an actual 409 and restores question 3
  without mutation, then preserves it across restart. Full remediation/completion
  and a weekly total of five responses/one chapter passed; screenshot inspected.
  Actual network-response loss, practice/rewrite device conflicts, account switch
  and legacy-client enforcement remain open. See `adaptive-submission-preconditions.md`.
- Verified Android recovery from a committed diagnostic answer whose response is
  replaced by a QA-only 503. Retry receives 409 and resumes without mutation;
  restart, completion and the five-response weekly count passed. Backend 93 tests
  passed. This is an HTTP failure after commit, not a TCP-loss simulation. Actual
  connection loss, malformed success payloads and other phase injections remain
  open; see `adaptive-submission-preconditions.md`.
- Fixed premature Android token acknowledgement: adaptive decoders now accept
  state only after constructing their result. Build/lint/42 JVM tests passed.
  API 36 QA injected HTTP 200 with a new token but missing answer fields; retry
  recovered via 409, restart and completion preserved the five-response total.
  Semantically inconsistent payloads and other phase/device coverage remain open;
  see `adaptive-submission-preconditions.md`.
- Android now exposes explicit omitted-range repair on the chapter selection
  screen and marks low-confidence ranges for review. Added ranges are not
  auto-selected, and pending quiz identity/settings are untouched. Build, lint
  and 61 JVM tests passed; device repair/restart/failure checks remain pending.
  This does not complete DOC-02 section/page/topic selection or user UAT. See
  `document-selection.md`.
- API 36 repair QA passed with an injected post-commit HTTP 503: retry exposes
  an unselected recovered range, restart preserves selection, pending quiz
  identity is unchanged, and creation retry resumes exactly one existing quiz.
  Screenshot inspected; backend 173 tests passed. Remaining-answer completion
  was API-driven. Actual TCP loss, unsafe-structure device checks and user UAT
  remain open. See `document-selection.md` for the exact scope.
- Added owner-only, bounded source-text preview and Android previous/next part
  navigation for existing/recovered chapters. Preview does not change selections.
  Backend 175 tests and Android build/lint/63 JVM tests passed; device navigation,
  offline retry and accessibility remain pending. Text chunks are not PDF pages;
  DOC-02 section/page/topic selection remains partial. See `document-selection.md`.
- API 36 preview QA now passed: both displayed source parts match the API,
  boundary navigation and backward/return controls work, restart preserves
  selection and pending quiz identity, and retry resumes the same quiz. Screenshot
  inspected. Remaining-answer completion was API-driven; preview-specific offline,
  malformed-response and accessibility checks remain open. See the preview contract.
- The backend now enforces the four prerequisite gates already shown in Android
  before diagnostic generation and again before session insertion. Latest-session
  mastery is scoped to owner, grade and subject, with deterministic timestamp ties.
  Backend 180 tests passed, including a generation-time eligibility race. This is
  not a complete curriculum graph; time tracking, server catalog and device denial
  checks remain open. See `shared/contracts/learning-path-prerequisites.md`.
- Android now consumes grade-scoped backend unlock IDs instead of inferring them
  from local chapter order. Legacy/unscoped responses grant no new unlocks;
  mismatched grades are rejected. Backend 180 tests and Android build/lint/66 JVM
  tests passed. Device transition/stale-denial checks and the full curriculum
  catalog remain open. See the learning-path prerequisite contract.
- Added Android stale-unlock recovery and explicit Refresh progress. A 403 on a
  new gated-chapter start clears only that cached unlock and preserves saved
  learning; no automatic generation retry. Removed the silent Grade 6 start
  fallback. Build/lint/67 JVM tests passed; on-device denial and refresh are still
  unverified. See `shared/contracts/learning-path-prerequisites.md`.
- API 36 Geometry gate QA passed: initial lock, server-driven unlock, actual stale
  start denial with zero saved sessions, restart relock and refreshed eligibility.
  Normal Fractions remediation/restart/completion regression also passed; screenshot
  inspected and 181 backend tests passed. A stale-XML harness failure was corrected
  and the full run repeated successfully. Other subject gates and account/grade
  switching on-device remain open. See the prerequisite contract for fixture scope.
- Added the backend observed-study-presence endpoint and durable interval storage.
  Server timestamps, a 60-second gap limit, one owner cursor and completion clipping
  prevent the tested overlap/idle-gap overcounts; 183 backend tests passed. Android
  lifecycle/idle signals and time displays are not connected yet, so MAST-01 time
  tracking remains partial. This measures presence, not attention. See
  `shared/contracts/study-presence.md`.
- Progress and weekly-report responses now include owner/grade-scoped observed
  study seconds. Weekly totals clip each interval to the exact reporting window;
  untracked history stays zero. Backend 184 tests passed, including both boundaries,
  aggregate/grade and other-owner checks. Android emission/display and device QA
 remain pending; MAST-01 is not complete. See the study-presence contract.
- Android now emits bounded presence observations only on active learning screens
  while resumed and recently interacted with. Pause/idle/session/failure transitions
  reset the next server interval; no offline event queue is replayed. Backend 185
  tests and Android build/lint/69 JVM tests passed. Device timing and report display
  still need verification; sampling can undercount and is not proof of attention.
  See `shared/contracts/study-presence.md` for lifecycle and deployment constraints.
- The Android seven-day report now displays server-reported study presence for
  the selected grade, distinguishes unavailable from zero, and explains coverage
  limits without equating presence to attention. Build/lint/71 JVM tests passed;
  device timing and report rendering still need verification. Parent access and
  UAT gates remain open. See the study-presence contract.
- API 36 study-presence QA passed using actual elapsed time: foreground accrual,
  background exclusion, fresh restart interval, idle cutoff and no accrual on the
  report screen. Weekly display matched the API at 1m 32s; screenshot inspected.
  Fractions remediation/restart/completion and weekly response counts passed.
  Network/account-switch timing, broader device/accessibility coverage, retention
  and UAT remain open. See `shared/contracts/study-presence.md` for exact scope.
- Added opt-in fresh arithmetic practice after wrong answers for the existing
  three Fractions concepts, with atomic prompt/key/hint persistence and stale
  retry protection. Android accepts and displays the next lesson and clears its
  old input. Backend 188 tests and Android build/lint/71 JVM tests passed. Device
  checks, general subject coverage and failed-rewrite variant generation remain
  open; TUT-02 is partial. See `shared/contracts/fresh-practice.md`.
- API 36 addition practice QA passed two wrong-answer/new-question cycles,
  matching hints, cleared input and restart preservation. The displayed variant's
  calculated answer advanced to rewrite; remaining diagnostics and the seven-response
  weekly report passed. Screenshot inspected. Other concepts on-device, response
  loss, broader subjects and failed-rewrite fresh practice remain open; TUT-02 is
  still partial. See the fresh-practice contract.
- Rejected Fractions explanations can now return to tutoring with a fresh
  arithmetic practice variant, persisted atomically with grading/coaching and
  delivered to Android. Legacy requests keep the original question; no mastery
  is awarded on rejection. Backend 190 tests and Android build/lint/71 JVM tests
  passed. Device rejected-rewrite recovery, broader subjects and UAT remain open.
  See `shared/contracts/fresh-practice.md`.
- API 36 rejected-rewrite recovery passed after two fresh-practice cycles: new
  question/coaching persisted through restart without early mastery, its correct
  answer returned to rewrite, and remaining diagnostics completed normally. The
  weekly report matched nine responses and one unique mastered chapter; screenshot
  inspected. Deterministic addition QA only, not live grading-quality or UAT proof.
  Broader concepts/subjects and response-loss checks remain open. See the
  fresh-practice contract for the exact command and evidence.
- Added a persistent AI teacher status bar across every screen plus a larger
  native vector teacher whose ready, thinking and speaking states are driven by
  actual request and TTS lifecycle state. The lesson avatar sits beside playback
  controls and animates while speaking; accessibility exposes the same state.
  API 36 verified the bar across navigation and speaking/ready frames plus background stop, restart,
  explicit stop and completion. Android build/lint and 124 JVM tests passed.
  This is not phoneme lip-sync, acoustic-quality, TalkBack, UAT or production
  evidence; TUT-05 and TUT-06 remain partial. See `voice-recovery.md`.
- Generalized opt-in fresh practice beyond Fractions for provider-backed Grade 8
  lessons. A second blind call independently solves each candidate without its
  proposed key or hint; repetition, unsafe review, disagreement and answer-leaking
  hints fail closed, while the saved question/key/hint remain atomic with state.
  Two narrow live Cells/English samples passed and one disagreement was rejected.
  Fractions remain deterministic and outages preserve the current prompt. This
  is not curriculum, educator, UAT, cost/latency or production acceptance; see
  `shared/contracts/fresh-practice.md`.
- API 36 live-provider QA passed a synthetic Grade 8 Science Cells journey:
  generated/reviewed diagnostic, known wrong answer, independently reviewed fresh
  practice, persisted restart, and acceptance of the saved private key. Review
  disagreement now tolerates only harmless short-answer decoration while learner
  matching remains strict; rejected diagnostics fail as 503 and safe logs expose
  fixed codes only. Visual inspection corrected the general answer placeholder.
  Backend 425 passed with one Windows skip; Android 124 JVM tests, lint and debug
  assembly passed. This is one emulator QA path, not curriculum, physical-device,
  educator/UAT or production acceptance; see `shared/contracts/fresh-practice.md`.
- Added a native Grade 8 Science Cells explorer with three curated organelle
  selections, state-driven diagram highlights, instructional function/evidence text
  and dynamic accessibility semantics. API 36 scripted QA changed the selection,
  visually confirmed the result and proved through the authenticated session API
  that exploration did not submit, coach or award mastery. Generated HTML/actions
  are deliberately rejected. See `cell-explorer.md` and OA-03 in
  `openmaic-provenance.md`; TUT-05 remains partial outside these bounded scenes.
- Added consent-based parent/teacher report sharing between separate authenticated
  accounts. Learner-created codes are 128-bit, stored only as hashes, expire after
  15 minutes, are single-use and are invalidated when regenerated. Links expose only
  aggregate dashboard/weekly routes; answers, sessions, tutor chat and documents
  remain owner-only. Either party can unlink, and account deletion cascades access.
  API 36 verified redemption, read-only report disclosure and immediate removal.
  Backend 451 passed with one existing Windows skip; Android 128 JVM tests, lint and
  debug assembly passed.
  Invitation rows receive startup/periodic cleanup after a configurable 1–365 day
  retention window (30 days default), with invalid configuration rejected. See
  `guardian-report-access.md`; identity/child-consent policy, broader data retention,
  physical-device accessibility, UAT and production verification remain open.
- Added a native Grade 8 English Grammar sentence-parts explorer. Subject, Verb and
  Object actions visibly highlight the exact words and show curated role/check text;
  generated executable content is rejected. API 36 changed Subject to Verb, visually
  confirmed "solved" was highlighted, and an authenticated server read proved no
  submission, coaching or mastery mutation. See `sentence-explorer.md` and OA-03 in
  `openmaic-provenance.md`. Android 129 JVM tests, lint and debug assembly passed;
  backend regression remained 451 passing with one existing Windows skip. Broad grammar/curriculum and remaining interactive
  concepts, TalkBack, physical-device QA and UAT remain open.
- Added a native Grade 8 Social Studies Geography coordinate explorer. Equator,
  Prime Meridian and Coordinates actions highlight application-owned globe marks
  and explain canonical zero lines plus latitude-first ordering. API 36 selected the
  coordinate point, visually confirmed the result, and an authenticated server read
  proved no submission, coaching or mastery mutation. See
  `map-coordinate-explorer.md` and OA-03 in `openmaic-provenance.md`. Android 130
  JVM tests, lint and debug assembly passed; backend remained 451 passing with one
  existing Windows skip. This gives one
  bounded native interactive route in each core subject; it is not broad curriculum,
  TalkBack, physical-device or UAT acceptance.
- Replaced Android's hardcoded subject/chapter graph with authenticated
  `foundation-2026-09` server catalog loading for grades 1–12. Unknown pairs are
  rejected before any provider call; prerequisite locks derive from the same graph.
  Android validates grade, board, subject order/identity and chapter integrity with
  no static fallback, and clears stale catalog data when the grade changes. API 36
  opened every Grade 8 subject list and restored the catalog after process restart;
  the board-unconfirmed disclosure was visually inspected. Follow-up API 36 QA
  changed to Grade 9 under an injected one-shot 503, proved no stale Grade 8 catalog
  remained, displayed an explicit recovery action, recovered all four subjects and
  retained the recovered catalog after restart. Both success and fail-closed frames
  were visually inspected. Mastery sessions now persist and return their creation
  catalog version; legacy databases are migrated, and Android refuses to map an
  older saved lesson into a changed catalog while retaining its server record.
  API 36 verified that restart path, absence of the local resume action, current
  catalog rendering and an authenticated read of the retained legacy-version server
  session. Backend 456 passed with one existing Windows skip; Android 133 JVM tests,
  lint and debug assembly passed. See
  `shared/contracts/curriculum-catalog.md`. This is a synchronized foundation catalog,
  not authoritative board coverage or curriculum UAT.
- Replaced generic progress advice with deterministic evidence-based next steps.
  Independent diagnostic/rewrite mistakes now accumulate per account, grade,
  subject, chapter and concept until newer successful independent evidence clears
  them; guided practice cannot create or clear a weak area. Recommendations name
  the catalog location and unresolved count, then fall back to the latest active
  session or first prerequisite-eligible unmastered chapter. API 36 displayed two
  recurring mistakes, then updated to the active diagnostic after successful
  remediation; the frame was visually inspected. See
  `shared/contracts/personalized-next-step.md`. This is QA evidence, not educator or
  user acceptance of the recommendation policy.
