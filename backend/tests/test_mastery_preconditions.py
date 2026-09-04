import importlib
from dataclasses import replace

import pytest

from app.config import get_settings
from app.database import connection
from app.mastery_service import FRACTION_DIAGNOSTIC
from app.tutor_provider import DeterministicTutorProvider
from test_mastery_loop import registered_client


@pytest.mark.parametrize('phase,payload', [
    ('diagnostic-answer', {'selected_option': '1'}),
    ('practice', {'response': 'wrong'}),
    ('rewrite', {'response': 'I do not know'}),
])
def test_delayed_retry_does_not_create_another_attempt(monkeypatch, tmp_path, phase, payload):
    client, headers = registered_client(monkeypatch, tmp_path)
    api = importlib.import_module('app.main')
    provider = DeterministicTutorProvider()
    # Repeated options make an old answer valid for the new question, so option
    # validation alone cannot accidentally make the regression test pass.
    bank = (FRACTION_DIAGNOSTIC[0],
            replace(FRACTION_DIAGNOSTIC[1], options=('1', '3/6', '4/6', '5/6')),
            FRACTION_DIAGNOSTIC[2])
    monkeypatch.setattr(provider, 'diagnostic_bank', lambda *args: bank)
    monkeypatch.setattr(api, 'tutor_provider', lambda *args, **kwargs: provider)
    try:
        started = client.post('/v1/mastery/diagnostics', headers=headers,
                              json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        path = f"/v1/mastery/sessions/{started['id']}"
        token = started['state_token']
        if phase != 'diagnostic-answer':
            outcome = client.post(path + '/diagnostic-answer', headers=headers,
                json={'selected_option': '1/2', 'expected_state': token})
            assert outcome.status_code == 200
            token = outcome.json()['state_token']
        if phase == 'rewrite':
            outcome = client.post(path + '/practice', headers=headers,
                json={'response': '6/8', 'expected_state': token})
            assert outcome.status_code == 200
            token = outcome.json()['state_token']
        submitted = dict(payload, expected_state=token)
        first = client.post(path + '/' + phase, headers=headers, json=submitted)
        assert first.status_code == 200
        assert first.json()['state_token'] != token
        before = client.get(path, headers=headers).json()
        assert before['state_token'] == first.json()['state_token']
        with connection(get_settings().database_path) as db:
            attempts = db.execute('SELECT COUNT(*) FROM mastery_attempts').fetchone()[0]
        # Replay must occur before any additional paid generation/grading.
        def unexpected_provider(*args, **kwargs):
            pytest.fail('A stale submission must not call the provider')
        monkeypatch.setattr(api, 'tutor_provider', unexpected_provider)
        retry = client.post(path + '/' + phase, headers=headers, json=submitted)
        assert retry.status_code == 200
        assert retry.json() == first.json()
        assert client.get(path, headers=headers).json() == before
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM mastery_attempts').fetchone()[0] == attempts
        # Intentional repeated practice with a freshly observed token is distinct.
        if phase == 'practice':
            assert client.post(path + '/practice', headers=headers,
                json=dict(payload, expected_state=before['state_token'])).status_code == 200
    finally:
        client.__exit__(None, None, None)


def test_state_tokens_are_session_scoped_and_validated(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        sessions = [client.post('/v1/mastery/diagnostics', headers=headers,
            json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json() for _ in range(2)]
        path = f"/v1/mastery/sessions/{sessions[1]['id']}/diagnostic-answer"
        assert client.post(path, headers=headers, json={'selected_option': '1',
            'expected_state': sessions[0]['state_token']}).status_code == 409
        for token in ('', 'a' * 201):
            assert client.post(path, headers=headers,
                json={'selected_option': '1', 'expected_state': token}).status_code == 422
        assert client.post(path, headers=headers, json={'selected_option': '1',
            'expected_state': sessions[1]['state_token']}).status_code == 200
    finally:
        client.__exit__(None, None, None)
