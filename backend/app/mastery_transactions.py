"""Validate a computed transition against its original snapshot under a write lock."""
from fastapi import HTTPException


def mastery_state_token(snapshot, **changes) -> str:
    values = dict(snapshot)
    values.update(changes)
    return ':'.join(str(values[field]) for field in
                    ('id', 'status', 'current_question', 'correct_answers', 'coaching_rounds'))


def check_expected_state(snapshot, expected_state: str) -> None:
    if expected_state != mastery_state_token(snapshot):
        raise HTTPException(status_code=409, detail='Learning state changed. Resume the session before submitting again.')


def lock_mastery_snapshot(db, snapshot) -> None:
    # Provider work is performed before this short transaction, never under the lock.
    db.execute('BEGIN IMMEDIATE')
    current = db.execute('SELECT * FROM mastery_sessions WHERE id = ? AND owner_id = ?',
                         (snapshot['id'], snapshot['owner_id'])).fetchone()
    fields = ('status', 'current_question', 'correct_answers', 'coaching_rounds')
    if current is None or any(current[field] != snapshot[field] for field in fields):
        raise HTTPException(status_code=409, detail='Learning state changed. Resume the session before submitting again.')
