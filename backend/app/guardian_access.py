from __future__ import annotations

import hashlib
import secrets
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .config import Settings
from .database import connection


INVITATION_MINUTES = 15


class GuardianInvitation(BaseModel):
    code: str
    expires_at: str


class GuardianInvitationRedemption(BaseModel):
    code: str = Field(min_length=20, max_length=128)


class LinkedAccount(BaseModel):
    id: str
    email: str
    linked_at: str


def _digest(code: str) -> str:
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def cleanup_invitations(settings: Settings, current_time: datetime | None = None) -> int:
    cutoff = (current_time or datetime.now(UTC)) - timedelta(days=settings.guardian_invitation_retention_days)
    with connection(settings.database_path) as db:
        return db.execute('DELETE FROM guardian_invitations WHERE expires_at < ?',
                          (cutoff.isoformat(),)).rowcount


def create_invitation(learner_id: str, settings: Settings) -> GuardianInvitation:
    created = datetime.now(UTC)
    expires = created + timedelta(minutes=INVITATION_MINUTES)
    # 128 bits of entropy while remaining easy to type on Android keyboards.
    code = secrets.token_hex(16)
    with connection(settings.database_path) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM guardian_invitations WHERE learner_id = ? AND redeemed_at IS NULL',
                   (learner_id,))
        db.execute(
            '''INSERT INTO guardian_invitations
               (id, learner_id, code_digest, expires_at, created_at, redeemed_at)
               VALUES (?, ?, ?, ?, ?, NULL)''',
            (str(uuid.uuid4()), learner_id, _digest(code), expires.isoformat(), created.isoformat()),
        )
    return GuardianInvitation(code=code, expires_at=expires.isoformat())


def redeem_invitation(guardian_id: str, code: str, settings: Settings) -> LinkedAccount:
    now = datetime.now(UTC)
    try:
        with connection(settings.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            invitation = db.execute(
                '''SELECT guardian_invitations.*, users.email FROM guardian_invitations
                   JOIN users ON users.id = guardian_invitations.learner_id
                   WHERE code_digest = ?''', (_digest(code),),
            ).fetchone()
            if (invitation is None or invitation['redeemed_at'] is not None or
                    datetime.fromisoformat(invitation['expires_at']) <= now):
                raise HTTPException(status_code=404, detail='Invitation is invalid or expired')
            if invitation['learner_id'] == guardian_id:
                raise HTTPException(status_code=422, detail='A learner cannot link their own account')
            linked_at = now.isoformat()
            db.execute(
                'INSERT INTO guardian_links (guardian_id, learner_id, created_at) VALUES (?, ?, ?)',
                (guardian_id, invitation['learner_id'], linked_at),
            )
            db.execute('UPDATE guardian_invitations SET redeemed_at = ? WHERE id = ?',
                       (linked_at, invitation['id']))
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail='This learner is already linked') from error
    return LinkedAccount(id=invitation['learner_id'], email=invitation['email'], linked_at=linked_at)


def linked_learners(guardian_id: str, settings: Settings) -> list[LinkedAccount]:
    with connection(settings.database_path) as db:
        rows = db.execute(
            '''SELECT users.id, users.email, guardian_links.created_at FROM guardian_links
               JOIN users ON users.id = guardian_links.learner_id
               WHERE guardian_links.guardian_id = ? ORDER BY guardian_links.created_at, users.id''',
            (guardian_id,),
        ).fetchall()
    return [LinkedAccount(id=row['id'], email=row['email'], linked_at=row['created_at']) for row in rows]


def linked_guardians(learner_id: str, settings: Settings) -> list[LinkedAccount]:
    with connection(settings.database_path) as db:
        rows = db.execute(
            '''SELECT users.id, users.email, guardian_links.created_at FROM guardian_links
               JOIN users ON users.id = guardian_links.guardian_id
               WHERE guardian_links.learner_id = ? ORDER BY guardian_links.created_at, users.id''',
            (learner_id,),
        ).fetchall()
    return [LinkedAccount(id=row['id'], email=row['email'], linked_at=row['created_at']) for row in rows]


def require_link(guardian_id: str, learner_id: str, settings: Settings) -> None:
    with connection(settings.database_path) as db:
        linked = db.execute(
            'SELECT 1 FROM guardian_links WHERE guardian_id = ? AND learner_id = ?',
            (guardian_id, learner_id),
        ).fetchone()
    if linked is None:
        raise HTTPException(status_code=404, detail='Linked learner not found')


def revoke_by_guardian(guardian_id: str, learner_id: str, settings: Settings) -> None:
    _delete_link(guardian_id, learner_id, settings)


def revoke_by_learner(learner_id: str, guardian_id: str, settings: Settings) -> None:
    _delete_link(guardian_id, learner_id, settings)


def _delete_link(guardian_id: str, learner_id: str, settings: Settings) -> None:
    with connection(settings.database_path) as db:
        deleted = db.execute(
            'DELETE FROM guardian_links WHERE guardian_id = ? AND learner_id = ?',
            (guardian_id, learner_id),
        ).rowcount
    if not deleted:
        raise HTTPException(status_code=404, detail='Linked account not found')
