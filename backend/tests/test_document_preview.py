import pytest

from app.document_preview import preview_chapter
from app.schemas import Chapter
from test_mastery_loop import registered_client


def test_preview_pages_reconstruct_exact_unicode_source_without_adjacent_text():
    source = '🙂é\n' * 1500
    text = 'PRIVATE PREFIX' + source + 'PRIVATE SUFFIX'
    chapter = Chapter(id='target', title='Target', start_character=14, end_character=14 + len(source), confidence=.35)
    pages = [preview_chapter('doc', text, [chapter], 'target', page) for page in range(3)]
    assert ''.join(page.text for page in pages) == source
    assert [len(page.text) for page in pages] == [2000, 2000, 500]
    assert all(page.total_pages == 3 for page in pages)
    for page in pages:
        assert text[page.start_character:page.end_character] == page.text
    for page in [-1, 3, 1000000]:
        with pytest.raises(ValueError):
            preview_chapter('doc', text, [chapter], 'target', page)
    with pytest.raises(ValueError):
        preview_chapter('doc', text, [chapter.model_copy(update={'end_character': len(text) + 1})], 'target', 0)


def test_preview_endpoint_owner_pagination_and_deletion(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        source = 'Chapter 1 Reading\n' + 'Read the exact source before selecting it. ' * 120
        doc = client.post('/v1/documents', headers=headers, files={'file': ('preview.txt', source)}).json()
        path = f"/v1/documents/{doc['id']}/chapters/{doc['chapters'][0]['id']}/preview"
        first = client.get(path, headers=headers)
        assert first.status_code == 200
        assert len(first.json()['text']) == 2000
        pages = [client.get(path, params={'page': p}, headers=headers).json() for p in range(first.json()['total_pages'])]
        assert ''.join(p['text'] for p in pages) == source
        assert client.get(path, params={'page': -1}, headers=headers).status_code == 422
        assert client.get(path, params={'page': first.json()['total_pages']}, headers=headers).status_code == 422
        assert client.get(path).status_code == 401
        token = client.post('/v1/auth/register', json={'email': 'preview-other@example.com', 'password': 'long-enough-password'}).json()['access_token']
        assert client.get(path, headers={'Authorization': f'Bearer {token}'}).status_code == 404
        assert client.get(f"/v1/documents/{doc['id']}/chapters/missing/preview", headers=headers).status_code == 404
        assert client.delete(f"/v1/documents/{doc['id']}", headers=headers).status_code == 204
        assert client.get(path, headers=headers).status_code == 404
    finally:
        client.__exit__(None, None, None)
