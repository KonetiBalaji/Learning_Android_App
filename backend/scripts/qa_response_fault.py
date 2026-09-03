"""Explicitly installed by the localhost QA runner, never by the production app."""
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
import json
from typing import Literal

from app.config import get_settings
from app.security import current_user_id


def install_response_fault(app):
    armed = {}

    @app.post('/__qa/mastery/{session_id}/fail-next-response')
    def arm(session_id: str, mode: Literal['503', 'malformed'] = '503', user_id=Depends(current_user_id), settings=Depends(get_settings)):
        from app.main import owned_mastery_session
        owned_mastery_session(session_id, user_id, settings)
        if len(armed) >= 100:
            raise HTTPException(status_code=429, detail='QA fault limit reached')
        armed[f'/v1/mastery/sessions/{session_id}/diagnostic-answer'] = mode
        return {'armed': True}

    @app.middleware('http')
    async def replace_success(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if request.method == 'POST' and response.status_code == 200 and path in armed:
            mode = armed.pop(path)
            if mode == 'malformed':
                payload = json.loads(b''.join([chunk async for chunk in response.body_iterator]))
                return JSONResponse({'state_token': payload['state_token']})
            # Endpoint has committed. Substitute a gateway-like failure instead of
            # delivering the saved outcome. This is not a TCP-disconnect simulation.
            await response.body_iterator.aclose()
            return JSONResponse({'detail': 'Scripted QA response failure after commit'}, status_code=503)
        return response
