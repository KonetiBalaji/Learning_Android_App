# Optional learner interests

Backend contract: authenticated `PUT /v1/account/interests` accepts an `interests`
array with zero to three unique choices from sports, music, art, nature, space and
games. Unknown choices, arbitrary text, duplicate choices, extra fields and
oversized selections are rejected. An empty list clears personalization.
`GET /v1/account` now includes the current interests. A separate owner-keyed
preference table keeps existing user rows compatible and cascades on account deletion.

New tutor explanations read that learner's saved interests. The OpenAI prompt
permits a relevant worked-example analogy without forcing one, inferring personal
traits or changing the verified method. Interests are not sent to rewrite grading
or used to award mastery. The original practice question is enforced server-side
after parsing so generated wording cannot invalidate its saved answer key.
Previously saved tutor lessons remain unchanged on resume.

The deterministic/scripted QA provider does not personalize examples. The live
provider retains response storage disabled. The user's existing-key reuse approval
remains in effect; no secret was changed or displayed, and this slice made no live
provider calls.

Verification: **88 backend tests passed** on 2026-09-03. New tests cover defaults,
save/read/clear, invalid inputs, owner isolation, account-deletion cascade, routing
saved interests to explanation generation, prompt constraints and preserving the
practice question. Mock prompt checks are not evidence of analogy accuracy.

Android Settings now offers Learning interests with explicit AI-provider-use
disclosure, selection limit, save acknowledgement and Clear all plus Save. Opening
the editor reads server preferences; leaving and reopening discards unsaved edits.
Load failure cannot be mistaken for an empty saved preference, and saving is
disabled until a successful load. Failed saves retain the draft for retry.

Android build/lint/**38 JVM tests passed** on 2026-09-03, including selection-limit,
removal and unknown-choice tests. `scripts/qa-interests.ps1 -ResetTestAppData` passed
on LearnSmart_API36 with a disposable account and scripted backend. It verifies
initial empty state, three choices persisted to the API, restoration after force
stop/restart, and clearing followed by another restart. The selector screenshot
at `artifacts/qa-interests.png` was visually inspected. No live AI calls were made.

TUT-03 remains partial: live age-appropriate example evaluation, offline/failing
save injection and device account-switch tests remain required. Existing saved
examples do not change when interests are edited. No full personalization or UAT
completion is claimed.
