from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import sqlite3

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth_throttle import consume_auth_attempt, limit_authentication
from app.config import Settings, get_settings
from app.database import connection, initialize
from app.main import app


@pytest.fixture
def settings(tmp_path):
    result = Settings(runtime_dir=tmp_path, jwt_secret='fixture-secret', auth_attempts_per_window=3)
    initialize(result.database_path)
    return result


def test_window_expiry_denials_do_not_extend_and_clients_are_isolated(settings):
    for _ in range(3):
        assert consume_auth_attempt(settings, '192.0.2.1', 100) == 0
    assert consume_auth_attempt(settings, '192.0.2.1', 101.5) == 59
    assert consume_auth_attempt(settings, '192.0.2.1', 159.5) == 1
    assert consume_auth_attempt(settings, '192.0.2.2', 159.5) == 0
    assert consume_auth_attempt(settings, '192.0.2.1', 160) == 0


def test_database_persists_limits_without_raw_peer(settings):
    for _ in range(3):
        consume_auth_attempt(settings, '192.0.2.1', 100)
    # New settings object and connection simulate a worker restart.
    assert consume_auth_attempt(replace(settings), '192.0.2.1', 101) == 59
    with connection(settings.database_path) as db:
        row = dict(db.execute('SELECT * FROM auth_attempt_windows').fetchone())
    assert len(row['client_digest']) == 64
    assert '192.0.2.1' not in str(row)
    assert set(row) == {'client_digest', 'expires_at', 'attempts'}


def test_parallel_admission_cannot_exceed_limit(settings):
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: consume_auth_attempt(settings, '192.0.2.1', 100), range(20)))
    assert results.count(0) == 3
    assert results.count(60) == 17


def test_capacity_fails_closed_and_expired_rows_are_reclaimed(settings, monkeypatch):
    monkeypatch.setattr('app.auth_throttle.MAX_CLIENT_WINDOWS', 1)
    consume_auth_attempt(settings, 'peer-a', 100)
    with pytest.raises(HTTPException) as failure:
        consume_auth_attempt(settings, 'peer-b', 101)
    assert failure.value.status_code == 503
    assert consume_auth_attempt(settings, 'peer-b', 160) == 0
    with connection(settings.database_path) as db:
        assert db.execute('SELECT COUNT(*) FROM auth_attempt_windows').fetchone()[0] == 1


def test_database_failure_is_generic_and_closed(settings, monkeypatch):
    def broken(*args):
        raise sqlite3.OperationalError('sensitive filesystem path')
    monkeypatch.setattr('app.auth_throttle.consume_auth_attempt', broken)
    with pytest.raises(HTTPException) as failure:
        limit_authentication(Request({'type': 'http', 'client': ('192.0.2.1', 123)}), settings)
    assert failure.value.status_code == 503
    assert 'sensitive' not in failure.value.detail
    assert failure.value.headers == {'Retry-After': '5'}


def test_all_auth_routes_share_admission_and_ignore_spoofed_forwarding(monkeypatch, tmp_path):
    monkeypatch.setenv('LEARNING_RUNTIME_DIR', str(tmp_path))
    monkeypatch.setenv('LEARNING_AUTH_ATTEMPTS', '2')
    monkeypatch.setenv('LEARNING_AUTH_WINDOW_SECONDS', '60')
    monkeypatch.setattr('app.auth_throttle.time.time', lambda: 100)
    with TestClient(app) as client:
        credentials = {'email': 'limit@example.com', 'password': 'long-enough-password'}
        registered = client.post('/v1/auth/register', json=credentials)
        assert registered.status_code == 201
        assert client.post('/v1/auth/login', json=credentials).status_code == 200
        for route, body in [('login', credentials), ('register', credentials), ('google', {'id_token': 'fake'})]:
            response = client.post('/v1/auth/' + route, json=body, headers={'X-Forwarded-For': '192.0.2.99', 'Forwarded': 'for=192.0.2.88'})
            assert response.status_code == 429
            assert response.headers['Retry-After'] == '60'
            assert 'fake' not in response.text and credentials['email'] not in response.text
        assert client.get('/v1/account', headers={'Authorization': 'Bearer ' + registered.json()['access_token']}).status_code == 200
        monkeypatch.setattr('app.auth_throttle.time.time', lambda: 160)
        assert client.post('/v1/auth/login', json=credentials).status_code == 200


@pytest.mark.parametrize('name,value', [('LEARNING_AUTH_ATTEMPTS', '0'), ('LEARNING_AUTH_ATTEMPTS', '1001'), ('LEARNING_AUTH_WINDOW_SECONDS', '0'), ('LEARNING_AUTH_WINDOW_SECONDS', '3601'), ('LEARNING_AUTH_ATTEMPTS', 'invalid')])
def test_invalid_configuration_rejected(monkeypatch, tmp_path, name, value):
    monkeypatch.setenv('LEARNING_RUNTIME_DIR', str(tmp_path))
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        get_settings()
