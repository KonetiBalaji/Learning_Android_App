from pathlib import Path

import fitz
import pytest

from app.config import get_settings
from app.database import connection
from app.document_service import detect_chapters, extract_text
from app.pdf_page_selection import read_pdf_pages, select_pdf_pages
from app.schemas import Chapter, PdfPage
from test_mastery_loop import registered_client


def pdf_bytes():
    # In-memory synthetic API fixture, not a delivered document.
    with fitz.open() as pdf:
        for text in [
            'Chapter 1 Cells\nCells are the basic units of life in living organisms.\n'
            'Mitochondria release usable energy for cellular work.\n'
            'Ribosomes support protein synthesis inside cells.\n'
            'Cell membranes regulate what enters and leaves the cell.\n'
            'The nucleus contains genetic information for the cell.',
            'Chapter 2 Plants\nPhotosynthesis converts light energy into chemical energy.\n'
            'Roots absorb water and minerals from the soil.\n'
            'Stems support leaves and transport materials through plants.\n'
            'Flowers contain reproductive structures in flowering plants.\n'
            'Seeds contain an embryo and stored food for early growth.',
            '',
        ]:
            page = pdf.new_page()
            if text:
                page.insert_text((54, 72), text, fontsize=11)
        return pdf.tobytes()


def fixture(tmp_path):
    uploads = tmp_path / 'uploads'
    uploads.mkdir()
    stored = uploads / 'fixture.pdf'
    content = pdf_bytes()
    stored.write_bytes(content)
    text = extract_text(content, '.pdf')
    return stored, uploads, text


def test_physical_page_offsets_match_upload_extraction_and_blank_pages(tmp_path):
    stored, uploads, text = fixture(tmp_path)
    pages = read_pdf_pages(stored, uploads, text, 1_000_000)
    assert [page.page for page in pages] == [1, 2, 3]
    assert [page.has_text for page in pages] == [True, True, False]
    assert pages[2].start_character == pages[2].end_character
    with fitz.open(stored) as pdf:
        for page, original in zip(pages, pdf):
            assert text[page.start_character:page.end_character] == original.get_text('text')
    selection = select_pdf_pages('doc', text, detect_chapters(text), pages, 2, 2)
    selected_text = ''.join(text[part.start_character:part.end_character] for part in selection.source_ranges)
    assert 'Photosynthesis' in selected_text and 'Mitochondria' not in selected_text
    assert selection.chapter_ids == ['chapter-2']
    assert select_pdf_pages('doc', text, detect_chapters(text), pages, 1, 3).empty_pages == [3]
    with pytest.raises(ValueError, match='no extractable text'):
        select_pdf_pages('doc', text, detect_chapters(text), pages, 3, 3)


@pytest.mark.parametrize('first,last', [(0, 1), (2, 1), (1, 4)])
def test_invalid_page_ranges_fail(tmp_path, first, last):
    stored, uploads, text = fixture(tmp_path)
    pages = read_pdf_pages(stored, uploads, text, 1_000_000)
    with pytest.raises(ValueError):
        select_pdf_pages('doc', text, detect_chapters(text), pages, first, last)


def test_mismatched_source_outside_storage_size_and_corruption_fail(tmp_path):
    stored, uploads, text = fixture(tmp_path)
    with pytest.raises(ValueError, match='no longer matches'):
        read_pdf_pages(stored, uploads, text + 'changed', 1_000_000)
    with pytest.raises(ValueError, match='storage path'):
        read_pdf_pages(stored, tmp_path / 'other', text, 1_000_000)
    with pytest.raises(ValueError, match='size limit'):
        read_pdf_pages(stored, uploads, text, 1)
    stored.write_bytes(b'corrupt fixture')
    with pytest.raises((ValueError, RuntimeError)):
        read_pdf_pages(stored, uploads, text, 1_000_000)


def test_omitted_source_is_not_silently_dropped(tmp_path):
    stored, uploads, text = fixture(tmp_path)
    pages = read_pdf_pages(stored, uploads, text, 1_000_000)
    chapters = [Chapter(id='partial', title='Partial', start_character=5, end_character=len(text), confidence=.5)]
    with pytest.raises(ValueError, match='omitted source'):
        select_pdf_pages('doc', text, chapters, pages, 1, 1)


def test_page_selection_clips_chapters_crossing_physical_page_boundaries():
    text = 'ABCDEFGHIJklmnopqrst'
    pages = [PdfPage(page=1, start_character=0, end_character=10, has_text=True),
             PdfPage(page=2, start_character=10, end_character=20, has_text=True)]
    chapters = [Chapter(id='a', title='A', start_character=0, end_character=13, confidence=.8),
                Chapter(id='b', title='B', start_character=13, end_character=20, confidence=.8)]
    selection = select_pdf_pages('doc', text, chapters, pages, 2, 2)
    assert selection.chapter_ids == ['a', 'b']
    assert [(part.start_character, part.end_character) for part in selection.source_ranges] == [(10, 13), (13, 20)]
    assert ''.join(text[part.start_character:part.end_character] for part in selection.source_ranges) == 'klmnopqrst'


def test_api_page_selection_is_owned_read_only_and_drives_exact_quiz(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        response = client.post('/v1/documents', headers=headers, files={'file': ('pages.pdf', pdf_bytes(), 'application/pdf')})
        assert response.status_code == 201
        doc = response.json()
        path = f"/v1/documents/{doc['id']}/pdf-pages"
        index = client.get(path, headers=headers)
        assert index.status_code == 200 and len(index.json()['pages']) == 3
        selected = client.post(path + '/selection', headers=headers, json={'first_page': 2, 'last_page': 2})
        assert selected.status_code == 200
        scope = selected.json()
        assert scope['chapter_ids'] == ['chapter-2']
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 0
        quiz = client.post(f"/v1/documents/{doc['id']}/quizzes", headers=headers,
            json={'chapter_ids': scope['chapter_ids'], 'source_ranges': scope['source_ranges'], 'question_count': 5})
        assert quiz.status_code == 201, quiz.text
        assert quiz.json()['source_ranges'] == scope['source_ranges']
        with connection(get_settings().database_path) as db:
            for row in db.execute('SELECT explanation FROM questions'):
                assert 'Mitochondria' not in row['explanation'] and 'nucleus' not in row['explanation']
        assert client.get(path).status_code == 401
        other = client.post('/v1/auth/register', json={'email': 'page-other@example.com', 'password': 'long-enough-password'}).json()
        other_headers = {'Authorization': f"Bearer {other['access_token']}"}
        assert client.get(path, headers=other_headers).status_code == 404
        assert client.post(path + '/selection', headers=other_headers, json={'first_page': 1, 'last_page': 2}).status_code == 404
        assert client.post(path + '/selection', headers=headers, json={'first_page': 3, 'last_page': 3}).status_code == 422
        assert client.post(path + '/selection', headers=headers, json={'first_page': True, 'last_page': 2}).status_code == 422
        with connection(get_settings().database_path) as db:
            stored = Path(db.execute('SELECT stored_path FROM documents').fetchone()[0])
        stored.unlink()
        assert client.get(path, headers=headers).status_code == 503
    finally:
        client.__exit__(None, None, None)
