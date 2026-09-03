import uuid

import pytest

from app.config import get_settings
from app.database import connection
from app.learning_path import PREREQUISITES
from app.mastery_service import FRACTION_DIAGNOSTIC, serialize_diagnostic_bank
from test_mastery_loop import registered_client


def seed(headers, subject, chapter, grade=8, status='mastered'):
    # Fixture state only; production mastery is obtained through assessed answers.
    from app.security import current_user_id
    from fastapi.security import HTTPAuthorizationCredentials
    owner = current_user_id(HTTPAuthorizationCredentials(scheme='Bearer', credentials=headers['Authorization'].split()[1]), get_settings())
    with connection(get_settings().database_path) as db:
        db.execute('''INSERT INTO mastery_sessions
            (id, owner_id, grade, subject_id, chapter_id, started_at, status, current_question, questions_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (str(uuid.uuid4()), owner, grade, subject, chapter, '2026-09-03T00:00:00+00:00', status,
             3 if status == 'mastered' else 0, serialize_diagnostic_bank(FRACTION_DIAGNOSTIC)))


@pytest.mark.parametrize('subject,chapter', PREREQUISITES)
def test_locked_diagnostics_require_current_owner_grade_mastery(monkeypatch, tmp_path, subject, chapter):
    import app.main as api
    client, headers = registered_client(monkeypatch, tmp_path)
    calls = []

    class FixtureProvider:
        def diagnostic_bank(self, *args):
            calls.append(args)
            return FRACTION_DIAGNOSTIC

    monkeypatch.setattr(api, 'tutor_provider', lambda settings: FixtureProvider())
    try:
        payload = {'grade': 8, 'subject_id': subject.upper(), 'chapter_id': chapter.upper()}
        path = '/v1/mastery/diagnostics'
        assert client.post(path, headers=headers, json=payload).status_code == 403
        assert calls == []
        assert client.get('/v1/progress/dashboard?grade=8', headers=headers).json()['unlocked_chapter_ids'] == []
        required = PREREQUISITES[subject, chapter]
        seed(headers, subject, required, grade=7)
        assert client.post(path, headers=headers, json=payload).status_code == 403
        token = client.post('/v1/auth/register', json={'email': 'other-path@example.com', 'password': 'long-enough-password'}).json()['access_token']
        seed({'Authorization': f'Bearer {token}'}, subject, required)
        assert client.post(path, headers=headers, json=payload).status_code == 403
        seed(headers, subject, required, status='tutor')
        assert client.post(path, headers=headers, json=payload).status_code == 403
        seed(headers, subject, required)
        snapshot = client.get('/v1/progress/dashboard?grade=8', headers=headers).json()
        assert snapshot['grade'] == 8
        assert snapshot['unlocked_chapter_ids'] == [f'{subject}:{chapter}']
        assert client.get('/v1/progress/dashboard?grade=9', headers=headers).json()['unlocked_chapter_ids'] == []
        aggregate = client.get('/v1/progress/dashboard', headers=headers).json()
        assert aggregate['grade'] is None and aggregate['unlocked_chapter_ids'] == []
        assert client.post(path, headers=headers, json=payload).status_code == 201
        assert len(calls) == 1
        seed(headers, subject, required, status='diagnostic')
        assert client.get('/v1/progress/dashboard?grade=8', headers=headers).json()['unlocked_chapter_ids'] == []
        assert client.post(path, headers=headers, json=payload).status_code == 403
        assert len(calls) == 1
    finally:
        client.__exit__(None, None, None)


def test_prerequisite_rechecked_after_provider_work(monkeypatch, tmp_path):
    import app.main as api
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        seed(headers, 'math', 'algebra')

        class RacingProvider:
            def diagnostic_bank(self, *args):
                seed(headers, 'math', 'algebra', status='diagnostic')
                return FRACTION_DIAGNOSTIC

        monkeypatch.setattr(api, 'tutor_provider', lambda settings: RacingProvider())
        response = client.post('/v1/mastery/diagnostics', headers=headers,
                               json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'geometry'})
        assert response.status_code == 403
        with connection(get_settings().database_path) as db:
            assert db.execute("SELECT COUNT(*) FROM mastery_sessions WHERE chapter_id = 'geometry'").fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)
