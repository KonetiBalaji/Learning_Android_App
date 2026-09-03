"""Durable deletion outbox; never infer deletion targets from a directory scan."""
from pathlib import Path
import sqlite3
import logging

from .config import Settings
from .database import connection


def queue_file_deletion(db: sqlite3.Connection, stored_path: str) -> None:
    # Called inside the same transaction that removes access to the document.
    db.execute('INSERT OR IGNORE INTO pending_file_deletions (stored_path) VALUES (?)', (stored_path,))


def discard_uncommitted_upload(settings: Settings, stored: Path) -> None:
    """Best-effort immediate cleanup, with durable retry if the file is locked."""
    if stored.resolve().parent != settings.uploads_dir.resolve():
        raise ValueError('Upload cleanup target is outside configured storage')
    try:
        with connection(settings.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            # A commit error can have an uncertain outcome; preserve a live record.
            if db.execute('SELECT 1 FROM documents WHERE stored_path = ?', (str(stored),)).fetchone():
                return
            try:
                stored.unlink(missing_ok=True)
            except OSError:
                queue_file_deletion(db, str(stored))
    except sqlite3.Error:
        # Cannot establish whether the file is live: preserve it and alert operators.
        logging.getLogger(__name__).critical('Uncommitted upload cleanup could not be persisted; storage repair is required')


def cleanup_pending_files(settings: Settings, limit: int = 100) -> int:
    removed = 0
    with connection(settings.database_path) as db:
        jobs = db.execute('SELECT stored_path FROM pending_file_deletions ORDER BY attempts, stored_path LIMIT ?', (limit,)).fetchall()
    root = settings.uploads_dir.resolve()
    for job in jobs:
        stored_path = job['stored_path']
        with connection(settings.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM pending_file_deletions WHERE stored_path = ?', (stored_path,)).fetchone():
                continue
            error = None
            try:
                target = Path(stored_path).resolve()
                if target.parent != root:
                    error = 'outside_uploads'
                elif db.execute('SELECT 1 FROM documents WHERE stored_path = ?', (stored_path,)).fetchone():
                    error = 'still_referenced'
                else:
                    target.unlink(missing_ok=True)
            except (OSError, RuntimeError):
                error = 'filesystem_error'
            if error:
                db.execute('UPDATE pending_file_deletions SET attempts = attempts + 1, last_error = ? WHERE stored_path = ?', (error, stored_path))
            else:
                db.execute('DELETE FROM pending_file_deletions WHERE stored_path = ?', (stored_path,))
                removed += 1
    with connection(settings.database_path) as db:
        remaining = db.execute('SELECT COUNT(*) FROM pending_file_deletions').fetchone()[0]
    if remaining:
        logging.getLogger(__name__).warning('Upload cleanup pending: %d job(s)', remaining)
    return removed
