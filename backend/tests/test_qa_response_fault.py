import importlib

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.config import get_settings
from app.security import current_user_id
from scripts.qa_response_fault import install_response_fault


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
    committed = []

    @app.post('/v1/mastery/sessions/{session_id}/diagnostic-answer')
    def answer(session_id: str):
        committed.append(session_id)
        return {'saved': True, 'state_token': 'new-state'}

    install_response_fault(app)
    with TestClient(app) as client:
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
