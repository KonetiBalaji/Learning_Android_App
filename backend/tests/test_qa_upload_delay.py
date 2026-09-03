from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from scripts.qa_upload_delay import install_upload_delay


def test_fixture_only_delays_upload_responses(monkeypatch):
    app = FastAPI()
    calls = []
    async def sleep(seconds):
        calls.append(seconds)
    monkeypatch.setattr('scripts.qa_upload_delay.asyncio.sleep', sleep)
    @app.post('/v1/documents')
    def upload():
        return {'saved': True}
    @app.get('/v1/documents')
    def listing():
        return []
    install_upload_delay(app, 20)
    with TestClient(app) as client:
        assert client.post('/v1/documents').json() == {'saved': True}
        assert client.get('/v1/documents').json() == []
        assert calls == [20]


def test_production_does_not_install_delay():
    from app.main import app
    assert not any(getattr(item, 'kwargs', {}).get('dispatch', lambda: None).__module__ == 'scripts.qa_upload_delay' for item in app.user_middleware)
    for value in [0, -1, 21]:
        with pytest.raises(ValueError):
            install_upload_delay(FastAPI(), value)


def test_failure_happens_after_save_and_keeps_rejected_upload_unchanged(monkeypatch):
    app = FastAPI()
    saved = []
    async def sleep(seconds):
        pass
    monkeypatch.setattr('scripts.qa_upload_delay.asyncio.sleep', sleep)
    @app.post('/v1/documents', status_code=201)
    def upload(reject: bool = False):
        if reject:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'rejected'}, status_code=422)
        saved.append('document')
        return {'id': 'document'}
    install_upload_delay(app, 1, True)
    with TestClient(app) as client:
        assert client.post('/v1/documents').status_code == 503
        assert saved == ['document']
        assert client.post('/v1/documents?reject=true').status_code == 422
        assert saved == ['document']
