"""Explicitly installed by the localhost QA runner, never by the production app."""
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
import json
from typing import Literal

from app.config import get_settings
from app.security import current_user_id


def install_response_fault(app):
    armed = {}

    @app.post('/__qa/documents/{document_id}/fail-next-creation-response')
    def arm_creation(document_id: str, user_id=Depends(current_user_id), settings=Depends(get_settings)):
        from app.main import owned_document
        owned_document(document_id, user_id, settings)
        if len(armed) >= 100:
            raise HTTPException(status_code=429, detail='QA fault limit reached')
        armed[f'/v1/documents/{document_id}/quizzes'] = '503'
        return {'armed': True}

    @app.get('/__qa/documents/{document_id}/created-quizzes')
    def created_quizzes(document_id: str, user_id=Depends(current_user_id), settings=Depends(get_settings)):
        from app.main import owned_document
        from app.database import connection
        owned_document(document_id, user_id, settings)
        with connection(settings.database_path) as db:
            ids = [row['id'] for row in db.execute('SELECT id FROM quizzes WHERE document_id = ? AND owner_id = ?',
                                                  (document_id, user_id))]
        return {'quiz_ids': ids}

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
        if request.method == 'POST' and response.status_code in {200, 201} and path in armed:
            mode = armed.pop(path)
            if mode == 'malformed':
                payload = json.loads(b''.join([chunk async for chunk in response.body_iterator]))
                return JSONResponse({'state_token': payload['state_token']})
            # Endpoint has committed. Substitute a gateway-like failure instead of
            # delivering the saved outcome. This is not a TCP-disconnect simulation.
            await response.body_iterator.aclose()
            return JSONResponse({'detail': 'Scripted QA response failure after commit'}, status_code=503)
        return response
