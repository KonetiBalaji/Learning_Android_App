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

| ID | Requirement | Current status | Required acceptance evidence |
| --- | --- | --- | --- |
| AUTH-01 | Email registration and login | Partial | Invalid/expired/deleted sessions, account switching, encrypted device tokens, automated Android tests |
| AUTH-02 | Google login | Missing | Verified Google ID tokens, audience checks, configured client, actual Android sign-in |
| CUR-01 | Grade 1–12, subject and chapter selection | Partial | User-confirmed curriculum/board; authoritative chapter coverage and grade isolation |
| ASM-01 | Diagnostic and correct-answer progression | Partial | Exactly-once submissions, restart recovery, no answer leakage, all question transitions |
| TUT-01 | Age-appropriate tutor explanations and worked examples | Partial | Grounding, factual evaluation, age suitability, provider failure and retry tests |
| TUT-02 | Fresh practice, hints and repeated coaching | Partial | New validated practice items, misconception handling, no automatic chapter mastery after one remediated concept |
| TUT-03 | Interest-personalized examples | Partial | Profile/prompt path and Android save/clear/restart verified; live example quality, failure/account-switch checks remain |
| TUT-04 | Written explanation assessment | Partial | Rubric/eval set, false-pass tests, helpful coaching without treating model confidence as measured reliability |
| TUT-05 | Interactive examples and visible AI teacher | Partial | Working interactive teaching visuals, accessible avatar, verified device interaction |
| TUT-06 | Verbal questions and spoken animated explanations | Partial | Conversational tutoring, speech unavailable/cancel/error cases, real audio and animation checks |
| MAST-01 | Mastery, time spent, next chapter unlock | Partial | Durable server-owned grade/account-scoped mastery; all concepts assessed; honest time/score display |
| PROG-01 | Real student subject/chapter progress | Partial | Remove static percentages; backend-derived values survive restart/account switching |
| PROG-02 | Weak concepts and personalized learning path | Partial | Recurring-error evidence, remediation updates, next-step selection tests |
| PARENT-01 | Parent/teacher dashboard and weekly reports | Partial | Defined parent access model; grade-scoped reports, unique chapter counting, exact time windows |
| PARENT-02 | Exam readiness prediction | Partial | Explicitly labelled heuristic until calibrated against a supplied exam/curriculum dataset |
| DOC-01 | Upload/analyze/select/quiz/feedback/results | Partial | File limits/corruption/password cases, source-grounding checks, deletion, interrupted-flow recovery |
| UX-01 | Mobile-first cards, badges, theme, accessibility | Partial | Both themes, large text, small screens, TalkBack, loading/empty/offline/retry states |
| DATA-01 | Durable state and account isolation | Partial | Server resume contracts, encrypted local state, account switching and forced-process-death tests |
| SEC-01 | Deletion and retention | Partial | Database cascade assertions, file removal, other-owner preservation, retention policy |
| SEC-02 | Production hardening | Partial | HTTPS-only release guard implemented; production secrets, abuse/rate/cost limits, logs without sensitive content, backup/restore still need verification |
| UP-01 | Traceable OpenMAIC adaptation | Partial | OA-01 grading adaptation pinned/licensed/tested; remaining relevant upstream capabilities still need separate evidence |
| QA-01 | Automated regression suite | Partial | Backend, Android unit/instrumentation, AI evals, failure/recovery and security tests |
| UAT-01 | User acceptance | Missing | Testable build, scripted user journeys, issue log, explicit user acceptance |
| PROD-01 | Production deployment | Missing | User-confirmed host/domain/distribution, staging verification, rollback, secrets and operational checks |

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
  disposable account; screenshot inspected. Live example quality and device
  failure/account-switch coverage remain open; see `learner-interests.md`.
- Evaluated nine synthetic interest-framed fraction explanations across three
  prompt revisions using the existing approved key. Initial tone, unit and
  whole/part errors were rejected; final three cases passed development-agent
  review. All practice prompts were preserved. Backend 88 tests passed, with
  three interest tests rerun after final guidance changes. This reused sample is
  not a holdout, educator review, UAT or production sign-off. Broader evaluation
  remains open; see `learner-interest-evaluation.md`.
