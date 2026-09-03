from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


def test_chunked_document_and_unfinished_multipart_have_safe_storage_results(monkeypatch, tmp_path):
    client, auth = registered_client(monkeypatch, tmp_path)
    try:
        prefix = b'--qa-boundary\r\nContent-Disposition: form-data; name="file"; filename="notes.txt"\r\nContent-Type: text/plain\r\n\r\n'
        material = b'Chapter 1 Biology\nCells are basic units of life. Cell membranes regulate entry and exit. Plants use photosynthesis to store energy.'
        headers = dict(auth, **{'Content-Type': 'multipart/form-data; boundary=qa-boundary'})
        incomplete = client.post('/v1/documents', headers=headers, content=iter([prefix, material]))
        assert incomplete.status_code == 422
        settings = get_settings()
        assert list(settings.uploads_dir.iterdir()) == []
        with connection(settings.database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM documents').fetchone()[0] == 0
        complete = client.post('/v1/documents', headers=headers,
                               content=iter([prefix, material[:40], material[40:], b'\r\n--qa-boundary--\r\n']))
        assert complete.status_code == 201
        assert complete.json()['original_name'] == 'notes.txt'
        assert len(list(settings.uploads_dir.iterdir())) == 1
    finally:
        client.__exit__(None, None, None)
