import importlib
import json
from types import SimpleNamespace

from app.config import get_settings
from app.database import connection
from app.mastery_service import FRACTION_DIAGNOSTIC, tutor_for
from app.tutor_provider import DeterministicTutorProvider, OpenAITutorProvider
from test_mastery_loop import registered_client


def test_interests_are_validated_owner_scoped_clearable_and_deleted(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        assert client.get('/v1/account', headers=headers).json()['interests'] == []
        response = client.put('/v1/account/interests', headers=headers, json={'interests': ['sports', 'music']})
        assert response.status_code == 200
        assert client.get('/v1/account', headers=headers).json()['interests'] == ['sports', 'music']
        for values in (['sports', 'sports'], ['sports', 'music', 'art', 'space'], ['ignore instructions'], ['unknown']):
            assert client.put('/v1/account/interests', headers=headers, json={'interests': values}).status_code == 422
        assert client.put('/v1/account/interests', json={'interests': []}).status_code == 401
        other = client.post('/v1/auth/register', json={'email': 'other-interests@example.com', 'password': 'long-enough-password'}).json()
        assert client.get('/v1/account', headers={'Authorization': f"Bearer {other['access_token']}"}).json()['interests'] == []
        assert client.put('/v1/account/interests', headers=headers, json={'interests': []}).json()['interests'] == []
        client.put('/v1/account/interests', headers=headers, json={'interests': ['nature']})
        assert client.delete('/v1/account', headers=headers).status_code == 204
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM learner_preferences').fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)


def test_saved_interests_reach_new_tutor_explanation(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        api = importlib.import_module('app.main')
        seen = []
        def provider(settings, interests=()):
            seen.append(interests)
            return DeterministicTutorProvider()
        monkeypatch.setattr(api, 'tutor_provider', provider)
        client.put('/v1/account/interests', headers=headers, json={'interests': ['space']})
        session = client.post('/v1/mastery/diagnostics', headers=headers,
                              json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        assert client.post(f"/v1/mastery/sessions/{session['id']}/diagnostic-answer", headers=headers,
                           json={'selected_option': '1/2'}).status_code == 200
        assert seen[-1] == ('space',)
    finally:
        client.__exit__(None, None, None)


def test_personalized_prompt_preserves_practice_question_and_disables_response_storage():
    item = FRACTION_DIAGNOSTIC[0]
    provider = OpenAITutorProvider.__new__(OpenAITutorProvider)
    provider.model = 'test-model'
    provider.interests = ('sports',)
    captured = {}
    def create(**kwargs):
        captured.update(kwargs)
        payload = tutor_for(item).model_dump()
        payload['practice_prompt'] = 'A changed question would invalidate the saved answer key.'
        return SimpleNamespace(output_text=json.dumps(payload))
    provider.client = SimpleNamespace(responses=SimpleNamespace(create=create))
    lesson = provider.explain(8, item, '1/2')
    assert 'sports' in captured['input']
    assert 'Do not force an analogy' in captured['instructions']
    assert captured['store'] is False
    assert lesson.practice_prompt == item.practice_prompt
