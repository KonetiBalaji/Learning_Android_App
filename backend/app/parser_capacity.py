"""Fail-fast parser admission shared by threads and API worker processes."""

import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class ParserCapacityError(RuntimeError):
    pass


_pool_guard = threading.Lock()
_pools: dict[int, threading.BoundedSemaphore] = {}


def _pool(limit: int) -> threading.BoundedSemaphore:
    if not 1 <= limit <= 16:
        raise ValueError('Concurrent parser limit must be between 1 and 16')
    with _pool_guard:
        return _pools.setdefault(limit, threading.BoundedSemaphore(limit))


def _acquire_shared_slot(database_path: Path, limit: int, lease_seconds: int) -> str:
    token = str(uuid.uuid4())
    now = time.time()
    try:
        with sqlite3.connect(database_path, timeout=2) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM document_parser_leases WHERE expires_at <= ?', (now,))
            active = db.execute('SELECT COUNT(*) FROM document_parser_leases').fetchone()[0]
            if active >= limit:
                raise ParserCapacityError('Document parser capacity is currently full')
            db.execute('INSERT INTO document_parser_leases (token, expires_at) VALUES (?, ?)',
                       (token, now + lease_seconds))
        return token
    except ParserCapacityError:
        raise
    except sqlite3.Error as error:
        raise ParserCapacityError('Document parser admission is unavailable') from error


def _release_shared_slot(database_path: Path, token: str) -> None:
    try:
        with sqlite3.connect(database_path, timeout=2) as db:
            db.execute('DELETE FROM document_parser_leases WHERE token = ?', (token,))
    except sqlite3.Error:
        # The finite lease is the crash/failure fallback. Never mask the parser
        # result because release will be retried implicitly after expiry.
        pass


@contextmanager
def parser_slot(limit: int, database_path: Path | None = None, lease_seconds: int = 130):
    if not 1 <= lease_seconds <= 300:
        raise ValueError('Parser lease must be between 1 and 300 seconds')
    pool = _pool(limit)
    if not pool.acquire(blocking=False):
        raise ParserCapacityError('Document parser capacity is currently full')
    token = None
    try:
        if database_path is not None:
            token = _acquire_shared_slot(database_path, limit, lease_seconds)
        yield
    finally:
        if token is not None:
            _release_shared_slot(database_path, token)
        pool.release()
