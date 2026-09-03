"""Bounded, shared-database admission control; not account lockout or a DDoS shield."""
from __future__ import annotations

import hashlib
import hmac
import math
import sqlite3
import time

from fastapi import Depends, HTTPException, Request

from .config import Settings, get_settings
from .database import connection

MAX_CLIENT_WINDOWS = 10_000


def consume_auth_attempt(settings: Settings, client: str, timestamp: float | None = None) -> int:
    """Return retry seconds (zero admits). Counts successes too; denials do not extend windows."""
    now = time.time() if timestamp is None else timestamp
    digest = hmac.new(settings.jwt_secret.encode(), b"auth-admission-v1\0" + client.encode(), hashlib.sha256).hexdigest()
    with connection(settings.database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM auth_attempt_windows WHERE expires_at <= ?", (now,))
        row = db.execute("SELECT expires_at, attempts FROM auth_attempt_windows WHERE client_digest = ?", (digest,)).fetchone()
        if row is not None:
            if row['attempts'] >= settings.auth_attempts_per_window:
                return max(1, math.ceil(row['expires_at'] - now))
            db.execute("UPDATE auth_attempt_windows SET attempts = attempts + 1 WHERE client_digest = ?", (digest,))
        else:
            if db.execute("SELECT COUNT(*) FROM auth_attempt_windows").fetchone()[0] >= MAX_CLIENT_WINDOWS:
                raise HTTPException(503, "Authentication is temporarily unavailable", headers={"Retry-After": "5"})
            db.execute("INSERT INTO auth_attempt_windows VALUES (?, ?, 1)", (digest, now + settings.auth_window_seconds))
    return 0


def limit_authentication(request: Request, settings: Settings = Depends(get_settings)) -> None:
    # Trust only the ASGI peer, never arbitrary Forwarded/X-Forwarded-For headers.
    # A trusted reverse proxy may already have rewritten this peer at the server layer.
    client = request.client.host if request.client else "unknown-peer"
    try:
        retry = consume_auth_attempt(settings, client)
    except sqlite3.Error:
        raise HTTPException(503, "Authentication is temporarily unavailable", headers={"Retry-After": "5"}) from None
    if retry:
        raise HTTPException(429, "Too many authentication attempts. Please wait and try again.", headers={"Retry-After": str(retry)})
