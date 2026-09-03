import pytest

from app.document_selection import resolve_chapters
from app.document_service import detect_chapters


@pytest.mark.parametrize('prefix', ['', 'A short but important introduction.\n'])
def test_every_heading_range_including_short_sections_is_preserved(prefix):
    text = prefix + 'Chapter 1 Cells\nCells are alive.\nSection 1 Definition\nA cell is a unit.\nChapter 2 Plants\n' + 'Plants need light. ' * 8
    chapters = detect_chapters(text)
    selected = resolve_chapters(text, chapters, [chapter.id for chapter in chapters])
    assert ''.join(text[c.start_character:c.end_character] for c in selected) == text
    assert len({c.id for c in chapters}) == len(chapters)
    assert [c.title for c in chapters if c.id != 'document-introduction'] == [
        'Chapter 1 Cells', 'Section 1 Definition', 'Chapter 2 Plants']
    assert next(c for c in chapters if c.id == 'chapter-1').confidence == 0.55
    assert chapters[-1].confidence == 0.85


def test_short_final_section_is_not_lost_after_long_chapter():
    text = 'Chapter 1 Plants\n' + 'Plants need light. ' * 8 + '\nSection 2 Summary\nRemember sunlight.'
    chapters = detect_chapters(text)
    assert chapters[-1].title == 'Section 2 Summary'
    assert chapters[-1].end_character == len(text)
    assert chapters[-1].confidence == 0.55


def test_introduction_does_not_renumber_heading_ids():
    body = 'Chapter 1 Cells\nCells are alive.\nChapter 2 Plants\nPlants need light.'
    without = detect_chapters(body)
    with_intro = detect_chapters('Introduction text.\n' + body)
    assert [(c.id, c.title) for c in with_intro[1:]] == [(c.id, c.title) for c in without]


def test_whitespace_prefix_does_not_create_empty_introduction():
    chapters = detect_chapters('\n\nChapter 1 Cells\nCells are alive.')
    assert len(chapters) == 1
    assert chapters[0].id == 'chapter-1'


def test_no_heading_keeps_whole_document_fallback():
    text = 'A plain source without headings.'
    chapter, = detect_chapters(text)
    assert chapter.id == 'whole-document'
    assert (chapter.start_character, chapter.end_character) == (0, len(text))


def test_uploaded_structure_preserves_coverage_when_reopened(monkeypatch, tmp_path):
    from test_mastery_loop import registered_client
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        text = 'Important opening definition.\nChapter 1 Cells\nCells are alive.\nChapter 2 Plants\n' + 'Plants need light. ' * 8
        response = client.post('/v1/documents', headers=headers, files={'file': ('sections.txt', text)})
        assert response.status_code == 201
        uploaded = response.json()
        reopened = client.get(f"/v1/documents/{uploaded['id']}", headers=headers).json()
        assert reopened['chapters'] == uploaded['chapters']
        assert ''.join(text[c['start_character']:c['end_character']] for c in reopened['chapters']) == text
        assert reopened['chapters'][0]['id'] == 'document-introduction'
    finally:
        client.__exit__(None, None, None)
