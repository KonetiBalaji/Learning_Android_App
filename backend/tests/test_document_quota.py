from concurrent.futures import ThreadPoolExecutor
import sqlite3

from app.config import get_settings
from app.database import connection, initialize
from test_mastery_loop import registered_client


TEXT = ('Cells are the basic units of life. The nucleus stores genetic information. '
        'Mitochondria release usable energy, and ribosomes support protein synthesis.')


def configure_quota(monkeypatch, count='1', upload_bytes='300', total_bytes='300'):
    monkeypatch.setenv('LEARNING_MAX_DOCUMENTS_PER_OWNER', count)
    monkeypatch.setenv('LEARNING_MAX_UPLOAD_BYTES', upload_bytes)
    monkeypatch.setenv('LEARNING_MAX_DOCUMENT_BYTES_PER_OWNER', total_bytes)


def upload(client, headers, name='cells.txt'):
    return client.post('/v1/documents', headers=headers, files={'file': (name, TEXT)})


def test_count_quota_rejects_safely_and_deletion_releases_slot(monkeypatch, tmp_path):
    configure_quota(monkeypatch)
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        first = upload(client, headers)
        assert first.status_code == 201
        rejected = upload(client, headers, 'second.txt')
        assert rejected.status_code == 422
        assert rejected.headers['X-Learning-Error'] == 'document_count_limit'
        assert client.delete(f"/v1/documents/{first.json()['id']}", headers=headers).status_code == 204
        assert upload(client, headers, 'replacement.txt').status_code == 201
        assert len(list(get_settings().uploads_dir.iterdir())) == 1
    finally:
        client.__exit__(None, None, None)


def test_byte_quota_is_owner_scoped(monkeypatch, tmp_path):
    configure_quota(monkeypatch, count='10', upload_bytes='200', total_bytes='200')
    client, first_headers = registered_client(monkeypatch, tmp_path)
    try:
        assert upload(client, first_headers).status_code == 201
        rejected = upload(client, first_headers, 'second.txt')
        assert rejected.status_code == 422
        assert rejected.headers['X-Learning-Error'] == 'document_bytes_limit'
        second = client.post('/v1/auth/register', json={
            'email': 'quota-second@example.com', 'password': 'long-enough-password'}).json()
        second_headers = {'Authorization': f"Bearer {second['access_token']}"}
        assert upload(client, second_headers, 'other-owner.txt').status_code == 201
        with connection(get_settings().database_path) as db:
            sizes = [row['stored_bytes'] for row in db.execute('SELECT stored_bytes FROM documents').fetchall()]
        assert sizes == [len(TEXT.encode()), len(TEXT.encode())]
    finally:
        client.__exit__(None, None, None)


def test_parallel_uploads_cannot_overshoot_one_owner_slot(monkeypatch, tmp_path):
    configure_quota(monkeypatch)
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda name: upload(client, headers, name), ('one.txt', 'two.txt')))
        assert sorted(response.status_code for response in results) == [201, 422]
        rejected = next(response for response in results if response.status_code == 422)
        assert rejected.headers['X-Learning-Error'] == 'document_count_limit'
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM documents').fetchone()[0] == 1
        assert len(list(get_settings().uploads_dir.iterdir())) == 1
    finally:
        client.__exit__(None, None, None)


def test_schema_migration_backfills_existing_file_size(tmp_path):
    database = tmp_path / 'legacy.sqlite3'
    stored = tmp_path / 'legacy.txt'
    stored.write_bytes(b'legacy material bytes')
    with sqlite3.connect(database) as db:
        db.execute('''CREATE TABLE users (
            id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL)''')
        db.execute('''CREATE TABLE documents (
            id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            original_name TEXT NOT NULL, media_type TEXT NOT NULL, stored_path TEXT NOT NULL,
            extracted_text TEXT NOT NULL, chapters_json TEXT NOT NULL, created_at TEXT NOT NULL)''')
        db.execute("INSERT INTO users VALUES ('owner', 'legacy@example.com', 'hash', 'now')")
        db.execute("INSERT INTO documents VALUES ('doc', 'owner', 'legacy.txt', 'text/plain', ?, 'text', '[]', 'now')",
                   (str(stored),))
    initialize(database)
    with connection(database) as db:
        assert db.execute("SELECT stored_bytes FROM documents WHERE id = 'doc'").fetchone()[0] == stored.stat().st_size
