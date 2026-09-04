import asyncio
from uuid import UUID

from fastapi.testclient import TestClient

from app.request_limits import MAX_REQUEST_ENVELOPE_BYTES, RequestBodyLimitMiddleware


def run_request(monkeypatch, chunks, headers=()):
    monkeypatch.setenv('LEARNING_MAX_UPLOAD_BYTES', '10')
    called = []

    async def downstream(_scope, receive, send):
        called.append(True)
        while True:
            message = await receive()
            if not message.get('more_body'):
                break
        await send({'type': 'http.response.start', 'status': 204, 'headers': []})
        await send({'type': 'http.response.body', 'body': b''})

    messages = iter([
        {'type': 'http.request', 'body': chunk, 'more_body': index < len(chunks) - 1}
        for index, chunk in enumerate(chunks)
    ])
    output = []

    async def receive():
        return next(messages)

    async def send(message):
        output.append(message)

    scope = {'type': 'http', 'method': 'POST', 'path': '/v1/documents',
             'headers': list(headers)}
    asyncio.run(RequestBodyLimitMiddleware(downstream)(scope, receive, send))
    return called, output


def test_declared_oversized_body_is_rejected_before_application(monkeypatch):
    limit = 10 + MAX_REQUEST_ENVELOPE_BYTES
    called, output = run_request(
        monkeypatch, [], [(b'content-length', str(limit + 1).encode())])
    assert called == [] and output[0]['status'] == 413
    assert output[1]['body'] == b'{"detail":"Request body exceeds the configured limit"}'


def test_streamed_body_without_length_is_bounded_while_reading(monkeypatch):
    called, output = run_request(
        monkeypatch, [b'a' * MAX_REQUEST_ENVELOPE_BYTES, b'01234567890'])
    assert called == [True] and output[0]['status'] == 413


def test_body_at_limit_reaches_application(monkeypatch):
    called, output = run_request(
        monkeypatch, [b'a' * MAX_REQUEST_ENVELOPE_BYTES, b'0123456789'])
    assert called == [True] and output[0]['status'] == 204


def test_invalid_content_length_fails_closed(monkeypatch):
    called, output = run_request(monkeypatch, [], [(b'content-length', b'not-a-number')])
    assert called == [] and output[0]['status'] == 400


def test_shipping_stack_rejects_before_route_and_keeps_support_id(monkeypatch, tmp_path):
    monkeypatch.setenv('LEARNING_RUNTIME_DIR', str(tmp_path / 'runtime'))
    monkeypatch.setenv('LEARNING_JWT_SECRET', 'test-secret-that-is-long-enough-32')
    monkeypatch.setenv('LEARNING_MAX_UPLOAD_BYTES', '1')
    from app.main import app

    with TestClient(app) as client:
        response = client.post('/v1/auth/login', content=b'a' * (MAX_REQUEST_ENVELOPE_BYTES + 2),
                               headers={'Content-Type': 'application/octet-stream'})
    assert response.status_code == 413
    assert response.json() == {'detail': 'Request body exceeds the configured limit'}
    assert str(UUID(response.headers['X-Request-ID'])) == response.headers['X-Request-ID']
