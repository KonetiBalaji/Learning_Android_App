from datetime import UTC, datetime

from test_mastery_loop import registered_client
from app.database import connection
from app.config import get_settings
from app.mastery_service import diagnostic_bank, serialize_diagnostic_bank
from app.weekly_reporting import load_weekly_rows


def test_weekly_window_and_distinct_completion_use_activity_not_session_start(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr('app.main.now', lambda: '2026-09-03T12:00:00+00:00')
        owner = client.get('/v1/account', headers=headers).json()['id']
        with connection(get_settings().database_path) as db:
            for sid, chapter, started, completed, index in [
                ('old-completed-now', 'fractions', '2026-08-01T00:00:00+00:00', '2026-09-02T11:00:00+00:00', 3),
                ('repeat', 'fractions', '2026-09-01T00:00:00+00:00', '2026-09-02T12:00:00+00:00', 3),
                ('legacy-false-mastery', 'decimals', '2026-09-01T00:00:00+00:00', '2026-09-02T12:00:00+00:00', 1),
                ('future', 'algebra', '2026-09-04T00:00:00+00:00', '2026-09-04T12:00:00+00:00', 3),
                ('stale', 'geometry', '2026-01-01T00:00:00+00:00', None, 0),
            ]:
                db.execute('INSERT INTO mastery_sessions (id, owner_id, grade, subject_id, chapter_id, started_at, completed_at, status, current_question, questions_json) VALUES (?, ?, 8, ?, ?, ?, ?, ?, ?, ?)',
                           (sid, owner, 'math', chapter, started, completed, 'mastered', index,
                            serialize_diagnostic_bank(diagnostic_bank('math', 'fractions'))))
            for aid, timestamp, correct in [
                ('before-start', '2026-08-27T11:59:59.999999+00:00', 0),
                ('at-start', '2026-08-27T12:00:00+00:00', 1),
                ('inside-offset', '2026-08-28T13:00:00+01:00', 1),
                ('before-end', '2026-09-03T11:59:59.999999+00:00', 0),
                ('at-end', '2026-09-03T12:00:00+00:00', 1),
                ('future', '2026-09-04T00:00:00+00:00', 1),
                ('stale', '2026-01-02T00:00:00+00:00', 1),
            ]:
                session_id = 'stale' if aid == 'stale' else 'old-completed-now'
                db.execute('INSERT INTO mastery_attempts (id, session_id, phase, prompt, response, correct, concept, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                           (aid, session_id, 'diagnostic', 'synthetic', 'synthetic', correct, 'Fractions', timestamp))
            sessions, attempts = load_weekly_rows(
                db, owner, 8, datetime(2026, 9, 3, 12, tzinfo=UTC))
            assert 'stale' not in {row['id'] for row in sessions}
            assert {row['id'] for row in attempts} == {
                'before-start', 'at-start', 'inside-offset', 'before-end', 'at-end', 'future'}
            plan = db.execute(
                "EXPLAIN QUERY PLAN SELECT * FROM mastery_attempts WHERE created_at >= ? AND created_at < ?",
                ('2026-08-26', '2026-09-05'),
            ).fetchall()
            assert 'mastery_attempts_created_idx' in ' '.join(row['detail'] for row in plan)
        report = client.get('/v1/progress/weekly-report?grade=8', headers=headers).json()
        assert report['questions_answered'] == 3
        assert report['correct_answers'] == 2
        assert report['mastered_chapters'] == 1
        assert report['active_subjects'] == 1
        assert report['period_start'] == '2026-08-27T12:00:00+00:00'
        assert report['period_end'] == '2026-09-03T12:00:00+00:00'
        assert report['readiness_is_calibrated'] is False
        assert report['estimated_exam_readiness'] == 0.0
        assert report['readiness_label'] == 'insufficient_evidence'
        assert report['strongest_concepts'] == []  # 2/3 is below the 70% evidence threshold.
        assert report['weak_areas'] == ['Fractions']
        assert client.get('/v1/progress/weekly-report?grade=6', headers=headers).json()['questions_answered'] == 0
        other = client.post('/v1/auth/register', json={'email': 'other-weekly@example.com', 'password': 'long-enough-password'}).json()
        other_report = client.get('/v1/progress/weekly-report?grade=8', headers={'Authorization': f"Bearer {other['access_token']}"}).json()
        assert other_report['questions_answered'] == other_report['mastered_chapters'] == 0
        with connection(get_settings().database_path) as db:
            db.execute("""INSERT INTO mastery_sessions (id, owner_id, grade, subject_id, chapter_id, started_at, completed_at, status, current_question, questions_json)
                          SELECT 'another-grade', owner_id, 6, subject_id, chapter_id, started_at, completed_at, status, current_question, questions_json
                          FROM mastery_sessions WHERE id = 'old-completed-now'""")
        assert client.get('/v1/progress/weekly-report', headers=headers).json()['mastered_chapters'] == 2
        assert client.get('/v1/progress/weekly-report?grade=8', headers=headers).json()['mastered_chapters'] == 1
    finally:
        client.__exit__(None, None, None)


def test_empty_week_has_no_claimed_strength_or_readiness_evidence(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        report = client.get('/v1/progress/weekly-report?grade=8', headers=headers).json()
        assert report['questions_answered'] == report['mastered_chapters'] == report['active_subjects'] == 0
        assert report['readiness_label'] == 'insufficient_evidence'
        assert report['strongest_concepts'] == report['weak_areas'] == []
    finally:
        client.__exit__(None, None, None)


def test_readiness_uses_only_sufficient_independent_cross_chapter_evidence(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr('app.main.now', lambda: '2026-09-03T12:00:00+00:00')
        owner = client.get('/v1/account', headers=headers).json()['id']
        with connection(get_settings().database_path) as db:
            bank = serialize_diagnostic_bank(diagnostic_bank('math', 'fractions'))
            for session_id, chapter in [('first', 'fractions'), ('second', 'decimals')]:
                db.execute('INSERT INTO mastery_sessions (id, owner_id, grade, subject_id, chapter_id, started_at, status, current_question, questions_json) VALUES (?, ?, 8, ?, ?, ?, ?, ?, ?)',
                           (session_id, owner, 'math', chapter, '2026-09-01T00:00:00+00:00',
                            'diagnostic', 0, bank))
            attempts = [
                (f'assessment-{index}', 'first' if index < 5 else 'second',
                 'diagnostic' if index % 2 == 0 else 'rewrite', 1)
                for index in range(10)
            ]
            attempts.extend((f'practice-{index}', 'first', 'practice', 0) for index in range(20))
            for attempt_id, session_id, phase, correct in attempts:
                db.execute('INSERT INTO mastery_attempts (id, session_id, phase, prompt, response, correct, concept, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                           (attempt_id, session_id, phase, 'synthetic', 'synthetic', correct,
                            'Fractions', '2026-09-02T00:00:00+00:00'))
        report = client.get('/v1/progress/weekly-report?grade=8', headers=headers).json()
        assert report['questions_answered'] == 30 and report['accuracy'] == 1 / 3
        assert report['estimated_exam_readiness'] == 60.0
        assert report['readiness_label'] == 'developing'
        assert report['readiness_is_calibrated'] is False
    finally:
        client.__exit__(None, None, None)
