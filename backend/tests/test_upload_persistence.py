from contextlib import contextmanager
import importlib
from pathlib import Path
import sqlite3

import pytest

from app.config import get_settings
from app.database import connection
from app.file_cleanup import cleanup_pending_files, discard_uncommitted_upload
from test_mastery_loop import registered_client

TEXT = 'Cells are the basic units of life in living organisms. Mitochondria release usable energy for cellular work. Ribosomes support protein synthesis inside cells.'


@pytest.mark.parametrize('locked', [False, True])
def test_failed_commit_cleans_upload_or_queues_locked_file(monkeypatch, tmp_path, locked):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        api = importlib.import_module('app.main')
        settings = get_settings()
        @contextmanager
        def failed_commit(path):
            with connection(path) as db:
                yield db
                raise sqlite3.OperationalError('synthetic private database detail')
        original_unlink = Path.unlink
        def locked_unlink(path, *args, **kwargs):
            if path.parent == settings.uploads_dir:
                raise PermissionError('synthetic private file detail')
            return original_unlink(path, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(api, 'connection', failed_commit)
            if locked:
                patch.setattr(Path, 'unlink', locked_unlink)
            response = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', TEXT)})
        assert response.status_code == 503
        assert 'synthetic' not in response.text and 'private' not in response.text
        with connection(settings.database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM documents').fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM pending_file_deletions').fetchone()[0] == int(locked)
        assert len(list(settings.uploads_dir.iterdir())) == int(locked)
        cleanup_pending_files(settings)
        assert list(settings.uploads_dir.iterdir()) == []
    finally:
        client.__exit__(None, None, None)


def test_partial_write_is_removed_and_invalid_content_is_never_written(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        settings = get_settings()
        writes = []
        original = Path.write_bytes
        def partial_write(path, data):
            writes.append(path)
            original(path, data[:3])
            raise OSError('synthetic full disk')
        with monkeypatch.context() as patch:
            patch.setattr(Path, 'write_bytes', partial_write)
            assert client.post('/v1/documents', headers=headers, files={'file': ('tiny.txt', 'short')}).status_code == 422
            assert writes == []
            response = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', TEXT)})
            assert response.status_code == 503 and 'full disk' not in response.text
        assert len(writes) == 1
        assert list(settings.uploads_dir.iterdir()) == []
    finally:
        client.__exit__(None, None, None)


def test_uncertain_commit_cleanup_preserves_referenced_upload(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        response = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', TEXT)})
        assert response.status_code == 201
        settings = get_settings()
        with connection(settings.database_path) as db:
            stored = Path(db.execute('SELECT stored_path FROM documents').fetchone()[0])
        discard_uncommitted_upload(settings, stored)
        assert stored.is_file()
        assert client.get(f"/v1/documents/{response.json()['id']}", headers=headers).status_code == 200
    finally:
        client.__exit__(None, None, None)
