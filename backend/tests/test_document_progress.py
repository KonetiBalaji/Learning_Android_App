from app.config import get_settings
from app.database import connection
from app.quiz_service import grounded_concept_term
from test_mastery_loop import registered_client


SOURCE = ('Cells are the basic units of life in all known living organisms. '
          'Mitochondria release usable energy that supports cellular work. '
          'Ribosomes support protein synthesis inside many living cells. '
          'Cell membranes regulate which materials enter and leave each cell. '
          'Photosynthesis converts light energy into chemical energy in plants.')


def test_deterministic_concept_uses_substantive_grounded_term():
    assert grounded_concept_term('Phloem carries sugars from leaves to other parts of a plant.') == 'Phloem'
    assert grounded_concept_term('The nucleus contains genetic information.') == 'nucleus'


def create_quiz(client, headers, document, count=5):
    return client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
        json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': count}).json()


def complete_quiz(client, headers, quiz_id, correct_count):
    state = client.get(f'/v1/quizzes/{quiz_id}', headers=headers).json()
    question = state['question']
    answered = 0
    while question is not None:
        with connection(get_settings().database_path) as db:
            correct = db.execute('SELECT correct_option FROM questions WHERE id = ?',
                                 (question['id'],)).fetchone()[0]
        selected = correct if answered < correct_count else next(
            option for option in question['options'] if option != correct)
        feedback = client.post(f"/v1/quizzes/{quiz_id}/questions/{question['id']}/answer",
            headers=headers, json={'selected_option': selected}).json()
        answered += 1
        question = feedback['next_question']


def test_document_progress_tracks_attempts_sources_and_improvement(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        document = client.post('/v1/documents', headers=headers,
            files={'file': ('cells.txt', SOURCE)}).json()
        empty = client.get(f"/v1/documents/{document['id']}/progress", headers=headers).json()
        assert empty == {'document_id': document['id'], 'quizzes_created': 0,
            'quizzes_completed': 0, 'questions_answered': 0, 'correct_answers': 0,
            'accuracy': 0.0, 'trend': 'insufficient_data',
            'improvement_percentage_points': None, 'strong_source_areas': [],
            'weak_source_areas': [], 'strongest_concepts': [], 'weak_concepts': [],
            'chapters': [{'chapter_id': document['chapters'][0]['id'],
                'title': document['chapters'][0]['title'], 'questions_answered': 0,
                'correct_answers': 0, 'accuracy': None}], 'attempts': []}

        first = create_quiz(client, headers, document)
        complete_quiz(client, headers, first['id'], 2)
        second = create_quiz(client, headers, document)
        complete_quiz(client, headers, second['id'], 4)
        progress = client.get(f"/v1/documents/{document['id']}/progress", headers=headers).json()
        assert progress['quizzes_created'] == progress['quizzes_completed'] == 2
        assert progress['questions_answered'] == 10
        assert progress['correct_answers'] == 6
        assert progress['accuracy'] == 0.6
        assert progress['trend'] == 'improving'
        assert progress['improvement_percentage_points'] == 40.0
        assert len(progress['strong_source_areas']) > 0
        assert len(progress['weak_source_areas']) > 0
        assert len(progress['strongest_concepts']) > 0
        assert len(progress['weak_concepts']) > 0
        assert progress['chapters'][0]['questions_answered'] == 10
        assert progress['chapters'][0]['correct_answers'] == 6
        assert progress['chapters'][0]['accuracy'] == 0.6
        assert all(attempt['complete'] and attempt['completed_at'] for attempt in progress['attempts'])
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes WHERE completed_at IS NOT NULL').fetchone()[0] == 2
            attributed = db.execute('SELECT chapter_id, concept FROM questions').fetchall()
            assert all(row['chapter_id'] == document['chapters'][0]['id'] and row['concept'] for row in attributed)
    finally:
        client.__exit__(None, None, None)


def test_document_progress_is_owner_scoped_and_excludes_unfinished_from_trend(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        document = client.post('/v1/documents', headers=headers,
            files={'file': ('cells.txt', SOURCE)}).json()
        quiz = create_quiz(client, headers, document)
        question = quiz['first_question']
        client.post(f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/answer",
            headers=headers, json={'selected_option': question['options'][0]})
        progress = client.get(f"/v1/documents/{document['id']}/progress", headers=headers).json()
        assert progress['quizzes_created'] == 1
        assert progress['quizzes_completed'] == 0
        assert progress['questions_answered'] == 1
        assert progress['trend'] == 'insufficient_data'
        assert progress['attempts'][0]['complete'] is False
        assert progress['attempts'][0]['completed_at'] is None

        other = client.post('/v1/auth/register', json={
            'email': 'progress-other@example.com', 'password': 'long-enough-password'}).json()
        other_headers = {'Authorization': f"Bearer {other['access_token']}"}
        assert client.get(f"/v1/documents/{document['id']}/progress", headers=other_headers).status_code == 404
        assert client.get(f"/v1/documents/{document['id']}/progress").status_code == 401
    finally:
        client.__exit__(None, None, None)
