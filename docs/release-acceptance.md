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

Physical-device UAT on signed candidate `0.3.0-uat.3` exposed a rewrite-grading
context defect after repeated coaching: the learner correctly applied the concept
to the fresh practice question, but the provider prompt identified only the older
diagnostic as an application target and returned 3/4. The grading contract now
supplies the current practice prompt and accepted answers and explicitly treats it
as an equal application target. Focused regression covers differing diagnostic and
practice quantities. TUT-04 remains QA verified, not UAT accepted, until the fixed
candidate is rebuilt and the physical-device rewrite passes.

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
or hint, then its hint is separately reviewed for accuracy, relevance and answer
leakage. Candidates fail closed on repetition/ambiguity/topic/grade/key/hint checks and are
atomically persisted only after the learning-state guard. Fractions retain their
deterministic variants; provider failure keeps the current question. Two live
Grade 8 Cells/English samples passed after one earlier disagreement was rejected;
a later four-subject Grade 8 evaluation accepted Math, Science, English and Social
Studies samples while safely rejecting two additional candidates. Backend
regression: 498 passed with one existing Windows skip. Broad curriculum,
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

The 2026-09-05 all-chapter live diagnostic run accepted 5/17 and failed closed on the
remainder. It exposed a format-adapter false rejection for objective text practice:
reviewed nonnumeric answers mislabeled `none` were forced through numeric parsing.
Grading mode now requires both the unconstrained classification and independently
numeric reviewed answers before enabling rational equivalence. A bounded rerun passed
Algebra, Geometry and Grammar; Economics remained safely rejected for key disagreement.
This improves availability without weakening the review gate; catalog-wide quality,
educator review and UAT remain open. See `docs/catalog-diagnostic-evaluation.md`.

A source-bounded generation follow-up now requires every necessary premise to be in
the generated question/options, keeps explanations within those premises and the
verified solution, and makes worked examples self-contained. A single live targeted
run accepted Civics; Matter was still safely rejected for ambiguity/invalid practice,
and Decimals timed out at the fixed provider deadline. The run was not resampled for
a pass. Independent review is unchanged, so this is a bounded availability repair,
not curriculum certification; see `docs/catalog-diagnostic-evaluation.md`.

Tutor explanations now pass a separate strict runtime review for accuracy, verified
method, worked example, grade suitability, concept, tone, hint quality, unsupported
claims and source-boundedness. Diagnostic teaching support is reviewed before storage,
so a rejected personalized lesson can use checked fallback content; legacy generated
support is re-reviewed or returns retryable `503` without committing the answer.
Backend 494 tests passed with one existing Windows skip. In the final live
four-subject run, Math,
English and Geography passed; Science added an unsupported fact and was correctly
rejected. A new live Fractions diagnostic bank passed teaching review and manual
arithmetic inspection. This advances TUT-01 to QA verified, not educator/UAT or
Grades 1–12 calibration; see `docs/tutor-lesson-quality.md`.

All five current Grade 8 Mathematics chapters now have app-owned deterministic
diagnostic fallbacks. Provider timeout or review rejection can therefore preserve the
complete Math diagnostic/tutor/practice/rewrite path without accepting failed model
content. Focused tests validate every bank, outage teaching, unsupported-chapter
failure, and authenticated creation for the non-gated chapters. Geometry retains its
Algebra prerequisite. The content is curriculum-neutral and not educator/UAT approved;
see `docs/deterministic-math-diagnostics.md`.

All four current Grade 8 Science chapters now have matching app-owned deterministic
diagnostic fallbacks as well. Focused provider/catalog/quality tests validate the banks,
outage teaching, generated-bank rejection fallback, authenticated creation for ungated
chapters, and continued failure for an uncurated English chapter. Ecosystems retains
its Force and Motion prerequisite. Further distinct practice after a failed guided
attempt still requires the reviewed provider. These foundation items are not board or
educator approved; see `docs/deterministic-science-diagnostics.md`.

All four current Grade 8 English chapters now have exact app-owned deterministic
fallbacks. Reading prompts are self-contained; Writing fallback items cover objective
editing and organization while the separate written-explanation evaluator retains its
four-point rubric. Focused tests validate every bank, outage teaching, ungated HTTP
creation, the Vocabulary prerequisite for Writing, and continued unavailability for an
uncurated Social Studies chapter. These are foundation items without board, educator,
or UAT approval; see `docs/deterministic-english-diagnostics.md`.

All four current Grade 8 Social Studies chapters now have matching app-owned
deterministic fallbacks using self-contained, country-neutral premises. Focused tests
validate each bank, outage teaching, ungated HTTP creation, the Civics prerequisite for
Economics, and rejection of unknown chapters. A set-equality contract now proves that
the deterministic map covers exactly all 17 chapters in the current catalog. Fresh
post-failure practice still requires independent provider review, and the foundation
content is not board, educator, or UAT approved; see
`docs/deterministic-social-diagnostics.md`.

Deterministic rewrite grading no longer treats eight words plus one repeated concept
term as proof of understanding. Non-Fractions explanations now remain ungraded and
cannot advance mastery unless the strict provider rubric is available. Only the three
explicitly curated Fractions methods retain offline rubrics. Focused QA includes an
authenticated Cells response that returns 503, stays in rewrite, and writes no attempt;
see `docs/rewrite-cross-subject-evaluation.md`.

A single authenticated deterministic end-to-end test now traverses all 17 catalog
chapters and 51 questions in prerequisite order through the real diagnostic routes.
Every session restores as mastered, and the final owner-scoped dashboard contains
exactly 17 mastered rows at 100%. This proves backend fallback continuity and unlock
state, not Android UAT or curriculum approval; see
`docs/full-catalog-fallback-qa.md`.

The current APK subsequently passed the API 36 catalog journey against the current
deterministic QA backend: all four subject lists, Grade 8 boundary, process restart and
legacy-catalog recovery were exercised. Three captures were inspected with readable,
unclipped grade/subject/action layouts. This strengthens installed-app integration
evidence but is not physical-device or user UAT; see the same QA record.

Representative production fallback content also passed installed-app API 36
rendering for Decimals, Cells, Grammar and Geography. The reusable harness asserted
each exact deterministic prompt and answer option; all four captures were visually
inspected without overlap or clipping. This is representative rendering evidence,
not exhaustive question coverage, physical-device testing, curriculum approval or
user UAT; see `docs/full-catalog-fallback-qa.md`.

Signed candidate `0.3.0-uat.10` (version code 12) at commit `940bdbd` has a
candidate-bound physical-device record with 22 PASS and 3 PENDING requirements.
The Xiaomi test device exercised email and Google authentication, Grade 8 learning,
guardian access, document learning, voice transcription, interactive teaching and
TalkBack/switch traversal against the candidate's pinned HTTPS staging backend.
The remaining candidate decisions are human acoustic acceptance (`TUT-06`), an
externally calibrated and reviewed readiness claim (`PARENT-02`), and human spoken
accessibility/usability/contrast acceptance (`UX-01`). The private record and its
screenshots remain outside Git. Agent-run device evidence is not explicit user UAT
acceptance and the temporary staging tunnel is not production deployment.

Signed candidate `0.3.0-uat.15` (version code 17) at commit `82477a8` adds a
candidate-bound physical-device retest for DOC-03. The Xiaomi device configured
all three chapters of the owned synthetic Grade 8 photosynthesis source with
custom count 5, Medium difficulty and True/False format. The reviewed live request
returned HTTP 201 in 68.664 seconds, exposed five distinct questions with exact
source ranges, accepted all responses and displayed `5 / 5 correct`. GitHub Quality
Gate run `34254950763` passed all four jobs for the same revision. The private v17
record remains pending overall because the other acceptance rows must be reconciled
for this exact candidate and the human/calibration/production gates remain open.
The same candidate subsequently restored its completed document session after an
Android force-stop, retained the Grade 8 catalog and subject progress, displayed
all five Mathematics chapters at 100%, and rendered the read-only seven-day report.
Its private record currently contains 9 PASS, 1 FAIL and 15 PENDING requirement
rows. The failure is TUT-02: a reviewed fresh Geometry prompt implied degrees but
rejected the correct bare response `70` because its stored key included a degree
suffix. Commit `7fab856` adds the narrowly scoped implied-degree variant while
preserving explicit precision and representation constraints.

Signed candidate `0.3.0-uat.16` (version code 18) at commit `28bc891` closes that
TUT-02 defect on the physical Xiaomi device. A newly reviewed prompt asked for the
third angle when the other angles were 35 degrees and 85 degrees; the persisted
answer bank contained `60°` and bare `60`, and the app accepted typed `60` and
advanced to rewrite. A separate explicit-precision journey rejected `58.5` when
two decimal places were required and accepted `67.360 degrees` when three decimal
places were required. This verifies that commit `7fab856` fixes implied-degree
answers without relaxing explicit formatting. The exact APK also entered active
read-aloud, and the product owner confirmed the voice was clear. TUT-06 remains
partial until the exact-v18 microphone journey and the rest of the verbal flow are
accepted. The private v18 ledger is pending overall because its remaining rows,
external readiness calibration and production deployment are still open.
The same v18 run also exercised wrong-answer remediation, two fresh-practice and
4/4 rewrite cycles, correct-answer diagnostic progression, cold-restart session
restoration, mastery completion, and an interactive triangle explorer change from
base 6/height 4/area 12 to base 8/height 5/area 20. These exact-candidate checks
advance ASM-01, TUT-01, TUT-04, TUT-05, MAST-01 and DATA-01 in the private ledger;
they do not replace broader educator, accessibility or multi-device acceptance.
The v18 dashboard and document-progress follow-up also reverified the approved
Grade 8 four-subject catalog, all five Mathematics chapters at 100%, three earned
badges, two completed document quizzes with 15 answers at 100%, and the bounded
seven-day report. CUR-01 and PROG-01 through PROG-03 therefore have exact-v18
physical-device evidence while later-grade, educator and broader-device scope stays
open.
An exact-v18 document journey then uploaded a fresh copy of the owned synthetic TXT
through the Xiaomi system picker, detected three sections, generated five Medium
True/False questions across the entire source in 59.959 seconds, displayed exact
source references and feedback, and completed at 5/5. The duplicate was subsequently
deleted through the named irreversible-confirmation dialog while the original stayed
in the library. This advances DOC-01, DOC-03 and SEC-01 for v18; DOC-02 remains open
for its full selection-mode matrix on this candidate. A subsequent signed-v18 PDF
journey indexed three physical pages, resolved page 1 to exact source characters,
confirmed that range as the active excerpt, and found an exact all-topic-words
passage. Adding that overlapping passage was safely rejected internally, but the UI
showed only a generic error instead of its available recovery instruction. Commit
`9a4ac03` gives this known local validation a fixed learner-safe message; a new
signed-candidate physical-device retest was required before closing DOC-02.

Signed candidate `0.3.0-uat.17` (version code 19) at commit `2d078b8` closes that
DOC-02 defect on the Xiaomi device. The exact build restored its persisted PDF
excerpt after upgrade, selected both detected chapters in entire-document mode,
replaced that scope with a reviewed topic passage, then replaced the topic excerpt
with physical PDF page 1 resolved to source characters 0–287. Repeating the overlap
displayed the fixed clear-or-choose-different message. Exact-v19 follow-up also
reverified the Grade 8 catalog, full Mathematics progress, badges, weekly and
document progress, an incorrect-answer-to-mastery Geometry journey, interest-aware
worked example, native triangle explorer, durable cold-start state, retention
disclosure and targeted document deletion. The private v19 ledger is machine-valid
with 15 PASS and 10 PENDING requirements; it remains pending overall and is not user
acceptance or production approval.

The v19 learner-side parent-access screen disclosed the aggregate-only boundary and
created a 15-minute single-use code. A disposable separate guardian account linked
through the candidate staging backend, read the linked learner's aggregate Grade 8
dashboard and weekly report without answer, document, upload or tutor-conversation
fields, then revoked itself. Report access immediately returned 404, the disposable
account was deleted, and the physical learner screen showed no active access plus an
anonymized grant/revocation history. This advances PARENT-01 with exact-candidate
physical-device and API evidence, but guardian Android UI, real-world identity and
child-consent policy, notification policy and human acceptance remain open.

| ID | Requirement | Current status | Required acceptance evidence |
| --- | --- | --- | --- |
| AUTH-01 | Email registration and login | QA verified | Physical-device/user acceptance and OEM AndroidKeyStore invalidation exercise |
| AUTH-02 | Google login | Partial | Backend exchange, five-minute one-use nonce binding and Android Credential Manager wiring are implemented; disabled-build device QA passes. OAuth configuration, real sign-in, configured-device lifecycle recovery and user acceptance remain missing |
| CUR-01 | Grade 1–12, subject and chapter selection | Candidate v19 physical-device verified for approved launch scope | The user approved Grade 8 as the initial boundary and an application-authored open-content curriculum. Signed v19 displayed Mathematics, Science, English and Social Studies, all five Mathematics chapters, and the CC BY 4.0 `open-oer-foundation-2026-09` identity without a false board claim. Grades 1–7/9–12 are later scope and educator approval remains open |
| ASM-01 | Diagnostic and correct-answer progression | Candidate v19 physical-device verified | Signed v19 exercised an incorrect angle answer, remediation, fresh practice, a 4/4 rewrite, return to the next diagnostic and correct remaining answers leading to 100% Geometry mastery. Transaction replay/conflict, owner scope and undisclosed-answer protections remain automated; broader live curriculum review remains open |
| TUT-01 | Age-appropriate tutor explanations and worked examples | Candidate v19 physical-device verified | The wrong Geometry answer on signed v19 produced a checked learner-controlled triangle-angle lesson, distinct worked example and next-step hint before practice. Broader ages and educator calibration remain open |
| TUT-02 | Fresh practice, hints and repeated coaching | Candidate v19 physical-device verified | Signed v19 accepted bare `60` for a reviewed 35°/85° triangle prompt whose persisted answer bank explicitly allowed degrees or bare input, then advanced to rewrite. Broader curriculum and educator/user review remain open |
| TUT-03 | Interest-personalized examples | Candidate v19 physical-device verified | Signed v19 saved Space as the sole optional interest with the disclosure that interests affect explanations, not grading, and a new Geometry lesson used a separate space-themed 40/90/50 worked example. Broader live example quality and educator review remain open |
| TUT-04 | Written explanation assessment | Candidate v19 physical-device verified | Signed v19 submitted a learner-authored triangle-angle explanation, received bounded 4/4 feedback and advanced to the next diagnostic. Strict rubric, server-owned feedback, persistence/failure tests and broader synthetic evaluations remain automated; calibration and educator review remain open |
| TUT-05 | Interactive examples and visible AI teacher | Candidate v19 physical-device verified | Signed v19 exposed the learner-controlled staged walkthrough and native triangle explorer. Changing from base 6/height 4 to base 8/height 5 recalculated area 20, identified perpendicular height and stated that exploration cannot submit or change mastery. Catalog-wide specialized explorers remain automated; spoken accessibility and educator review remain open |
| TUT-06 | Verbal questions and spoken animated explanations | Partial | Conversation, read-aloud lifecycle/animation and voice-input recovery are automated. Signed v18 entered active read-aloud, exposed Stop reading and the device-speech-service disclosure, and the product owner confirmed the audible voice was clear. A real microphone transcription was previously verified on v12; exact-v18 microphone journey and final end-to-end verbal acceptance remain pending |
| MAST-01 | Mastery, time spent, next chapter unlock | Candidate v19 physical-device verified | Signed v19 reached Concept mastered and 100% only after the remaining diagnostics were answered, displayed Learning path complete and restored Geometry at 100% in the chapter list. Graph unlock/relock recovery and bounded presence remain automated; broader accessibility review remains open |
| PROG-01 | Real student subject/chapter progress | Candidate v19 physical-device verified | Static percentages are absent; signed v19 displayed Fractions, Decimals, Percentages, Algebra and Geometry at 100% from server-backed progress and Mathematics at 100% on the Grade 8 dashboard. Owner isolation, zero state and recovery remain automated; broader user acceptance remains open |
| PROG-02 | Weak concepts and personalized learning path | Candidate v19 physical-device verified | Signed v19 retained 100% assessed Mathematics progress and the earned First answer, Learn from mistakes and Chapter master badges after completed mastery journeys. Recurring-error/remediation rules and prerequisite-aware continuation remain automated; educator review remains open |
| PROG-03 | Per-uploaded-document learning progress | Candidate v19 physical-device verified | Signed v19 displayed three completed quizzes, 20 answers, 100% overall accuracy, per-section counts and a strongest grounded concept. Its seven-day report showed 52 responses, 65% accuracy, five mastered chapters, 58m 6s presence and the uncalibrated-not-exam-prediction limitation. Broader provider quality and user review remain open |
| PARENT-01 | Parent/teacher dashboard and weekly reports | Candidate v19 boundary partially verified | Signed v19 displayed the learner consent boundary and single-use-code flow on the physical Xiaomi device. A disposable separate guardian account read only aggregate dashboard/report data, self-revocation immediately returned 404, account deletion anonymized the learner-visible audit history, and no active access remained. Guardian Android UI, real-world identity/child-consent and notification policy, production-scale latency and human acceptance remain open |
| PARENT-02 | Exam readiness prediction | Partial | The product truthfully labels this as an uncalibrated learning indicator, excludes guided practice and withholds a level until 10 independent diagnostic/rewrite answers span 2 chapters. Signed candidate v12 displayed the same limitation to learner and guardian. A fail-closed holdout evaluator now validates de-identified records and reports Brier score, calibration-in-the-large and expected calibration error, but always requires review. A matched external outcome dataset plus educator/statistical review and UAT approval remain required; see `docs/readiness-calibration-protocol.md` |
| DOC-01 | Upload/analyze/select/quiz/feedback/results | Candidate v18 physical-device verified | Signed v18 uploaded a fresh owned TXT through the Xiaomi system picker, detected three sections, generated an entire-document quiz, displayed exact source references and grounded feedback, and reached results. File limits/corruption, parser isolation/capacity, PDF ceilings and recovery remain automated; complex layouts and broader device paths remain open |
| DOC-02 | Entire document, multiple chapters, section, page range and topic selection | Candidate v19 physical-device verified | Signed v19 selected both PDF chapters in entire-document mode, replaced whole chapters with a reviewed topic passage, then replaced that excerpt with physical page 1 resolved to exact source characters. The overlap retest displayed the fixed actionable message from commit `9a4ac03`. Highlighted-excerpt breadth, semantic curriculum scale and multilingual relevance remain open |

Document quiz results now expose the learner's selected answer, correct answer,
grounded explanation and source reference for each completed incorrect response;
Android validates and renders the complete teaching record. Unanswered answers
remain undisclosed and ownership is unchanged. The results screen can create an
owner-scoped, idempotent new quiz containing only completed incorrect items, with
fresh unanswered question IDs and preserved source evidence. Automated QA is
recorded in `quiz-mistake-review.md`. Configure-another and bounded
increase-difficulty actions revalidate the document and return to explicit source
selection; API 36 review and UAT remain open.

The result-actions API 36 journey subsequently verified a complete mistake teaching
record, a seven-item fresh unanswered retry, durable retry identity cleanup,
force-stop restoration, configure-another document revalidation and persisted
Easy-to-Medium increase. Captures were inspected. Remaining evidence is physical
device accessibility and user UAT; TalkBack tree exposure for the teaching record
and all five actions passed on API 36 with service/permission restoration verified.
See `quiz-mistake-review.md`.

Displayed source references on immediate feedback and completed mistake records are
now actions rather than dead labels. The server reveals only the exact persisted
source range after the question is answered, checks question/quiz/document ownership,
and fails closed for malformed historical references. API 36 verified opening the
correct answered question after process restart, independently reconciled the exact
text/range with the authenticated endpoint, and captured the readable dialog. See
`docs/question-source-evidence.md`. The PDF follow-up also rendered and accessibility-
labelled the original physical page containing the exact sentence. Complex layouts,
hostile-PDF stress, physical-device accessibility and UAT remain open, so DOC-01
stays partial.
| DOC-03 | Question count, difficulty and question-type configuration | Candidate v18 physical-device verified | Signed v18 generated five Medium True/False questions across the complete owned three-section source in 59.959 seconds, displayed the requested labels and exact source ranges, and completed at 5/5. Preset/custom recovery and the broader difficulty/type matrix remain automated; broader provider sampling remains open |
| UX-01 | Mobile-first cards, badges, theme, accessibility | Partial | API 36 verifies both themes, large text, small-screen scrolling, learning badges and targeted loading/empty/offline/retry flows. Signed candidate v12 completed keyboard/switch traversal and the TalkBack tutorial, then exposed the interactive tutor screen while the real TalkBack service was active. Human full-screen spoken traversal, usability and non-text contrast acceptance remain pending |
| DATA-01 | Durable state and account isolation | Candidate v19 physical-device verified | Signed v19 restored the authenticated PDF at the exact Chapter 1 source-character excerpt after Android force-stop and cold launch. Two-account isolation remains automated; multi-device races and broader explicit user acceptance remain open |
| SEC-01 | Deletion and retention | Candidate v19 physical-device verified | Signed v19 displayed the active-data/document, 24-hour crash-file, 30-day invitation and 30-day backup retention rules, then permanently deleted only the synthetic PDF through the named confirmation flow while retaining the original TXT. Backup prune and active-data cleanup remain automated; production scheduling/storage-provider deletion and legal review remain open |
| SEC-02 | Production hardening | Partial | HTTPS release guard, hosted-booted TLS proxy with bounded body/slow-client/per-IP controls and a private API port, pre-parser declared/streamed request-body admission, locked non-root/read-only-root four-worker/two-container same-host smoke, bounded round-robin authenticated traffic gate, independent APK/hash/deployment-identity plus database/upload readiness verifier, schedulable privacy-safe deployment identity/readiness/latency probe, offline backup checks, persistent authentication peer throttle, atomic per-account daily AI-operation caps, enforced per-call provider output-token ceilings, privacy-safe correlated request events, spawned parser timeout/output isolation, Windows Job Object memory caps, fail-fast atomic cross-worker parser admission with crash recovery and API 36-verified support IDs implemented; trusted production certificate/edge behavior, cross-host/network-filesystem safety, long-duration load, provider project currency budget, deployed probe/alert channel, log sink and deployment recovery still need verification |
| UP-01 | Traceable OpenMAIC adaptation | QA verified | OA-01 grading, OA-02 owner-material quotas and OA-03 bounded native action/highlight patterns across all 17 Grade 8 catalog chapters are pinned, licensed and tested. A machine-readable contract verifies the pins, source list, retained license, local implementation paths and explicit exclusions; this is selective adaptation, not a port |
| QA-01 | Automated regression suite | Candidate v19 verified | GitHub run 34271215616 passed Android, backend, backend-container and repository-hygiene jobs. The candidate verifier matched commit `2d078b8`, APK/signing hashes and staging readiness; the APK installed on the Xiaomi device as version code 19. Explicit user acceptance remains separate |
| UAT-01 | User acceptance | Partial | Signed candidate v19 has a machine-valid physical-device record with 15 PASS and 10 PENDING requirements. The fixed DOC-02 issue is closed; Google OAuth, exact-candidate verbal/microphone, guardian Android UI/consent, fresh document, accessibility, production, provenance release review and external readiness-calibration decisions remain open. Explicit user acceptance cannot be inferred from agent-run evidence |
| PROD-01 | Production deployment | Missing | Private APK distribution confirmed; a host-neutral locked non-root container and hosted production-mode smoke are implemented, and candidate verification requires matching health plus database/schema/write and upload-volume readiness. User-confirmed host/domain, staging deployment, rollback, secrets and remaining operational checks are still missing |

UAT preparation now includes a machine-checkable candidate-bound record covering
every pre-production ledger ID. It rejects mismatched APK/backend/commit identity,
missing or untestable requirements, evidence-free passes, incomplete physical-device
details, timezone-free dates, unapproved scope changes and unresolved issues. This
prevents incomplete sign-off from being recorded as acceptance; it does not supply
the still-missing physical-device journeys or the user's decision. See
`docs/uat-runbook.md`.

Gamification badges are now earned only from persisted learning evidence. The
backend owns four fixed achievements for a first diagnostic answer, independently
correcting a mistake through rewrite, completing chapter mastery and starting all
four core subjects. Guided practice alone cannot award recovery. API 36 reconciled
three earned badges with the authenticated owner/Grade 8 dashboard and verified
them after process restart; the capture was visually inspected. See
`docs/learning-badges.md`. Motivation/usability, physical-device accessibility and
user acceptance remain open, so UX-01 stays partial.

Uploaded-document progress is now derived from persisted server quizzes and answers,
not Android counters. Fully completed attempts alone drive the improvement trend;
unfinished work remains visible in cumulative answer totals. API 36 verified three
completed attempts, 27 answers, completion timestamps, retry provenance, 22% overall
accuracy and a 30 percentage-point improvement, then matched those values to the
rendered progress card. A later attribution pass migrated historical rows without
guessing, persisted selected chapter IDs, rejected invented live-provider concept
labels, preserved attribution across mistake retries, and rendered separately
reconciled chapter accuracy plus grounded Chlorophyll/Chloroplasts concept evidence
on API 36. See `document-learning-progress.md`.

Private APK packaging now fails closed without a non-local HTTPS endpoint, a clean
commit and all four environment-only signing inputs. The build helper verifies the
signature and records commit, APK/certificate hashes, APK version and backend URL
without secret values. A disposable-key `assembleRelease`/APK Signature Scheme v2
check passed; this is packaging QA, not an owned production signature, reachable
backend, UAT candidate or deployment. See `private-apk-release.md`.

Private release versioning now requires an explicit positive monotonic version code
and semantic version name. The build refuses to overwrite an output directory's
existing candidate unless its version code increases, and verifies the packaged APK
matches both requested values. This repairs ambiguous `versionCode=1` artifacts but
does not itself create a UAT candidate without a confirmed reachable HTTPS backend.
The owned signing identity then passed an API 36 upgrade from the rebuilt commit
`3154cd4` version-1 APK to commit `0c30e05` version 2 (`0.2.0-qa.1`); Android retained
the package UID and signing key set. Both artifacts intentionally target
`https://qa.invalid`, so this is upgrade QA rather than a distributable candidate.

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

The two-account API 36 journey now also gives only Account A an uploaded document.
Account B's library remains empty; after switching back, Account A restores its
document and first-chapter selection across process restart. Combined with distinct
server progress, distinct interests and encrypted session restoration, this advances
DATA-01 to QA verified for the tested account-scoped state. Multi-device races,
physical-device behavior and user UAT remain open; see `authentication-recovery.md`.

API 36 authenticated-decryption QA altered a real encrypted session only inside the
dedicated app sandbox. Startup failed closed, displayed safe recovery, cleared both
credential fields across restart and allowed password reauthentication. The synthetic
account was deleted. This covers ciphertext corruption with AndroidKeyStore but not
OEM key invalidation, hardware-backed certification or user UAT; see
`android-session-security.md`. Android 126 JVM tests, lint and debug assembly pass.

Upload retries now use a durable owner-scoped UUID and transactional server replay
mapping. Identical retries return the original document, changed content conflicts,
and concurrent identical requests commit once. Backend 473 tests passed with one
existing Windows skip; Android build/lint and 138 JVM tests passed. API 36 post-commit
503 injection retained the identity, reselected the same file, reopened the single
original document and cleared the identity after confirmation. DOC-01 remains
partial for cancellation/background transfer, broader malformed/network failures,
physical-device accessibility, UAT and production evidence; see `upload-progress.md`.

MAST-01 is now QA verified. The rewrite unlock flag was corrected so mastery only
claims an unlock when the completed chapter is an actual prerequisite in the catalog;
concrete access remains the grade-scoped dashboard list. Backend 476 tests passed
with one existing Windows skip, including final-rewrite cases with and without a
dependent chapter. Separate API 36 reruns verified all-item mastery, remediation and
restart; server unlock, stale relock and refresh recovery; foreground-only timed
presence; and a matching honest seven-day display (`1m 48s` in this disposable run).
Physical-device accessibility, curriculum authority and user UAT remain open.

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

- Educator review of the approved Grade 8 Open OER Foundation content; no national/state board alignment is claimed.
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
- 2026-09-04: a corrupted saved quiz-creation identity now fails closed with a
  specific explanation and two explicit actions: retain the uncertain retry record,
  or discard only that local record before making a new request. The production
  dialog passed Accessibility Test Framework checks and both actions on API 36;
  all 14 connected component tests plus build, lint and 58 JVM tests passed. A
  subsequent full app journey injected the corrupt account-scoped preference, proved
  keep/discard persistence, created and completed the replacement quiz, recovered a
  saved answer conflict, opened exact source evidence and restored results after
  restart. Screenshot captured. Storage-removal failure injection remains.
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
- 2026-09-04: reran both binary fixtures on API 36 and submitted a known wrong
  answer followed by a known correct answer through Android for True/False and
  Yes/No. Both runs verified feedback, process-restart restoration and next-question
  continuation. DOC-03 is QA verified for the supported single-format contract;
  live-provider Android recovery, broader materials, educator review and UAT remain.
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
  curriculum verification, or user UAT acceptance. Legacy prematurely mastered
  sessions now have an idempotent, audited repair rule; isolated production-data
  rehearsal and operator review remain required. See `premature-mastery-repair.md`.
- Adaptive mutation replay now stores the winning diagnostic-answer, practice or
  rewrite outcome atomically with its attempt, keyed by the pre-transition state.
  Identical delayed and overlapping submissions return the same outcome with one
  committed attempt; different content fails 409, ownership is checked first and
  account deletion cascades replay rows. Fourteen focused tests passed. API 36 then
  passed a post-commit 503, directly replayed question 3, finished every question
  before mastery and retained exactly five weekly learning responses. This advances
  ASM-01 to QA verified; tokenless legacy clients, simultaneous provider-work
  coalescing, physical-device and UAT gates remain. See
  `docs/adaptive-submission-preconditions.md`.
- Removed the adaptive API's tokenless compatibility path. Diagnostic-answer,
  practice and rewrite schemas now reject missing, null, blank and oversized state
  tokens before mutation. All first-party test/QA callers were migrated; 469 backend
  tests and the API 36 personalized-next-step scenario pass. The release must pair
  this backend with the current private APK because an older pre-token APK is no
  longer compatible. This closes the legacy precondition gate without claiming
  production deployment.
- Cross-subject rewrite evaluation added twelve held-out Science, English and
  Geography cases to the eight-case Fractions regression. A first 20/20 live scoring
  run exposed extra model-authored facts in full-credit comments; all learner-visible
  score feedback is now server-owned, and a second `gpt-5-mini` run passed 20/20
  while verifying the fixed score-4 confirmation. This advances TUT-04 to QA
  verified, not calibrated accuracy, curriculum approval or UAT. See
  `docs/rewrite-cross-subject-evaluation.md`.
- Progress account-isolation QA: the extended `scripts/qa-account-switch.ps1`
  scenario created two synthetic accounts, seeded assessed progress only for the
  first, verified the second displayed no assessment rather than leaked progress,
  then restored the first account's backend-derived 100% Mathematics value after
  sign-out/sign-in and forced app restart. Both accounts retained only their own
  interests and were deleted. The API 36 screenshot was inspected; see
  `docs/progress-account-isolation.md`. This advances PROG-01 to QA verified, not
  physical-device or user acceptance.
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
  lifecycle/idle signals and time displays were not connected at that stage. This
  measures presence, not attention. See
  `shared/contracts/study-presence.md`.
- Progress and weekly-report responses now include owner/grade-scoped observed
  study seconds. Weekly totals clip each interval to the exact reporting window;
  untracked history stays zero. Backend 184 tests passed, including both boundaries,
  aggregate/grade and other-owner checks. Android emission/display and device QA
  remained pending at that stage. See the study-presence contract.
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
- API 36 voice-input recovery launched the real recognition activity from a typed
  tutor-question draft, cancelled it, and preserved the exact text with explicit
  feedback. Disabling the emulator speech package exercised the missing-activity
  fallback; a `finally` block restored the package, the draft remained unchanged,
  and no tutor question was sent. Screenshot inspected. Successful recognition,
  transcript/acoustic quality, physical-device accessibility and UAT remain open.
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
  `foundation-2026-09` server catalog loading for Grade 8. Grades 1–7 and 9–12
  remain visible as planned expansion but cannot be selected, restored or requested;
  the backend rejects them before provider work or session creation. Unknown pairs are
  rejected before any provider call; prerequisite locks derive from the same graph.
  Android validates grade, board, subject order/identity and chapter integrity with
  no static fallback, and clears stale catalog data when the grade changes. API 36
  opened every Grade 8 subject list and restored the catalog after process restart;
  the board-unconfirmed disclosure was visually inspected. Follow-up API 36 QA
  changed to grade selection, verified Grade 9 was marked coming later and disabled,
  and confirmed a tap could not enter a mislabeled catalog. It then selected Grade 8
  and retained the catalog after restart. Both catalog and grade-boundary frames were
  visually inspected. Mastery sessions now persist and return their creation
  catalog version; legacy databases are migrated, and Android refuses to map an
  older saved lesson into a changed catalog while retaining its server record.
  API 36 verified that restart path, absence of the local resume action, current
  catalog rendering and an authenticated read of the retained legacy-version server
  session. Current regression passed 634 backend tests with one existing Windows
  skip and 176 Android JVM tests with zero failures/skips; lint and debug assembly
  passed. The API 36 journey passed and its Grade 8 boundary screenshot was visually
  inspected without clipping. See
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
- Defined and exposed the learner-data retention policy from authenticated server
  configuration. Android validates and displays active-data, document, deletion,
  crash-orphan, guardian-invitation and backup periods. New format-2 backups carry
  timezone-aware creation evidence; pruning previews by default, verifies every
  direct-child bundle, and requires an explicit deletion flag. API 36 registration,
  wrong-password recovery, persisted-session restart and policy disclosure passed
  and the Settings capture was visually inspected. Backend 570 passed with one
  existing Windows skip; Android JVM tests, lint and debug assembly passed. This is
  implementation and emulator QA, not proof of a production schedule, storage-
  provider erasure, legal review or UAT; see `data-retention.md`.
- Extended the deterministic Grade 8 catalog explorer journey across all 13 newer
  specialized routes with the emulator's installed TalkBack service genuinely
  active. Each fresh-account path exposed its heading, changed selection and
  route-specific instructional description in the accessibility hierarchy, kept
  the server session in tutor state with zero coaching and mastery mutation, and
  restored prior accessibility and notification-permission settings. All 13 routes
  passed on the dedicated API 36 AVD. This is service-active hierarchy evidence,
  not manual spoken traversal, physical-device usability, curriculum-board approval
  or UAT; see `chapter-explorer-device-qa.md`.
- Replaced the backend origin's confusing framework 404 with a non-sensitive
  service landing response that points operators to `/health` and `/docs`. A live
  localhost restart returned 200 for the root and health routes, the root appeared
  in OpenAPI, and the complete backend regression passed 602 tests with one existing
  Windows skip. This does not supply the still-missing public production origin.
- Reconciled UP-01 with the completed selective OpenMAIC boundary. A checked-in
  machine-readable contract now binds OA-01 through OA-03 to exact upstream
  revisions and source paths, the retained MIT license, resolvable local
  implementations and explicit exclusions. Every upstream object was resolved
  from the official `THU-MAIC/OpenMAIC` remote; Android's route regression passed
  for all 17 allowlisted Grade 8 explorers. This verifies traceability, not a full
  upstream port or curriculum-board approval.
- Extended the hosted production-shaped contention gate from one container to two
  independent read-only containers, each running two workers against one shared
  runtime volume. The load client distributes authenticated requests across both
  origins and requires readiness plus final learner identity/preferences to agree
  through each instance. This closes same-host multi-instance correctness only;
  cross-host storage, soak duration and deployed capacity remain open.
- Added a host-neutral production Compose stack with an Nginx TLS boundary, private
  API network, external runtime volume, read-only/no-new-privileges containers,
  exact multipart ceiling, slow-client/upstream timeouts and bounded per-IP bursts.
  Hosted CI boots it with a disposable certificate and verifies readiness through
  HTTPS plus absence of a published API port. This is deployment-package evidence,
  not a trusted certificate, real domain, durable host or production acceptance.
- Hosted quality run 33927404992 passed repository hygiene, all 608 backend tests
  (with one platform skip), Android JVM/lint/debug assembly, and the locked
  production image/HTTPS Compose smoke at commit `d89b8f7`. The production smoke
  first reproduced concurrent Uvicorn workers racing to migrate the same legacy
  SQLite schema; startup now holds an exclusive migration transaction with a
  bounded busy timeout, and an eight-caller legacy-schema regression verifies the
  repair. This proves same-host concurrent startup for the tested stack, not a
  public deployment, trusted certificate, production migration rehearsal or UAT.
