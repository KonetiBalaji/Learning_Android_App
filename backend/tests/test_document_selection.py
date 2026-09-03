import pytest

from app.document_selection import resolve_chapters
from app.schemas import Chapter


def chapter(identifier, start, end):
    return Chapter(id=identifier, title=identifier, start_character=start, end_character=end, confidence=1)


@pytest.mark.parametrize('ids', [[], ['a', 'missing'], ['a', 'a']])
def test_rejects_incomplete_or_duplicate_selection(ids):
    with pytest.raises(ValueError):
        resolve_chapters('abcdefghij', [chapter('a', 0, 5), chapter('b', 5, 10)], ids)


def test_multiple_chapters_resolve_in_source_order_without_unselected_text():
    chapters = [chapter('a', 0, 3), chapter('b', 3, 6), chapter('c', 6, 9)]
    selected = resolve_chapters('AAABBBCCC', chapters, ['c', 'a'])
    assert [item.id for item in selected] == ['a', 'c']
    assert ['AAABBBCCC'[item.start_character:item.end_character] for item in selected] == ['AAA', 'CCC']
    assert resolve_chapters('AAABBBCCC', chapters, ['a', 'b', 'c']) == chapters


@pytest.mark.parametrize('chapters', [
    [chapter('a', -1, 3)], [chapter('a', 0, 11)], [chapter('a', 3, 3)],
    [chapter('a', 0, 5), chapter('b', 4, 8)],
    [chapter('a', 5, 8), chapter('b', 0, 3)],
    [chapter('a', 0, 3), chapter('a', 3, 6)],
])
def test_rejects_ambiguous_or_invalid_source_ranges(chapters):
    with pytest.raises(ValueError):
        resolve_chapters('abcdefghij', chapters, list(dict.fromkeys(item.id for item in chapters)))


def test_both_generators_reject_partial_selection_before_generation():
    from app.quiz_service import generate_grounded_questions
    from app.document_question_provider import generate_document_questions
    chapters = [chapter('a', 0, 10)]
    with pytest.raises(ValueError, match='valid chapters'):
        generate_grounded_questions('abcdefghij', chapters, ['a', 'missing'], 5)
    # No settings or API client is needed: rejection must precede provider access.
    with pytest.raises(ValueError, match='valid chapters'):
        generate_document_questions('abcdefghij', chapters, ['a', 'missing'], 5, None)


def test_invalid_selection_returns_422_without_saving_quiz(monkeypatch, tmp_path):
    from test_mastery_loop import registered_client
    from app.config import get_settings
    from app.database import connection
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        text = 'Cells are the basic units of living organisms. ' * 8
        upload = client.post('/v1/documents', headers=headers, files={'file': ('selection.txt', text)})
        assert upload.status_code == 201
        document = upload.json()
        selected = document['chapters'][0]['id']
        for ids in ([selected, 'missing'], [selected, selected]):
            response = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
                json={'chapter_ids': ids, 'question_count': 5})
            assert response.status_code == 422
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM questions').fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)
