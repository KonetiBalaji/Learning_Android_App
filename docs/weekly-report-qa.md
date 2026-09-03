# Weekly reporting evidence and limits

The earlier implementation compared ISO timestamps to SQLite space-separated
date strings, had no upper time bound, selected completions by session start,
counted repeated mastered sessions as separate chapters, and classified an empty
week as needing support. Two regression tests failed against that implementation.

The report now captures one UTC endpoint, parses timestamp instants (including
offsets), and uses a seven-day half-open interval. Invalid timestamps are excluded
from dated metrics; legacy timestamps without offsets are interpreted as UTC.
Completed chapters are deduplicated by grade/subject/chapter and validated against
the stored bank length. This does not repair legacy session records themselves.

The legacy `questions_answered` field counts every learning response, including
practice and rewrite attempts, not unique questions. Android now says so. Its
indicator is explicitly uncalibrated and not an exam prediction. Empty reports
show no evidence rather than zero accuracy or a learner weakness. The subject
cards are explicitly current/all-time assessed-chapter progress, and the fake
Mathematics=0 fallback was removed.

Verification on 2026-09-03: backend **44 tests passed**, Android build/lint and
**14 JVM tests passed**. New API regression covers microsecond boundary exclusion,
inclusive start/exclusive end, future data, timezone offsets, duplicate chapters,
older sessions completed this week, incomplete legacy mastery and empty evidence.
Existing grade-isolation tests remain passing. Synthetic fixture banks are used;
these tests do not establish curriculum accuracy or student outcomes.

Emulator `LearnSmart_API36`: the full scripted learning journey and weekly-report
extension passed after refreshing the confirmed QA fixture. An earlier run against
the stale fixture failed the new response metadata check and was not accepted.
Inspected `artifacts/qa-weekly-report.png`: five responses, 80% response accuracy,
one unique mastered chapter, 88% explicitly uncalibrated indicator, and separate
current chapter progress. The rule-based recommendation title was subsequently
renamed from "AI recommendation" to "Suggested next step"; it is not model-generated.
Status-bar contrast and full accessibility/theme validation remain UX work.

Remaining: parent identity/consent/sharing model, calibrated prediction data,
recurring-error remediation semantics, time-on-task measurement, report performance
with large histories, and user acceptance. The report currently loads scoped
history before exact timestamp filtering; load testing/indexed timestamp migration
is required before claiming production scalability.
