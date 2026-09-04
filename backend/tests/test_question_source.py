import re
import base64

import fitz

from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


SOURCE = """Chapter 1 Cells
Cells contain structures that support the essential processes of life.
The cell membrane controls which substances enter and leave the cell.
Mitochondria release usable energy from nutrients during cellular respiration.
Ribosomes assemble proteins that cells need for growth and repair.
Chloroplasts contain chlorophyll and capture light energy in plant cells.
The nucleus stores genetic information and helps direct cell activities.
The cytoplasm supports many chemical reactions within the living cell.
Vacuoles store water and other materials used by cells.
Cell walls provide firm support around many plant cells.
Specialized cells have structures suited to their particular functions.
Organ systems depend on cells working together in organized groups.
"""


def source_pdf() -> bytes:
    with fitz.open() as pdf:
        page = pdf.new_page()
        for index, line in enumerate(SOURCE.splitlines()):
            page.insert_text((54, 54 + index * 18), line, fontsize=10)
        return pdf.tobytes()


def test_answered_question_exposes_exact_owned_source_and_unanswered_does_not(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        document = client.post('/v1/documents', headers=headers,
            files={'file': ('cells.txt', SOURCE)}).json()
        quiz = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
            json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5}).json()
        question = quiz['first_question']
        path = f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/source"
        assert client.get(path, headers=headers).status_code == 409
        other = client.post('/v1/auth/register', json={
            'email': 'source-other@example.com', 'password': 'long-enough-password'}).json()
        assert client.get(path, headers={
            'Authorization': f"Bearer {other['access_token']}"}).status_code == 404
        answer = client.post(
            f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/answer",
            headers=headers, json={'selected_option': question['options'][0]})
        assert answer.status_code == 200
        evidence = client.get(path, headers=headers)
        assert evidence.status_code == 200
        value = evidence.json()
        assert value['quiz_id'] == quiz['id'] and value['question_id'] == question['id']
        assert value['text'] == SOURCE[value['start_character']:value['end_character']]
        start, end = map(int, re.search(r'source characters (\d+)-(\d+)',
                                       value['source_reference']).groups())
        assert (start, end) == (value['start_character'], value['end_character'])
        assert value['text'].strip() in answer.json()['explanation']
    finally:
        client.__exit__(None, None, None)


def test_invalid_historical_reference_fails_closed(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        document = client.post('/v1/documents', headers=headers,
            files={'file': ('cells.txt', SOURCE)}).json()
        quiz = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
            json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5}).json()
        question = quiz['first_question']
        client.post(f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/answer",
                    headers=headers, json={'selected_option': question['options'][0]})
        with connection(get_settings().database_path) as db:
            db.execute("UPDATE questions SET source_reference = 'Legacy chapter label' WHERE id = ?",
                       (question['id'],))
        response = client.get(
            f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/source", headers=headers)
        assert response.status_code == 409
        assert response.json()['detail'] == 'Exact source evidence is unavailable for this question'
    finally:
        client.__exit__(None, None, None)


def test_answered_pdf_question_includes_bounded_original_page_image(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        document = client.post('/v1/documents', headers=headers,
            files={'file': ('cells.pdf', source_pdf(), 'application/pdf')}).json()
        quiz = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
            json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5}).json()
        question = quiz['first_question']
        client.post(f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/answer",
                    headers=headers, json={'selected_option': question['options'][0]})
        response = client.get(
            f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/source", headers=headers)
        assert response.status_code == 200, response.text
        pages = response.json()['original_pdf_pages']
        assert len(pages) == 1 and pages[0]['page'] == 1
        assert pages[0]['mime_type'] == 'image/png'
        image = base64.b64decode(pages[0]['image_base64'], validate=True)
        assert image.startswith(b'\x89PNG\r\n\x1a\n') and len(image) < 6_000_000
        with fitz.open(stream=image, filetype='png') as rendered:
            assert rendered[0].rect.width > 0 and rendered[0].rect.height > 0
    finally:
        client.__exit__(None, None, None)
