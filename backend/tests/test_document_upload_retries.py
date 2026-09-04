from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


TEXT = ('Cells are the basic units of life. The nucleus stores genetic information. '
        'Mitochondria release usable energy for cellular work.')


def upload(client, headers, request_id, text=TEXT, name='cells.txt'):
    request_headers = {**headers, 'X-Upload-Request-ID': request_id}
    return client.post('/v1/documents', headers=request_headers, files={'file': (name, text)})


def test_identical_upload_retry_returns_original_without_duplicate(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        request_id = str(uuid4())
        first = upload(client, headers, request_id)
        replay = upload(client, headers, request_id)
        assert first.status_code == replay.status_code == 201
        assert replay.json() == first.json()
        assert len(client.get('/v1/documents', headers=headers).json()) == 1
        assert len(list(get_settings().uploads_dir.iterdir())) == 1
        assert client.delete(f"/v1/documents/{first.json()['id']}", headers=headers).status_code == 204
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM document_upload_requests').fetchone()[0] == 0
        recreated = upload(client, headers, request_id)
        assert recreated.status_code == 201 and recreated.json()['id'] != first.json()['id']
    finally:
        client.__exit__(None, None, None)


def test_upload_request_identity_rejects_changed_content_and_is_owner_scoped(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        request_id = str(uuid4())
        assert upload(client, headers, request_id).status_code == 201
        conflict = upload(client, headers, request_id, TEXT + ' Changed.')
        assert conflict.status_code == 409 and 'different content' in conflict.json()['detail']
        second = client.post('/v1/auth/register', json={
            'email': 'upload-retry-owner@example.com', 'password': 'long-enough-password'}).json()
        other_headers = {'Authorization': f"Bearer {second['access_token']}"}
        assert upload(client, other_headers, request_id, TEXT + ' Other owner.').status_code == 201
        assert len(client.get('/v1/documents', headers=headers).json()) == 1
        assert len(client.get('/v1/documents', headers=other_headers).json()) == 1
    finally:
        client.__exit__(None, None, None)


def test_concurrent_identical_uploads_commit_one_document(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        request_id = str(uuid4())
        with ThreadPoolExecutor(max_workers=2) as workers:
            responses = list(workers.map(lambda _: upload(client, headers, request_id), range(2)))
        assert [response.status_code for response in responses] == [201, 201]
        assert responses[0].json() == responses[1].json()
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM documents').fetchone()[0] == 1
            assert db.execute('SELECT COUNT(*) FROM document_upload_requests').fetchone()[0] == 1
        assert len(list(get_settings().uploads_dir.iterdir())) == 1
    finally:
        client.__exit__(None, None, None)


def test_invalid_upload_request_identity_is_rejected_before_storage(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        response = upload(client, headers, 'not-a-uuid')
        assert response.status_code == 422
        assert client.get('/v1/documents', headers=headers).json() == []
        assert list(get_settings().uploads_dir.iterdir()) == []
    finally:
        client.__exit__(None, None, None)
