import pytest

from app.document_errors import DocumentErrorCode, DocumentValidationError, document_error_headers
from app.pdf_page_selection import select_pdf_pages
from app.schemas import Chapter, PdfPage
from test_mastery_loop import registered_client
from test_pdf_page_selection import pdf_bytes


def test_only_typed_codes_produce_recovery_headers():
    assert document_error_headers(ValueError('private arbitrary error')) is None
    assert document_error_headers(DocumentValidationError('untrusted-value', 'private')) is None
    for code in DocumentErrorCode:
        assert document_error_headers(DocumentValidationError(code, 'private')) == {'X-Learning-Error': code.value}


def test_pdf_coverage_and_range_limit_have_distinct_codes():
    text = 'a b c'
    with pytest.raises(DocumentValidationError) as gap:
        select_pdf_pages('doc', text, [Chapter(id='c', title='c', start_character=2, end_character=5, confidence=1)],
                         [PdfPage(page=1, start_character=0, end_character=5, has_text=True)], 1, 1)
    assert gap.value.code == DocumentErrorCode.PDF_COVERAGE_GAP
    text = 'x ' * 51
    chapters = [Chapter(id=str(i), title=str(i), start_character=i * 2, end_character=i * 2 + 1, confidence=1) for i in range(51)]
    with pytest.raises(DocumentValidationError) as many:
        select_pdf_pages('doc', text, chapters, [PdfPage(page=1, start_character=0, end_character=len(text), has_text=True)], 1, 1)
    assert many.value.code == DocumentErrorCode.TOO_MANY_PDF_RANGES


def test_http_codes_preserve_status_owner_checks_and_success(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        doc = client.post('/v1/documents', headers=headers,
            files={'file': ('pages.pdf', pdf_bytes(), 'application/pdf')}).json()
        pages = f"/v1/documents/{doc['id']}/pdf-pages/selection"
        empty = client.post(pages, headers=headers, json={'first_page': 3, 'last_page': 3})
        assert empty.status_code == 422
        assert empty.headers['X-Learning-Error'] == 'empty_pdf_pages'
        invalid = client.post(pages, headers=headers, json={'first_page': True, 'last_page': 3})
        assert invalid.status_code == 422 and 'X-Learning-Error' not in invalid.headers
        unauthorized = client.post(pages, json={'first_page': 3, 'last_page': 3})
        assert unauthorized.status_code == 401 and 'X-Learning-Error' not in unauthorized.headers
        scope = client.post(pages, headers=headers, json={'first_page': 2, 'last_page': 2}).json()
        request = {'chapter_ids': scope['chapter_ids'], 'source_ranges': scope['source_ranges'], 'question_count': 10}
        path = f"/v1/documents/{doc['id']}/quizzes"
        insufficient = client.post(path, headers=headers, json=request)
        assert insufficient.status_code == 422
        assert insufficient.headers['X-Learning-Error'] == 'insufficient_quiz_material'
        request['question_count'] = 5
        success = client.post(path, headers=headers, json=request)
        assert success.status_code == 201 and 'X-Learning-Error' not in success.headers
    finally:
        client.__exit__(None, None, None)
