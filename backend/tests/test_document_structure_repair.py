import pytest

from app.document_selection import repair_chapter_coverage
from app.schemas import Chapter
from app.config import get_settings
from app.database import connection, json_value
from test_mastery_loop import registered_client


def chapter(identifier, start, end):
    return Chapter(id=identifier, title='Existing title', start_character=start, end_character=end, confidence=0.85)


def test_repair_fills_gaps_preserves_existing_metadata_and_is_repeatable():
    text = 'introAAA middleBBB ending'
    original = [chapter('legacy-7', 5, 8), chapter('legacy-9', 15, 18)]
    result = repair_chapter_coverage(text, original)
    assert ''.join(text[c.start_character:c.end_character] for c in result) == text
    assert [c for c in result if c.id.startswith('legacy')] == original
    assert repair_chapter_coverage(text, result) == result


@pytest.mark.parametrize('chapters', [[chapter('a', 0, 5), chapter('b', 4, 8)],
    [chapter('a', -1, 5)], [chapter('a', 0, 30)], [chapter('a', 0, 3), chapter('a', 4, 8)]])
def test_unsafe_existing_ranges_are_not_rewritten(chapters):
    with pytest.raises(ValueError):
        repair_chapter_coverage('0123456789', chapters)


def test_empty_structure_and_id_collisions_are_handled():
    assert repair_chapter_coverage('abc', [chapter('recovered-0-1', 1, 3)])[0].id == 'recovered-0-1-gap'
    assert repair_chapter_coverage('abc', [])[0].end_character == 3
    assert repair_chapter_coverage('   ', []) == []


def test_owner_repair_preserves_existing_quiz_and_stored_chapter(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        prefix = 'Omitted introductory fact.\n'
        body = ' '.join(f'Example {i}: plants convert sunlight into stored chemical energy through photosynthesis.' for i in range(5))
        text = prefix + body
        doc = client.post('/v1/documents', headers=headers, files={'file': ('old.txt', text)}).json()
        old = chapter('legacy-1', len(prefix), len(text))
        with connection(get_settings().database_path) as db:
            db.execute('UPDATE documents SET chapters_json = ? WHERE id = ?', (json_value([old.model_dump()]), doc['id']))
        quiz = client.post(f"/v1/documents/{doc['id']}/quizzes", headers=headers,
                           json={'chapter_ids': [old.id], 'question_count': 5}).json()
        with connection(get_settings().database_path) as db:
            before = [dict(row) for row in db.execute('SELECT * FROM questions WHERE quiz_id = ?', (quiz['id'],))]
        token = client.post('/v1/auth/register', json={'email': 'other-repair@example.com', 'password': 'long-enough-password'}).json()['access_token']
        path = f"/v1/documents/{doc['id']}/structure/repair"
        assert client.post(path, headers={'Authorization': f'Bearer {token}'}).status_code == 404
        fixed = client.post(path, headers=headers)
        assert fixed.status_code == 200
        assert fixed.json()['chapters'][1] == old.model_dump()
        assert client.post(path, headers=headers).json() == fixed.json()
        with connection(get_settings().database_path) as db:
            assert [dict(row) for row in db.execute('SELECT * FROM questions WHERE quiz_id = ?', (quiz['id'],))] == before
        assert client.get(f"/v1/quizzes/{quiz['id']}", headers=headers).status_code == 200
        unsafe = json_value([chapter('overlap-a', 0, 40).model_dump(), chapter('overlap-b', 20, 60).model_dump()])
        with connection(get_settings().database_path) as db:
            db.execute('UPDATE documents SET chapters_json = ? WHERE id = ?', (unsafe, doc['id']))
        assert client.post(path, headers=headers).status_code == 422
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT chapters_json FROM documents WHERE id = ?', (doc['id'],)).fetchone()[0] == unsafe
    finally:
        client.__exit__(None, None, None)
