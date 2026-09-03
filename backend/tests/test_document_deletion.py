from pathlib import Path

from app.config import get_settings
from app.database import connection
from test_document_answer_retries import make_quiz
from test_mastery_loop import registered_client


def test_document_deletion_removes_file_and_quiz_but_preserves_other_material(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        removed = make_quiz(client, headers)
        kept = make_quiz(client, headers)
        first = removed['first_question']
        assert client.post(f"/v1/quizzes/{removed['id']}/questions/{first['id']}/answer", headers=headers,
                           json={'selected_option': first['options'][0]}).status_code == 200
        with connection(get_settings().database_path) as db:
            documents = [db.execute('SELECT documents.* FROM documents JOIN quizzes ON quizzes.document_id = documents.id WHERE quizzes.id = ?',
                                   (quiz['id'],)).fetchone() for quiz in (removed, kept)]
        removed_document, kept_document = documents
        removed_path = Path(removed_document['stored_path'])
        kept_path = Path(kept_document['stored_path'])
        assert removed_path.is_file() and kept_path.is_file()
        assert client.delete(f"/v1/documents/{removed_document['id']}", headers=headers).status_code == 204
        assert not removed_path.exists()
        assert kept_path.is_file()
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM questions WHERE quiz_id = ?', (removed['id'],)).fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM quizzes WHERE id = ?', (removed['id'],)).fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM questions WHERE quiz_id = ?', (kept['id'],)).fetchone()[0] == 5
        assert client.get(f"/v1/quizzes/{removed['id']}", headers=headers).status_code == 404
        assert client.get(f"/v1/quizzes/{kept['id']}", headers=headers).status_code == 200
        assert [item['id'] for item in client.get('/v1/documents', headers=headers).json()] == [kept_document['id']]
    finally:
        client.__exit__(None, None, None)
