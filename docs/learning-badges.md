# Evidence-based learning badges

## Product contract

Badges are derived by the backend from durable, owner-scoped mastery sessions and
attempts. Android never increments badge counters or awards an achievement locally.
Deleting an account deletes the underlying evidence; grade-filtered dashboards do
not borrow achievements from another grade.

The current fixed badge vocabulary is:

- **First answer**: the learner completed a diagnostic answer.
- **Learn from mistakes**: after an independently incorrect diagnostic answer in
  one session, a later correct rewrite demonstrated recovery. Guided practice alone
  cannot earn this badge.
- **Chapter master**: a persisted mastery session reached `mastered` with a
  completion timestamp.
- **Four-subject explorer**: the learner started persisted sessions in Mathematics,
  Science, English and Social Studies within the selected grade.

Each response contains a stable ID, application-owned title/description and the
first evidence timestamp. Unknown IDs, duplicates, blank copy, inconsistent
identity and malformed lengths fail closed in Android. This prevents provider text
or untrusted learning content from becoming executable or misleading UI awards.

The learner dashboard shows only earned badges, with a visible star, explanation
and a combined accessibility description. There is no unearned-badge pressure,
leaderboard or comparison with other learners.

## Verification

Backend tests cover every threshold, earliest-earned timestamps, exclusion of
practice-only evidence, grade scope and owner isolation. Android JVM tests cover
the allowlist and malformed response rejection; unit tests, lint and debug assembly
pass.

`scripts/qa-mastery-resume.ps1 -ResetTestAppData -VerifyBadges` passed on the
dedicated API 36 emulator. One persisted wrong-answer/remediation/mastery journey
earned exactly `first_answer`, `learn_from_mistakes` and `chapter_master`. Visible
titles matched the authenticated dashboard response and survived process restart.
`artifacts/qa-learning-badges.png` was visually inspected and is readable.

This is deterministic emulator QA, not motivation/usability UAT or physical-device
accessibility acceptance. The four-subject badge has automated backend coverage but
was not earned in this single-subject device journey.
