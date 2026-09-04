from app.learning_badges import learning_badges


def session(identifier, subject, started, status='diagnostic', completed=None):
    return {'id': identifier, 'subject_id': subject, 'started_at': started,
            'status': status, 'completed_at': completed}


def attempt(session_id, phase, correct, created):
    return {'session_id': session_id, 'phase': phase, 'correct': int(correct),
            'created_at': created}


def test_badges_require_durable_evidence_and_use_first_earned_time():
    sessions = [
        session('m', 'math', '2026-01-01T00:00:00+00:00', 'mastered', '2026-01-02T00:00:00+00:00'),
        session('s', 'science', '2026-01-03T00:00:00+00:00'),
        session('e', 'english', '2026-01-04T00:00:00+00:00'),
        session('g', 'social', '2026-01-05T00:00:00+00:00'),
    ]
    attempts = [
        attempt('m', 'diagnostic', False, '2026-01-01T00:01:00+00:00'),
        attempt('m', 'practice', True, '2026-01-01T00:02:00+00:00'),
        attempt('m', 'rewrite', True, '2026-01-01T00:03:00+00:00'),
    ]
    badges = learning_badges(sessions, attempts)
    assert [item['id'] for item in badges] == [
        'first_answer', 'learn_from_mistakes', 'chapter_master', 'four_subject_explorer']
    assert badges[1]['earned_at'] == '2026-01-01T00:03:00+00:00'
    assert badges[3]['earned_at'] == '2026-01-05T00:00:00+00:00'


def test_guided_practice_or_incomplete_subject_coverage_does_not_award_badges():
    sessions = [session('m', 'math', '2026-01-01'), session('s', 'science', '2026-01-02')]
    attempts = [attempt('m', 'practice', True, '2026-01-01T01:00:00')]
    assert learning_badges(sessions, attempts) == []
