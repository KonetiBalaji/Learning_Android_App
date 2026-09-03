from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import importlib

import pytest
from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


@pytest.mark.parametrize('phase,payload,setup_attempts', [
    ('diagnostic-answer', {'selected_option': '1'}, 0),
    ('practice', {'response': '7/8'}, 1),
    ('rewrite', {'response': 'We add the numerator parts with the same denominator to make one whole.'}, 2),
])
def test_overlapping_submissions_commit_only_one_transition(monkeypatch, tmp_path, phase, payload, setup_attempts):
    client, headers = registered_client(monkeypatch, tmp_path)
    api = importlib.import_module('app.main')
    original = api.owned_mastery_session
    try:
        session = client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        path = f"/v1/mastery/sessions/{session['id']}"
        if phase != 'diagnostic-answer':
            assert client.post(path + '/diagnostic-answer', headers=headers, json={'selected_option': '1/2'}).status_code == 200
        if phase == 'rewrite':
            assert client.post(path + '/practice', headers=headers, json={'response': '6/8'}).status_code == 200
        barrier = Barrier(2)
        def read_same_snapshot(*args):
            row = original(*args)
            barrier.wait(timeout=5)
            return row
        monkeypatch.setattr(api, 'owned_mastery_session', read_same_snapshot)
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(client.post, path + '/' + phase, headers=headers, json=payload) for _ in range(2)]
            statuses = sorted(future.result(timeout=15).status_code for future in futures)
        monkeypatch.setattr(api, 'owned_mastery_session', original)
        assert statuses == [200, 409]
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM mastery_attempts WHERE session_id = ?', (session['id'],)).fetchone()[0] == setup_attempts + 1
            row = db.execute('SELECT * FROM mastery_sessions WHERE id = ?', (session['id'],)).fetchone()
            assert row['current_question'] == (0 if phase == 'practice' else 1)
            assert row['coaching_rounds'] == (1 if phase == 'practice' else 0)
    finally:
        monkeypatch.setattr(api, 'owned_mastery_session', original)
        client.__exit__(None, None, None)
