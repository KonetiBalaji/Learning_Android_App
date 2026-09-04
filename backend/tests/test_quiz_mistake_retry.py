import uuid

from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


def test_retry_mistakes_is_owned_idempotent_and_copies_only_incorrect(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        source = ('Cells are the basic units of life in all known living organisms. '
                  'Mitochondria release usable energy that supports cellular work. '
                  'Ribosomes support protein synthesis inside many living cells. '
                  'Cell membranes regulate which materials enter and leave each cell. '
                  'Photosynthesis converts light energy into chemical energy in plants.')
        document = client.post('/v1/documents', headers=headers,
            files={'file': ('cells.txt', source)}).json()
        quiz = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
            json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5}).json()
        state = client.get(f"/v1/quizzes/{quiz['id']}", headers=headers).json()
        first = state['question']
        with connection(get_settings().database_path) as db:
            first_correct = db.execute('SELECT correct_option FROM questions WHERE id = ?',
                                       (first['id'],)).fetchone()[0]
        wrong = next(option for option in first['options'] if option != first_correct)
        first_feedback = client.post(f"/v1/quizzes/{quiz['id']}/questions/{first['id']}/answer",
            headers=headers, json={'selected_option': wrong}).json()
        question = first_feedback['next_question']
        while question is not None:
            with connection(get_settings().database_path) as db:
                answer = db.execute('SELECT correct_option FROM questions WHERE id = ?',
                                    (question['id'],)).fetchone()[0]
            feedback = client.post(f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/answer",
                headers=headers, json={'selected_option': answer}).json()
            question = feedback['next_question']

        request = {'request_id': str(uuid.uuid4())}
        path = f"/v1/quizzes/{quiz['id']}/retry-mistakes"
        retry = client.post(path, headers=headers, json=request)
        assert retry.status_code == 201
        assert retry.json()['question_count'] == 1
        assert retry.json()['first_question']['prompt'] == first['prompt']
        assert retry.json()['first_question']['id'] != first['id']
        assert client.post(path, headers=headers, json=request).json() == retry.json()
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quiz_retry_requests').fetchone()[0] == 1
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 2

        other = client.post('/v1/auth/register', json={
            'email': 'retry-other@example.com', 'password': 'long-enough-password'}).json()
        other_headers = {'Authorization': f"Bearer {other['access_token']}"}
        assert client.post(path, headers=other_headers, json={'request_id': str(uuid.uuid4())}).status_code == 404
        assert client.post(path, json=request).status_code == 401
    finally:
        client.__exit__(None, None, None)


def test_retry_rejects_unfinished_quiz(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        source = ('Cells are the basic units of life in all known living organisms. '
                  'Mitochondria release usable energy that supports cellular work. '
                  'Ribosomes support protein synthesis inside many living cells. '
                  'Cell membranes regulate which materials enter and leave each cell. '
                  'Photosynthesis converts light energy into chemical energy in plants.')
        document = client.post('/v1/documents', headers=headers,
            files={'file': ('cells.txt', source)}).json()
        quiz = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
            json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5}).json()
        response = client.post(f"/v1/quizzes/{quiz['id']}/retry-mistakes", headers=headers,
            json={'request_id': str(uuid.uuid4())})
        assert response.status_code == 409
        assert response.json()['detail'] == 'Finish this quiz before retrying its mistakes'
    finally:
        client.__exit__(None, None, None)


def test_retry_rejects_completed_quiz_without_mistakes(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        source = ('Cells are the basic units of life in all known living organisms. '
                  'Mitochondria release usable energy that supports cellular work. '
                  'Ribosomes support protein synthesis inside many living cells. '
                  'Cell membranes regulate which materials enter and leave each cell. '
                  'Photosynthesis converts light energy into chemical energy in plants.')
        document = client.post('/v1/documents', headers=headers,
            files={'file': ('cells.txt', source)}).json()
        quiz = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
            json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5}).json()
        with connection(get_settings().database_path) as db:
            db.execute('UPDATE questions SET answered_option = correct_option WHERE quiz_id = ?',
                       (quiz['id'],))
        response = client.post(f"/v1/quizzes/{quiz['id']}/retry-mistakes", headers=headers,
            json={'request_id': str(uuid.uuid4())})
        assert response.status_code == 409
        assert response.json()['detail'] == 'This quiz has no answered mistakes to retry'
    finally:
        client.__exit__(None, None, None)
