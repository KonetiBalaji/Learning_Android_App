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
were made. The new controls, keyboard behavior, restart/account-switch preferences
and non-default generated totals still require device QA.

Difficulty, true/false and yes/no question modes remain missing. Custom counts
outside 5–20 are not supported. Full quiz configuration, UAT and production
completion are not claimed.
