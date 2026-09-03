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
| DOC-02 | Entire document, multiple chapters, section, page range and topic selection | Partial | Backend chapter-set validation; Android multi-selection and persistence; page/section/topic retrieval boundaries and device QA |
| DOC-03 | Question count, difficulty and question-type configuration | Partial | Preset/custom count device QA; easy/medium/hard/mixed difficulty; multiple-choice, true/false and yes/no generation, grading and recovery |
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
  disposable account; screenshot inspected. Live example quality and device
  failure/account-switch coverage remain open; see `learner-interests.md`.
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
