"""Explicitly installed by the localhost QA runner, never by the production app."""
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
import json
from typing import Literal

from app.config import get_settings
from app.security import current_user_id


def install_response_fault(app):
    armed = {}

    @app.post('/__qa/catalog/fail-next-response')
    def arm_catalog_failure(_: str = Depends(current_user_id)):
        if len(armed) >= 100:
            raise HTTPException(status_code=429, detail='QA fault limit reached')
        armed['/v1/catalog'] = '503'
        return {'armed': True}

    @app.post('/__qa/interests/fail-next-response')
    def arm_interest_failure(_: str = Depends(current_user_id)):
        if len(armed) >= 100:
            raise HTTPException(status_code=429, detail='QA fault limit reached')
        armed['/v1/account/interests'] = '503'
        return {'armed': True}

    @app.post('/__qa/learning-path/algebra')
    def seed_algebra(state: Literal['mastered', 'diagnostic'], user_id=Depends(current_user_id), settings=Depends(get_settings)):
        from app.database import connection
        from app.mastery_service import FRACTION_DIAGNOSTIC, serialize_diagnostic_bank
        from datetime import datetime, UTC
        from uuid import uuid4
        # A fixture state transition, not an assessment or production capability.
        with connection(settings.database_path) as db:
            db.execute('''INSERT INTO mastery_sessions
                (id, owner_id, grade, subject_id, chapter_id, started_at, status, current_question, questions_json)
                VALUES (?, ?, 8, 'math', 'algebra', ?, ?, ?, ?)''',
                (str(uuid4()), user_id, datetime.now(UTC).isoformat(), state, 3 if state == 'mastered' else 0,
                 serialize_diagnostic_bank(FRACTION_DIAGNOSTIC)))
        return {'fixture_state': state}

    @app.post('/__qa/mastery/latest/mark-legacy-catalog')
    def mark_latest_mastery_legacy(user_id=Depends(current_user_id), settings=Depends(get_settings)):
        from app.database import connection
        with connection(settings.database_path) as db:
            row = db.execute('''SELECT id FROM mastery_sessions WHERE owner_id = ?
                                ORDER BY started_at DESC, rowid DESC LIMIT 1''', (user_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail='Mastery session not found')
            db.execute("UPDATE mastery_sessions SET catalog_version = 'legacy-qa' WHERE id = ? AND owner_id = ?",
                       (row['id'], user_id))
        return {'session_id': row['id'], 'catalog_version': 'legacy-qa'}

    @app.get('/__qa/learning-path/geometry-count')
    def geometry_count(user_id=Depends(current_user_id), settings=Depends(get_settings)):
        from app.database import connection
        with connection(settings.database_path) as db:
            count = db.execute("SELECT COUNT(*) FROM mastery_sessions WHERE owner_id = ? AND grade = 8 AND subject_id = 'math' AND chapter_id = 'geometry'", (user_id,)).fetchone()[0]
        return {'sessions': count}

    @app.post('/__qa/documents/{document_id}/omit-tail-and-fail-repair-response')
    def arm_repair(document_id: str, user_id=Depends(current_user_id), settings=Depends(get_settings)):
        from app.main import owned_document
        from app.database import connection
        owned_document(document_id, user_id, settings)
        if len(armed) >= 100:
            raise HTTPException(status_code=429, detail='QA fault limit reached')
        with connection(settings.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM documents WHERE id = ? AND owner_id = ?', (document_id, user_id)).fetchone()
            if row is None or row['original_name'] != 'qa-biology.txt':
                raise HTTPException(status_code=409, detail='Requires the disposable QA biology fixture')
            chapters = json.loads(row['chapters_json'])
            last = chapters[-1]
            if last['end_character'] != len(row['extracted_text']) or last['end_character'] - last['start_character'] <= 80:
                raise HTTPException(status_code=409, detail='Fixture already changed or too short')
            last['end_character'] -= 40
            db.execute('UPDATE documents SET chapters_json = ? WHERE id = ? AND owner_id = ?',
                       (json.dumps(chapters), document_id, user_id))
        armed[f'/v1/documents/{document_id}/structure/repair'] = '503'
        return {'armed': True}

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

    @app.post('/__qa/mastery/{session_id}/fail-next-tutor-response')
    def arm_tutor(session_id: str, user_id=Depends(current_user_id), settings=Depends(get_settings)):
        from app.main import owned_mastery_session
        owned_mastery_session(session_id, user_id, settings)
        if len(armed) >= 100:
            raise HTTPException(status_code=429, detail='QA fault limit reached')
        armed[f'/v1/mastery/sessions/{session_id}/tutor-questions'] = '503'
        return {'armed': True}

    @app.middleware('http')
    async def replace_success(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if request.method in {'GET', 'POST', 'PUT'} and response.status_code in {200, 201} and path in armed:
            mode = armed.pop(path)
            if mode == 'malformed':
                payload = json.loads(b''.join([chunk async for chunk in response.body_iterator]))
                replacement = JSONResponse({'state_token': payload['state_token']})
                if request_id := response.headers.get('x-request-id'):
                    replacement.headers['x-request-id'] = request_id
                return replacement
            # Endpoint has committed. Substitute a gateway-like failure instead of
            # delivering the saved outcome. This is not a TCP-disconnect simulation.
            await response.body_iterator.aclose()
            replacement = JSONResponse({'detail': 'Scripted QA response failure after commit'}, status_code=503)
            if request_id := response.headers.get('x-request-id'):
                replacement.headers['x-request-id'] = request_id
            return replacement
        return response
