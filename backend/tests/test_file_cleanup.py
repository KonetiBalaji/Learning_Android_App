from pathlib import Path
import asyncio
import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.file_cleanup import cleanup_pending_files, queue_file_deletion
from test_document_answer_retries import make_quiz
from test_mastery_loop import registered_client


def test_periodic_worker_retries_database_failures_and_can_be_cancelled(monkeypatch):
    api = importlib.import_module('app.main')
    pauses = []
    attempts = []
    invitation_attempts = []
    async def fake_sleep(seconds):
        pauses.append(seconds)
        if len(pauses) == 3:
            raise asyncio.CancelledError()
    def cleanup(settings):
        attempts.append(settings)
        if len(attempts) == 1:
            raise sqlite3.OperationalError('synthetic contention')
        return 0
    monkeypatch.setattr(api.asyncio, 'sleep', fake_sleep)
    monkeypatch.setattr(api, 'cleanup_pending_files', cleanup)
    monkeypatch.setattr(api, 'cleanup_invitations', lambda settings: invitation_attempts.append(settings))
    marker = object()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(api.retry_file_cleanup(marker))
    assert pauses == [60, 60, 60]
    assert attempts == [marker, marker]
    assert invitation_attempts == [marker]


@pytest.mark.parametrize('delete_account', [False, True])
def test_failed_unlink_is_durable_and_retried_at_startup(monkeypatch, tmp_path, delete_account):
    client, headers = registered_client(monkeypatch, tmp_path)
    closed = False
    try:
        quiz = make_quiz(client, headers)
        settings = get_settings()
        with connection(settings.database_path) as db:
            doc = db.execute('SELECT documents.* FROM documents JOIN quizzes ON quizzes.document_id = documents.id WHERE quizzes.id = ?', (quiz['id'],)).fetchone()
        target = Path(doc['stored_path'])
        original = Path.unlink
        def locked_file(path, *args, **kwargs):
            if path == target.resolve():
                raise PermissionError('synthetic locked file')
            return original(path, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(Path, 'unlink', locked_file)
            endpoint = '/v1/account' if delete_account else f"/v1/documents/{doc['id']}"
            assert client.delete(endpoint, headers=headers).status_code == 204
        assert target.is_file()
        with connection(settings.database_path) as db:
            job = db.execute('SELECT * FROM pending_file_deletions').fetchone()
            assert job['stored_path'] == str(target)
            assert job['attempts'] == 1 and job['last_error'] == 'filesystem_error'
            assert db.execute('SELECT COUNT(*) FROM documents WHERE id = ?', (doc['id'],)).fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM questions WHERE quiz_id = ?', (quiz['id'],)).fetchone()[0] == 0
        client.__exit__(None, None, None)
        closed = True
        from app.main import app
        with TestClient(app):
            assert not target.exists()
            with connection(settings.database_path) as db:
                assert db.execute('SELECT COUNT(*) FROM pending_file_deletions').fetchone()[0] == 0
    finally:
        if not closed:
            client.__exit__(None, None, None)


def test_cleanup_rejects_outside_targets_and_live_references(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        make_quiz(client, headers)
        settings = get_settings()
        outside = tmp_path / 'not-an-upload.txt'
        outside.write_text('must remain')
        with connection(settings.database_path) as db:
            live = db.execute('SELECT stored_path FROM documents').fetchone()[0]
            queue_file_deletion(db, str(outside))
            queue_file_deletion(db, live)
        assert cleanup_pending_files(settings) == 0
        assert outside.read_text() == 'must remain'
        assert Path(live).is_file()
        with connection(settings.database_path) as db:
            errors = {row['last_error'] for row in db.execute('SELECT last_error FROM pending_file_deletions')}
            assert errors == {'outside_uploads', 'still_referenced'}
    finally:
        client.__exit__(None, None, None)


def test_cleanup_job_rolls_back_with_transaction_and_missing_file_is_success(monkeypatch, tmp_path):
    client, _ = registered_client(monkeypatch, tmp_path)
    try:
        settings = get_settings()
        missing = str(settings.uploads_dir / 'already-removed.txt')
        with pytest.raises(RuntimeError):
            with connection(settings.database_path) as db:
                queue_file_deletion(db, missing)
                raise RuntimeError('rollback')
        with connection(settings.database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM pending_file_deletions').fetchone()[0] == 0
            queue_file_deletion(db, missing)
        assert cleanup_pending_files(settings) == 1
        assert cleanup_pending_files(settings) == 0
    finally:
        client.__exit__(None, None, None)
