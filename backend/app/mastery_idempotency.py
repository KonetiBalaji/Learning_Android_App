"""Replay completed adaptive mutations from owner-scoped durable records."""
from hashlib import sha256

from fastapi import HTTPException
from pydantic import BaseModel

from .database import connection


def request_fingerprint(request: BaseModel) -> str:
    payload = request.model_dump_json(exclude={'expected_state'}, exclude_none=False)
    return sha256(payload.encode('utf-8')).hexdigest()


def replay(settings, session_id: str, operation: str, expected_state: str | None,
           fingerprint: str, response_type: type[BaseModel]):
    if expected_state is None:
        return None
    with connection(settings.database_path) as db:
        row = db.execute(
            '''SELECT fingerprint, response_json FROM mastery_mutation_results
               WHERE session_id = ? AND operation = ? AND expected_state = ?''',
            (session_id, operation, expected_state),
        ).fetchone()
    if row is None:
        return None
    if row['fingerprint'] != fingerprint:
        raise HTTPException(409, 'That learning step was already submitted with different content')
    return response_type.model_validate_json(row['response_json'])


def save(db, session_id: str, operation: str, expected_state: str | None,
         fingerprint: str, outcome: BaseModel) -> None:
    if expected_state is not None:
        db.execute(
            '''INSERT INTO mastery_mutation_results
               (session_id, operation, expected_state, fingerprint, response_json)
               VALUES (?, ?, ?, ?, ?)''',
            (session_id, operation, expected_state, fingerprint, outcome.model_dump_json()),
        )
