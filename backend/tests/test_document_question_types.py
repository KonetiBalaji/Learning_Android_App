import sqlite3

import pytest

from app.config import get_settings
from app.database import connection, initialize
from app.quiz_service import GeneratedQuestion
from test_mastery_loop import registered_client


@pytest.mark.parametrize('kind,options', [('true_false', ['True', 'False']), ('yes_no', ['Yes', 'No'])])
def test_binary_quiz_grading_retry_resume_and_results(monkeypatch, tmp_path, kind, options):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        source = 'Mitochondria release usable energy for cellular work. ' * 5
        doc = client.post('/v1/documents', headers=headers, files={'file': ('cells.txt', source)}).json()
        path = f"/v1/documents/{doc['id']}/quizzes"
        request = dict(chapter_ids=[doc['chapters'][0]['id']], question_count=5, question_type=kind)
        assert client.post(path, headers=headers, json=request).status_code == 422
        assert client.post(path, headers=headers, json=dict(request, question_type='essay')).status_code == 422
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 0

        def generate(text, chapters, ids, count, settings, difficulty, question_type):
            assert question_type == kind
            return [GeneratedQuestion(f'Synthetic item {index}: judge the supplied statement.', options,
                options[index % 2], 'Synthetic test explanation.', 'Cells') for index in range(count)]
        monkeypatch.setattr('app.main.generate_document_questions', generate)
        monkeypatch.setenv('LEARNING_AI_MODE', 'openai')
        response = client.post(path, headers=headers, json=request)
        assert response.status_code == 201
        quiz = response.json()
        assert quiz['question_type'] == kind
        initialize(get_settings().database_path)
        state_path = f"/v1/quizzes/{quiz['id']}"
        current = client.get(state_path, headers=headers).json()
        assert current['question_type'] == kind
        question = current['question']
        for index in range(5):
            assert question['question_type'] == kind
            assert question['options'] == options
            answer_path = f"{state_path}/questions/{question['id']}/answer"
            assert client.post(answer_path, headers=headers, json={'selected_option': 'Maybe'}).status_code == 422
            response = client.post(answer_path, headers=headers, json={'selected_option': options[0]})
            assert response.status_code == 200
            feedback = response.json()
            assert feedback['correct'] == (index % 2 == 0)
            assert feedback['correct_option'] == options[index % 2]
            assert client.post(answer_path, headers=headers, json={'selected_option': options[0]}).json() == feedback
            assert client.post(answer_path, headers=headers, json={'selected_option': options[1]}).status_code == 409
            resumed = client.get(state_path, headers=headers).json()
            assert resumed['answered'] == index + 1
            assert resumed['last_feedback'] == feedback
            question = resumed['question']
        result = client.get(state_path + '/results', headers=headers).json()
        assert result['correct'] == 3
        assert result['answered'] == result['total'] == 5
        assert all(item['question_type'] == kind for item in result['mistakes'])
    finally:
        client.__exit__(None, None, None)


def test_legacy_question_type_migration_is_repeatable(tmp_path):
    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE quizzes (id TEXT PRIMARY KEY, title TEXT)')
        db.execute("INSERT INTO quizzes VALUES ('old', 'Legacy quiz')")
    initialize(path)
    initialize(path)
    with connection(path) as db:
        assert db.execute("SELECT question_type FROM quizzes WHERE id='old'").fetchone()[0] == 'multiple_choice'
