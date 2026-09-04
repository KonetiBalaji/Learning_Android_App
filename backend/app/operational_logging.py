"""Privacy-safe HTTP completion logs with bounded correlation identifiers."""
import json
import logging
from time import monotonic
from uuid import UUID, uuid4


def request_id(headers) -> str:
    supplied = next((value.decode('ascii', 'ignore') for name, value in headers
                     if name.lower() == b'x-request-id'), '')
    try:
        parsed = str(UUID(supplied))
        return parsed if supplied == parsed else str(uuid4())
    except (ValueError, AttributeError):
        return str(uuid4())


class OperationalLoggingMiddleware:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('learning.http')

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        correlation = request_id(scope.get('headers', ()))
        started = monotonic()
        status = 500

        async def observe(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
                headers = list(message.get('headers', ()))
                headers.append((b'x-request-id', correlation.encode('ascii')))
                message = {**message, 'headers': headers}
            await send(message)

        try:
            await self.app(scope, receive, observe)
        finally:
            route = getattr(scope.get('route'), 'path', '<unmatched>')
            event = {
                'event': 'http_request_complete',
                'request_id': correlation,
                'method': scope.get('method', 'UNKNOWN'),
                'route': route,
                'status': status,
                'duration_ms': max(0, round((monotonic() - started) * 1000)),
            }
            self.logger.info('%s', json.dumps(event, separators=(',', ':'), sort_keys=True))
