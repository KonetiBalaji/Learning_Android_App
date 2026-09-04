"""Deterministic achievements derived only from durable learning evidence."""

from collections.abc import Iterable, Mapping


BADGE_COPY = {
    'first_answer': ('First answer', 'Completed the first diagnostic answer.'),
    'learn_from_mistakes': ('Learn from mistakes', 'Corrected an independently missed concept in a rewrite.'),
    'chapter_master': ('Chapter master', 'Mastered a complete chapter.'),
    'four_subject_explorer': ('Four-subject explorer', 'Started learning in all four core subjects.'),
}


def _badge(identifier: str, earned_at: str) -> dict[str, str]:
    title, description = BADGE_COPY[identifier]
    return {'id': identifier, 'title': title, 'description': description, 'earned_at': earned_at}


def learning_badges(sessions: Iterable[Mapping], attempts: Iterable[Mapping]) -> list[dict[str, str]]:
    sessions = list(sessions)
    attempts = list(attempts)
    earned: list[dict[str, str]] = []

    diagnostics = [row for row in attempts if row['phase'] == 'diagnostic']
    if diagnostics:
        earned.append(_badge('first_answer', min(row['created_at'] for row in diagnostics)))

    attempts_by_session: dict[str, list[Mapping]] = {}
    for row in attempts:
        attempts_by_session.setdefault(row['session_id'], []).append(row)
    recovered_at = []
    for rows in attempts_by_session.values():
        missed = False
        for row in rows:
            if row['phase'] == 'diagnostic' and not row['correct']:
                missed = True
            elif missed and row['phase'] == 'rewrite' and row['correct']:
                recovered_at.append(row['created_at'])
                break
    if recovered_at:
        earned.append(_badge('learn_from_mistakes', min(recovered_at)))

    mastered = [row for row in sessions if row['status'] == 'mastered' and row['completed_at']]
    if mastered:
        earned.append(_badge('chapter_master', min(row['completed_at'] for row in mastered)))

    required = {'math', 'science', 'english', 'social'}
    seen: set[str] = set()
    explored_at = None
    for row in sorted(sessions, key=lambda item: item['started_at']):
        seen.add(row['subject_id'])
        if required <= seen:
            explored_at = row['started_at']
            break
    if explored_at:
        earned.append(_badge('four_subject_explorer', explored_at))

    return sorted(earned, key=lambda item: (item['earned_at'], item['id']))
