import sqlite3

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.database import initialize
from app.main import ready
from app.runtime_readiness import verify_runtime_readiness


def configured(tmp_path):
    settings = Settings(runtime_dir=tmp_path, jwt_secret='test-secret')
    settings.uploads_dir.mkdir()
    initialize(settings.database_path)
    return settings


def test_readiness_proves_database_schema_write_lock_and_upload_write(tmp_path):
    settings = configured(tmp_path)
    assert verify_runtime_readiness(settings) == ('database', 'upload_storage')
    assert list(settings.uploads_dir.iterdir()) == []
    assert ready(settings) == {'status': 'ready', 'environment': 'development',
                               'revision': 'development',
                               'checks': ['database', 'upload_storage']}


def test_readiness_fails_closed_for_incomplete_schema(monkeypatch, tmp_path):
    settings = configured(tmp_path)
    with sqlite3.connect(settings.database_path) as db:
        db.execute('DROP TABLE document_parser_leases')
    with pytest.raises(sqlite3.DatabaseError, match='schema'):
        verify_runtime_readiness(settings)

    monkeypatch.setattr('app.main.verify_runtime_readiness',
                        lambda _: (_ for _ in ()).throw(OSError('private storage path')))
    with pytest.raises(HTTPException) as raised:
        ready(settings)
    assert raised.value.status_code == 503
    assert raised.value.detail == 'Runtime storage is not ready'
    assert 'private storage path' not in raised.value.detail
