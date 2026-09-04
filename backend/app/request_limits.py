"""ASGI request-body admission before multipart parsing or endpoint dispatch."""
from __future__ import annotations

import json

from .config import get_settings


MAX_REQUEST_ENVELOPE_BYTES = 256 * 1024


class RequestBodyTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        limit = get_settings().max_upload_bytes + MAX_REQUEST_ENVELOPE_BYTES
        lengths = [value for name, value in scope.get('headers', [])
                   if name.lower() == b'content-length']
        if lengths:
            try:
                declared = int(lengths[-1])
            except ValueError:
                await self._reject(send, 400, 'Invalid Content-Length')
                return
            if declared < 0:
                await self._reject(send, 400, 'Invalid Content-Length')
                return
            if declared > limit:
                await self._reject(send, 413, 'Request body exceeds the configured limit')
                return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message['type'] == 'http.request':
                received += len(message.get('body', b''))
                if received > limit:
                    raise RequestBodyTooLarge
            return message

        started = False

        async def tracked_send(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except RequestBodyTooLarge:
            if started:
                raise
            await self._reject(send, 413, 'Request body exceeds the configured limit')

    @staticmethod
    async def _reject(send, status: int, detail: str) -> None:
        body = json.dumps({'detail': detail}, separators=(',', ':')).encode()
        await send({'type': 'http.response.start', 'status': status, 'headers': [
            (b'content-type', b'application/json'),
            (b'content-length', str(len(body)).encode()),
        ]})
        await send({'type': 'http.response.body', 'body': body})
