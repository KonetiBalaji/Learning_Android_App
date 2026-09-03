from datetime import datetime, timedelta, UTC

from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


def test_presence_is_bounded_nonoverlapping_and_stops_at_completion(monkeypatch, tmp_path):
    import app.main as api
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        base = datetime.now(UTC)
        def start(grade):
            return client.post('/v1/mastery/diagnostics', headers=headers,
                json={'grade': grade, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()['id']
        first, second = start(8), start(7)
        def beat(session, elapsed):
            monkeypatch.setattr(api, 'now', lambda: (base + timedelta(seconds=elapsed)).isoformat())
            response = client.post(f'/v1/mastery/sessions/{session}/presence', headers=headers)
            assert response.status_code == 200
            assert response.json()['session_id'] == session
            return response.json()['observed_study_seconds']
        assert beat(first, 0) == 0
        assert beat(first, 30) == 30
        assert beat(first, 30) == 30  # Duplicate at the same observation time.
        assert beat(first, 20) == 30  # Clock rollback cannot rewind the cursor.
        assert beat(first, 60) == 60
        assert beat(first, 121) == 60  # Long idle/offline gap discarded completely.
        assert beat(first, 151) == 90
        assert beat(second, 160) == 0  # Switching sessions cannot credit the gap.
        assert beat(second, 190) == 30
        assert beat(first, 200) == 90
        assert beat(first, 230) == 120
        with connection(get_settings().database_path) as db:
            db.execute("UPDATE mastery_sessions SET status = 'mastered', completed_at = ? WHERE id = ?",
                       ((base + timedelta(seconds=245)).isoformat(), first))
        assert beat(first, 260) == 135  # Final report clipped to server completion.
        assert beat(first, 270) == 135
        assert beat(second, 280) == 30
        assert beat(first, 290) == 135  # Completed session cannot steal the cursor.
        assert beat(second, 310) == 60
        with connection(get_settings().database_path) as db:
            intervals = db.execute('SELECT * FROM study_time_intervals ORDER BY started_at').fetchall()
            assert all(a['ended_at'] <= b['started_at'] for a, b in zip(intervals, intervals[1:]))
    finally:
        client.__exit__(None, None, None)


def test_presence_owner_checks_and_account_deletion_cascade(monkeypatch, tmp_path):
    import app.main as api
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        session = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()['id']
        path = f'/v1/mastery/sessions/{session}/presence'
        other = client.post('/v1/auth/register', json={'email': 'other-presence@example.com', 'password': 'long-enough-password'}).json()['access_token']
        assert client.post(path).status_code == 401
        assert client.post(path, headers={'Authorization': f'Bearer {other}'}).status_code == 404
        assert client.post('/v1/mastery/sessions/missing/presence', headers=headers).status_code == 404
        base = datetime.now(UTC)
        monkeypatch.setattr(api, 'now', lambda: base.isoformat())
        assert client.post(path, headers=headers, json={'seconds': 999999}).json()['observed_study_seconds'] == 0
        monkeypatch.setattr(api, 'now', lambda: (base + timedelta(seconds=30)).isoformat())
        assert client.post(path, headers=headers).json()['observed_study_seconds'] == 30
        assert client.delete('/v1/account', headers=headers).status_code == 204
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM study_presence').fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM study_time_intervals').fetchone()[0] == 0
        assert client.post(path, headers=headers).status_code == 401
    finally:
        client.__exit__(None, None, None)
