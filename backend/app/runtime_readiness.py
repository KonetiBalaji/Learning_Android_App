"""Production readiness checks for the durable database and upload volume."""

import os
import sqlite3
import uuid

from .config import Settings


REQUIRED_TABLES = frozenset({'users', 'documents', 'document_parser_leases'})


def verify_runtime_readiness(settings: Settings) -> tuple[str, ...]:
    with sqlite3.connect(settings.database_path, timeout=2) as db:
        tables = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not REQUIRED_TABLES <= tables:
            raise sqlite3.DatabaseError('Required runtime schema is incomplete')
        if db.execute('PRAGMA quick_check(1)').fetchone() != ('ok',):
            raise sqlite3.DatabaseError('Runtime database integrity check failed')
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE document_parser_leases SET expires_at = expires_at WHERE 0')
        db.rollback()

    probe = settings.uploads_dir / f'.readiness-{uuid.uuid4()}.tmp'
    try:
        with probe.open('xb') as stream:
            stream.write(b'ready')
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        probe.unlink(missing_ok=True)
    return ('database', 'upload_storage')
