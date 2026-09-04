import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.operational_logging import OperationalLoggingMiddleware, request_id


def event(caplog):
    record = next(record for record in caplog.records if record.name == 'learning.http')
    return json.loads(record.message)


def test_raw_uvicorn_access_logger_is_disabled():
    assert logging.getLogger('uvicorn.access').disabled is True


def test_completion_log_uses_route_template_and_omits_sensitive_request_data(caplog):
    app = FastAPI()

    @app.get('/items/{item_id}')
    def item(item_id: str, answer: str):
        return {'item': item_id, 'answer': answer}

    app.add_middleware(OperationalLoggingMiddleware)
    supplied = '123e4567-e89b-12d3-a456-426614174000'
    caplog.set_level(logging.INFO, logger='learning.http')
    with TestClient(app) as client:
        response = client.get('/items/private-student-id?answer=private-learner-answer',
                              headers={'Authorization': 'Bearer private-token', 'X-Request-ID': supplied})
    assert response.headers['X-Request-ID'] == supplied
    logged = event(caplog)
    assert logged['route'] == '/items/{item_id}'
    assert logged['method'] == 'GET' and logged['status'] == 200
    assert logged['request_id'] == supplied and logged['duration_ms'] >= 0
    serialized = json.dumps(logged)
    for secret in ('private-student-id', 'private-learner-answer', 'private-token', 'answer='):
        assert secret not in serialized


def test_invalid_correlation_id_is_replaced_and_unmatched_route_is_safe(caplog):
    app = FastAPI()
    app.add_middleware(OperationalLoggingMiddleware)
    caplog.set_level(logging.INFO, logger='learning.http')
    with TestClient(app) as client:
        response = client.get('/private-missing-path?email=student@example.com',
                              headers={'X-Request-ID': 'attacker-controlled\nlog'})
    assert response.status_code == 404
    generated = response.headers['X-Request-ID']
    assert generated != 'attacker-controlled\nlog'
    assert request_id([(b'x-request-id', generated.encode())]) == generated
    logged = event(caplog)
    assert logged['route'] == '<unmatched>' and logged['status'] == 404
    assert 'student@example.com' not in json.dumps(logged)
