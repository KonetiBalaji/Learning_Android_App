import importlib

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.config import get_settings
from app.security import current_user_id
from scripts.qa_response_fault import install_response_fault


def test_learning_path_fixtures_are_owner_scoped_and_not_production_routes(monkeypatch, tmp_path):
    from test_mastery_loop import registered_client
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        production = importlib.import_module('app.main')
        qa = FastAPI()
        qa.include_router(production.app.router)
        install_response_fault(qa)
        other = client.post('/v1/auth/register', json={'email': 'other-fixture@example.com', 'password': 'long-enough-password'}).json()['access_token']
        with TestClient(qa) as test:
            path = '/__qa/learning-path/algebra'
            assert test.post(path, params={'state': 'mastered'}).status_code == 401
            assert test.post(path, params={'state': 'invalid'}, headers=headers).status_code == 422
            assert test.post(path, params={'state': 'mastered'}, headers=headers).status_code == 200
            assert test.get('/v1/progress/dashboard?grade=8', headers=headers).json()['unlocked_chapter_ids'] == ['math:geometry']
            assert test.get('/v1/progress/dashboard?grade=7', headers=headers).json()['unlocked_chapter_ids'] == []
            assert test.get('/v1/progress/dashboard?grade=8', headers={'Authorization': f'Bearer {other}'}).json()['unlocked_chapter_ids'] == []
            assert test.post(path, params={'state': 'diagnostic'}, headers=headers).status_code == 200
            assert test.get('/v1/progress/dashboard?grade=8', headers=headers).json()['unlocked_chapter_ids'] == []
            assert test.get('/__qa/learning-path/geometry-count', headers=headers).json() == {'sessions': 0}
            marked = test.post('/__qa/mastery/latest/mark-legacy-catalog', headers=headers)
            assert marked.status_code == 200
            assert marked.json()['catalog_version'] == 'legacy-qa'
            assert test.post('/__qa/mastery/latest/mark-legacy-catalog', headers={'Authorization': f'Bearer {other}'}).status_code == 404
        assert not any(route.path.startswith('/__qa/') for route in production.app.routes)
    finally:
        client.__exit__(None, None, None)


def test_qa_fault_is_one_shot_after_success_and_not_installed_in_production(monkeypatch):
    production = importlib.import_module('app.main')
    assert not any(route.path.startswith('/__qa/') for route in production.app.routes)
    app = FastAPI()
    app.dependency_overrides[current_user_id] = lambda: 'owner'
    app.dependency_overrides[get_settings] = lambda: None

    def owned(session_id, user_id, settings):
        if session_id != 'owned' or user_id != 'owner':
            raise HTTPException(status_code=404)
    monkeypatch.setattr(production, 'owned_mastery_session', owned)
    monkeypatch.setattr(production, 'owned_document', owned)
    committed = []

    @app.post('/v1/mastery/sessions/{session_id}/diagnostic-answer')
    def answer(session_id: str):
        committed.append(session_id)
        return {'saved': True, 'state_token': 'new-state'}

    @app.post('/v1/mastery/sessions/{session_id}/tutor-questions')
    def tutor_answer(session_id: str):
        committed.append(f'tutor:{session_id}')
        return {'request_id': 'saved-turn', 'status': 'complete'}

    @app.post('/v1/documents/{document_id}/quizzes', status_code=201)
    def create(document_id: str):
        committed.append(document_id)
        return {'id': 'saved-quiz'}

    @app.get('/v1/catalog')
    def catalog():
        return {'version': 'fixture'}

    install_response_fault(app)
    with TestClient(app) as client:
        assert client.post('/__qa/catalog/fail-next-response').status_code == 200
        assert client.get('/v1/catalog').status_code == 503
        assert client.get('/v1/catalog').json() == {'version': 'fixture'}
        assert client.post('/__qa/mastery/other/fail-next-response').status_code == 404
        assert client.post('/__qa/mastery/owned/fail-next-response').status_code == 200
        path = '/v1/mastery/sessions/owned/diagnostic-answer'
        assert client.post(path).status_code == 503
        assert committed == ['owned']
        assert client.post(path).json() == {'saved': True, 'state_token': 'new-state'}
        assert committed == ['owned', 'owned']
        assert client.post('/__qa/mastery/owned/fail-next-response?mode=malformed').status_code == 200
        broken = client.post(path)
        assert broken.status_code == 200
        assert broken.json() == {'state_token': 'new-state'}
        assert len(committed) == 3
        assert client.post(path).json()['saved'] is True
        assert client.post('/__qa/mastery/other/fail-next-tutor-response').status_code == 404
        assert client.post('/__qa/mastery/owned/fail-next-tutor-response').status_code == 200
        tutor_path = '/v1/mastery/sessions/owned/tutor-questions'
        assert client.post(tutor_path).status_code == 503
        assert committed[-1] == 'tutor:owned'
        assert client.post(tutor_path).json() == {'request_id': 'saved-turn', 'status': 'complete'}
        assert client.post('/__qa/documents/other/fail-next-creation-response').status_code == 404
        assert client.get('/__qa/documents/other/created-quizzes').status_code == 404
        assert client.post('/__qa/documents/owned/fail-next-creation-response').status_code == 200
        before = len(committed)
        assert client.post('/v1/documents/owned/quizzes').status_code == 503
        assert len(committed) == before + 1
        retry = client.post('/v1/documents/owned/quizzes')
        assert retry.status_code == 201
        assert retry.json() == {'id': 'saved-quiz'}


def test_repair_fixture_is_owner_scoped_and_failure_is_after_commit(monkeypatch, tmp_path):
    from test_mastery_loop import registered_client
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        production = importlib.import_module('app.main')
        qa = FastAPI()
        qa.include_router(production.app.router)
        install_response_fault(qa)
        body = 'Chapter 1 Cells\n' + 'Cells contain genetic material. ' * 20
        doc = client.post('/v1/documents', headers=headers, files={'file': ('qa-biology.txt', body)}).json()
        other = client.post('/v1/auth/register', json={'email': 'repair-other@example.com', 'password': 'long-enough-password'}).json()['access_token']
        arm = f"/__qa/documents/{doc['id']}/omit-tail-and-fail-repair-response"
        repair = f"/v1/documents/{doc['id']}/structure/repair"
        with TestClient(qa) as test:
            assert test.post(arm, headers={'Authorization': f'Bearer {other}'}).status_code == 404
            assert test.post(arm, headers=headers).status_code == 200
            assert test.post(arm, headers=headers).status_code == 409
            assert test.post(repair, headers=headers).status_code == 503
            fixed = test.get(f"/v1/documents/{doc['id']}", headers=headers).json()
            assert len(fixed['chapters']) == 2
            assert fixed['chapters'][-1]['end_character'] == len(body)
            assert test.post(repair, headers=headers).json() == fixed
            non_fixture = test.post('/v1/documents', headers=headers, files={'file': ('notes.txt', body)}).json()
            assert test.post(f"/__qa/documents/{non_fixture['id']}/omit-tail-and-fail-repair-response", headers=headers).status_code == 409
        assert not any(route.path.startswith('/__qa/') for route in production.app.routes)
    finally:
        client.__exit__(None, None, None)
