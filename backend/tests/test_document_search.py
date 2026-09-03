import pytest

from app.config import get_settings
from app.database import connection
from app.document_search import search_source
from app.document_selection import resolve_quiz_selection
from app.schemas import Chapter, SourceRange
from test_mastery_loop import registered_client


def chapter(identifier, start, end):
    return Chapter(id=identifier, title=identifier, start_character=start, end_character=end, confidence=.8)


def test_literal_unicode_matching_uses_absolute_source_offsets_and_selected_chapters():
    text = '😀 CELL source.\nAnother cell fact.\nHIDDEN CELL secret.'
    boundary = text.index('HIDDEN')
    chapters = [chapter('allowed', 0, boundary), chapter('hidden', boundary, len(text))]
    result = search_source('doc', text, chapters, ['allowed'], 'cell')
    assert len(result.matches) == 2
    assert result.match_mode == 'literal_case_insensitive' and result.has_more is False
    for hit in result.matches:
        assert hit.text == text[hit.start_character:hit.end_character]
        assert text[hit.match_start:hit.match_end].lower() == 'cell'
        assert 0 <= hit.start_character <= hit.match_start < hit.match_end <= hit.end_character <= boundary
        assert 'HIDDEN' not in hit.text
    assert result.matches[0].match_start == 2  # Emoji is one Unicode code point.


def test_regex_characters_are_literal_and_zero_results_do_not_fallback():
    text = 'A .* literal pattern and a different phrase.'
    chapters = [chapter('a', 0, len(text))]
    assert len(search_source('doc', text, chapters, ['a'], '.*').matches) == 1
    result = search_source('doc', text, chapters, ['a'], 'nonexistent')
    assert result.matches == [] and result.has_more is False


def test_limit_reports_more_passages_and_exact_last_page_is_not_truncated():
    text = '\n'.join(f'topic occurrence in source line {index}.' for index in range(21))
    chapters = [chapter('a', 0, len(text))]
    result = search_source('doc', text, chapters, ['a'], 'topic', 20)
    assert len(result.matches) == 20 and result.has_more is True
    twenty = text[:text.rfind('\n')]
    assert search_source('doc', twenty, [chapter('a', 0, len(twenty))], ['a'], 'topic').has_more is False


def test_long_paragraph_context_is_bounded_and_straddling_matches_are_complete():
    text = 'topic ' + 'x' * 1992 + 'topic ' + 'x' * 3000
    result = search_source('doc', text, [chapter('a', 0, len(text))], ['a'], 'topic')
    assert len(result.matches) == 2
    for hit in result.matches:
        assert len(hit.text) <= 2000 and hit.context_truncated
        assert hit.start_character <= hit.match_start < hit.match_end <= hit.end_character
        assert text[hit.match_start:hit.match_end] == 'topic'


@pytest.mark.parametrize('query', ['', ' ', 'a', 'a' * 121, 'x\ny', 'x\ty'])
def test_invalid_queries_rejected(query):
    with pytest.raises(ValueError):
        search_source('doc', 'abcdef', [chapter('a', 0, 6)], ['a'], query)


def test_invalid_selection_rejected_even_when_no_match():
    with pytest.raises(ValueError):
        search_source('doc', 'abcdef', [chapter('a', 0, 6)], ['a', 'missing'], 'absent')


def test_search_result_can_be_explicitly_used_as_exact_quiz_range():
    text = 'Unselected introduction.\nPhotosynthesis is a topic in this source.\nExcluded next paragraph.'
    chapters = [chapter('a', 0, len(text))]
    hit = search_source('doc', text, chapters, ['a'], 'photosynthesis').matches[0]
    selected = resolve_quiz_selection(text, chapters, ['a'], [SourceRange(
        chapter_id=hit.chapter_id, start_character=hit.start_character, end_character=hit.end_character)])
    assert text[selected[0].start_character:selected[0].end_character] == hit.text
    assert 'Unselected' not in hit.text and 'Excluded' not in hit.text


def test_api_search_is_owned_read_only_and_never_calls_generation(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        text = ('Chapter 1 Cells\nCells contain structures that support the essential processes of life.\n'
                'Chapter 2 Plants\nPhotosynthesis converts light energy into chemical energy in green plants.')
        document = client.post('/v1/documents', headers=headers, files={'file': ('source.txt', text)}).json()
        path = f"/v1/documents/{document['id']}/search"
        request = {'chapter_ids': [document['chapters'][1]['id']], 'query': 'photosynthesis'}
        def unexpected(*args):
            raise AssertionError('Source search must not call generation')
        monkeypatch.setattr('app.main.generate_document_questions', unexpected)
        monkeypatch.setattr('app.main.generate_grounded_questions', unexpected)
        result = client.post(path, headers=headers, json=request)
        assert result.status_code == 200
        assert len(result.json()['matches']) == 1
        assert result.json()['matches'][0]['text'] in text
        assert client.get(f"/v1/documents/{document['id']}", headers=headers).json() == document
        assert client.post(path, json=request).status_code == 401
        other = client.post('/v1/auth/register', json={'email': 'search-other@example.com', 'password': 'long-enough-password'}).json()
        assert client.post(path, headers={'Authorization': f"Bearer {other['access_token']}"}, json=request).status_code == 404
        assert client.post(path, headers=headers, json={**request, 'chapter_ids': ['missing']}).status_code == 422
        assert client.post(path, headers=headers, json={**request, 'limit': 21}).status_code == 422
        assert client.post(path, headers=headers, json={**request, 'query': '   '}).status_code == 422
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM quiz_creation_requests').fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)
