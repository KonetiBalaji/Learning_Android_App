"""Rolling UTC reporting; inputs must already be owner/grade scoped."""
from datetime import UTC, datetime, timedelta

from .schemas import WeeklyReport

MIN_READINESS_RESPONSES = 10
MIN_READINESS_CHAPTERS = 2
INDEPENDENT_ASSESSMENT_PHASES = frozenset({'diagnostic', 'rewrite'})


def utc_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except ValueError:
        return None


def build_weekly_report(sessions, attempts, as_of: datetime, bank_sizes: dict[str, int]) -> WeeklyReport:
    end = as_of.astimezone(UTC)
    start = end - timedelta(days=7)

    def in_window(value):
        stamp = utc_timestamp(value)
        return stamp is not None and start <= stamp < end

    by_id = {row['id']: row for row in sessions}
    responses = [row for row in attempts if row['session_id'] in by_id and in_window(row['created_at'])]
    active_ids = {row['session_id'] for row in responses}
    active_ids.update(row['id'] for row in sessions if in_window(row['started_at']) or in_window(row['completed_at']))

    def chapter_key(row):
        return row['grade'], row['subject_id'], row['chapter_id']

    active_chapters = {chapter_key(by_id[sid]) for sid in active_ids}
    completed_chapters = {chapter_key(row) for row in sessions
                          if row['status'] == 'mastered' and in_window(row['completed_at'])
                          and bank_sizes.get(row['id'], 0) > 0
                          and row['current_question'] == bank_sizes[row['id']]}
    correct = sum(int(row['correct']) for row in responses)
    concept_totals: dict[str, list[int]] = {}
    for row in responses:
        concept_totals.setdefault(row['concept'], []).append(int(row['correct']))
    scores = {name: sum(values) / len(values) for name, values in concept_totals.items()}
    strongest = [name for name, score in sorted(scores.items(), key=lambda item: (-item[1], item[0])) if score >= .7][:3]
    weak = [name for name, score in sorted(scores.items(), key=lambda item: (item[1], item[0])) if score < .7][:3]
    accuracy = correct / len(responses) if responses else 0.0
    completion = len(completed_chapters) / len(active_chapters) if active_chapters else 0.0
    independent = [row for row in responses if row['phase'] in INDEPENDENT_ASSESSMENT_PHASES]
    assessed_chapters = {chapter_key(by_id[row['session_id']]) for row in independent}
    has_readiness_evidence = (len(independent) >= MIN_READINESS_RESPONSES
                              and len(assessed_chapters) >= MIN_READINESS_CHAPTERS)
    if has_readiness_evidence:
        independent_accuracy = sum(int(row['correct']) for row in independent) / len(independent)
        readiness = round((independent_accuracy * .6 + completion * .4) * 100, 1)
        label = 'high' if readiness >= 85 else 'developing' if readiness >= 60 else 'needs_support'
    else:
        readiness = 0.0
        label = 'insufficient_evidence'
    recommendations = [f'Review {concept} for 15 minutes' for concept in weak]
    if not recommendations:
        recommendations = ['Continue with the next chapter or review a mastered concept'] if completed_chapters else ['Complete one diagnostic this week']
    return WeeklyReport(
        period_days=7, period_start=start.isoformat(), period_end=end.isoformat(),
        questions_answered=len(responses), correct_answers=correct, accuracy=accuracy,
        mastered_chapters=len(completed_chapters), active_subjects=len({by_id[sid]['subject_id'] for sid in active_ids}),
        strongest_concepts=strongest, weak_areas=weak, estimated_exam_readiness=readiness,
        readiness_label=label, readiness_is_calibrated=False, recommendations=recommendations,
    )
