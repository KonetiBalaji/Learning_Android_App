# Document quiz configuration

The original brief requests 5/10/15/20/custom question counts, difficulty choices
and multiple question types. Android now exposes the four count presets and a
custom whole-number input within the backend's supported 5–20 range. Default is
10. Invalid or empty input disables generation and shows a validation message.
The selected count is sent to the backend instead of the previous hard-coded 10.

Count input is saved under an account-scoped device preference and restored when
opening or resuming uploaded material. It is a device preference, not a synced
server profile. Invalid drafts remain invalid on restoration rather than silently
switching the requested count. Existing quizzes still display their actual saved
total; changing this preference does not change previously generated quizzes.

The live provider already validates exact question count. The deterministic QA
generator now also rejects insufficient material instead of silently generating
fewer questions. This is not a claim that QA recall questions match live AI quality.

On 2026-09-03: 111 backend tests and Android build/lint/47 JVM tests passed.
Count tests cover all integers 5–20, invalid input, exact generation for preset
counts plus custom 7, and insufficient-material rejection. No live AI requests
were made.

API 36 device QA subsequently passed on 2026-09-03 using
`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyLibrary -VerifyQuestionCount`.
The updated debug APK and refreshed localhost scripted backend used a disposable
account and synthetic Plants material. The test exercised all four presets,
verified their generation labels, entered invalid 21 and observed disabled
generation with validation feedback, then entered custom 7 and restarted.
The saved count and Generate 7 action restored. The backend returned exactly
seven questions, and Android showed the correct total after another restart.
Conflict recovery, results restoration and library reopening passed without
changing the existing seven-question quiz. Remaining answers were API-driven.
`artifacts/qa-document-count.png` was visually inspected; controls and text were
readable. No live AI requests were made.

Account switching, invalid-draft restart, physical devices, large-font/TalkBack
coverage and live generation across counts remain unverified. Preset buttons
were exercised but this device run generated only the custom seven-question quiz;
it does not verify live generation at every supported count.

Difficulty now has a backend request/persistence/resume contract, with explicit
recall/application/multi-fact reasoning guidance for live generation. Deterministic
mode rejects Medium/Hard/Mixed instead of mislabelling recall content. Existing
quizzes migrate to unspecified difficulty. On 2026-09-03, 120 backend tests passed;
five difficulty tests passed again after refining the migration fixture. Tests
cover enum validation, routing, prompt guidance, persistence, repeated startup,
legacy migration and refusal without saved quizzes. Mocked provider checks are
not evidence of achieved difficulty. See `shared/contracts/document-configuration.md`.

Android now includes accessible single-choice Easy/Medium/Hard/Mixed controls
with short descriptions. New preferences default to Easy and persist per account
on the device. The selected value is sent on creation; question and result screens
display server-returned requested difficulty, including after resume, rather than
using the current preference. Legacy quizzes are labelled unspecified. The UI
discloses that difficulty is not measured ability and that offline generation
supports only Easy recall. Invalid saved preference values fall back to Easy.

Android build/lint/49 JVM tests passed on 2026-09-03. New tests cover valid and
invalid preference restoration and unspecified legacy labels. No live AI requests
were made. Device selection/restart/account-switch tests, failure recovery for
unsupported offline levels, visual/accessibility review and live difficulty
quality evaluation remain pending. This is implemented UI, not completed QA.

Difficulty quality evaluation, true/false and yes/no question modes remain
incomplete. Custom counts
outside 5–20 are not supported. Full quiz configuration, UAT and production
completion are not claimed.
