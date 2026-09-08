"""Google ID token exchange. No email-based account linking or password fallback."""
from datetime import UTC, datetime
import hashlib
import hmac
import logging
import secrets
import sqlite3
import time
import uuid

from fastapi import Depends, HTTPException
from google.auth import exceptions
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter
import requests

from .config import Settings, get_settings
from .database import connection
from .schemas import Token
from .security import create_token


class GoogleCredentials(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id_token: str = Field(min_length=1, max_length=16384, repr=False)
    nonce: str = Field(min_length=43, max_length=128, pattern=r'^[A-Za-z0-9_-]+$', repr=False)


class GoogleChallenge(BaseModel):
    nonce: str = Field(min_length=43, max_length=128)
    expires_in_seconds: int = 300


MAX_GOOGLE_CHALLENGES = 10_000
GOOGLE_CHALLENGE_SECONDS = 300
logger = logging.getLogger(__name__)


def google_validation_reason(error: Exception) -> str:
    """Return a privacy-safe rejection category; never log token data or claims."""
    message = str(error).lower()
    if 'audience' in message:
        return 'audience'
    if 'expired' in message:
        return 'expired'
    if 'too early' in message or 'issued in the future' in message:
        return 'issued_at'
    if 'issuer' in message:
        return 'issuer'
    if 'certificate' in message or 'signature' in message or 'key id' in message:
        return 'signature'
    if 'nonce' in message:
        return 'nonce'
    if 'subject' in message:
        return 'subject'
    if 'email' in message:
        return 'email'
    return type(error).__name__


def nonce_digest(nonce: str) -> str:
    return hashlib.sha256(nonce.encode('ascii')).hexdigest()


def google_challenge(settings: Settings = Depends(get_settings)) -> GoogleChallenge:
    if not settings.google_client_id:
        raise HTTPException(503, 'Google sign-in is not configured')
    nonce = secrets.token_urlsafe(32)
    timestamp = time.time()
    try:
        with connection(settings.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM google_login_challenges WHERE expires_at <= ?', (timestamp,))
            if db.execute('SELECT COUNT(*) FROM google_login_challenges').fetchone()[0] >= MAX_GOOGLE_CHALLENGES:
                raise HTTPException(503, 'Google sign-in is temporarily unavailable')
            db.execute('INSERT INTO google_login_challenges VALUES (?, ?)',
                       (nonce_digest(nonce), timestamp + GOOGLE_CHALLENGE_SECONDS))
    except sqlite3.Error as error:
        raise HTTPException(503, 'Google sign-in is temporarily unavailable') from error
    return GoogleChallenge(nonce=nonce)


def verified_google_identity(token: str, audience: str, expected_nonce: str) -> tuple[str, str]:
    # Per-call session is closed; bound certificate fetch rather than default 120s.
    with requests.Session() as session:
        transport = Request(session=session)
        def fetch(*args, **kwargs):
            kwargs['timeout'] = 5
            return transport(*args, **kwargs)
        claims = id_token.verify_oauth2_token(token, fetch, audience=audience)
    # Defense in depth for required claims, including mocked/provider regressions.
    if claims.get('iss') not in {'accounts.google.com', 'https://accounts.google.com'} or claims.get('aud') != audience:
        raise ValueError('Invalid issuer or audience')
    claimed_nonce = claims.get('nonce')
    if not isinstance(claimed_nonce, str) or not hmac.compare_digest(claimed_nonce, expected_nonce):
        raise ValueError('Invalid nonce')
    subject = claims.get('sub')
    if not isinstance(subject, str) or not 1 <= len(subject) <= 255 or any(ord(c) < 33 for c in subject):
        raise ValueError('Invalid subject')
    if claims.get('email_verified') is not True or not isinstance(claims.get('email'), str):
        raise ValueError('Verified email required')
    email = str(TypeAdapter(EmailStr).validate_python(claims['email'])).lower()
    return subject, email


def google_login(credentials: GoogleCredentials, settings: Settings = Depends(get_settings)) -> Token:
    if not settings.google_client_id:
        raise HTTPException(503, 'Google sign-in is not configured')
    try:
        subject, email = verified_google_identity(
            credentials.id_token, settings.google_client_id, credentials.nonce)
    except exceptions.TransportError as error:
        raise HTTPException(503, 'Google sign-in is temporarily unavailable') from error
    except (ValueError, TypeError, KeyError, exceptions.GoogleAuthError) as error:
        logger.warning('Google identity token rejected: %s', google_validation_reason(error))
        raise HTTPException(401, 'Invalid Google sign-in token') from error
    try:
        with connection(settings.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            digest = nonce_digest(credentials.nonce)
            challenge = db.execute(
                'SELECT expires_at FROM google_login_challenges WHERE nonce_hash = ?',
                (digest,),
            ).fetchone()
            db.execute('DELETE FROM google_login_challenges WHERE nonce_hash = ?', (digest,))
        if challenge is None or challenge['expires_at'] <= time.time():
            raise HTTPException(401, 'Invalid Google sign-in token')
        with connection(settings.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            account = db.execute('SELECT user_id FROM google_accounts WHERE subject = ?', (subject,)).fetchone()
            if account:
                user_id = account['user_id']
            else:
                # Never grant access to an existing account based on matching email.
                if db.execute('SELECT 1 FROM users WHERE email = ?', (email,)).fetchone():
                    raise HTTPException(409, 'Use the existing account sign-in method; automatic linking is disabled')
                user_id = str(uuid.uuid4())
                db.execute('INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
                           (user_id, email, 'google_only$$', datetime.now(UTC).isoformat()))
                db.execute('INSERT INTO google_accounts (subject, user_id) VALUES (?, ?)', (subject, user_id))
    except sqlite3.IntegrityError as error:
        raise HTTPException(409, 'Could not create Google account; sign in again') from error
    return Token(access_token=create_token(user_id, settings))
