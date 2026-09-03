from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


def make_quiz(client, headers):
    text = ('Cells are the basic units of life in living organisms. '
            'Mitochondria release usable energy for cellular work. '
            'Ribosomes support protein synthesis inside cells. '
            'Cell membranes regulate what enters and leaves the cell. '
            'Photosynthesis converts light energy into chemical energy in plants.')
    upload = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', text)})
    assert upload.status_code == 201
    document = upload.json()
    result = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
                        json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5})
    assert result.status_code == 201
    return result.json()


def test_retry_replays_feedback_without_changing_answer_or_timestamp(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        quiz = make_quiz(client, headers)
        question = quiz['first_question']
        path = f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/answer"
        payload = {'selected_option': question['options'][0]}
        first = client.post(path, headers=headers, json=payload)
        assert first.status_code == 200
        with connection(get_settings().database_path) as db:
            before = dict(db.execute('SELECT * FROM questions WHERE id = ?', (question['id'],)).fetchone())
        retry = client.post(path, headers=headers, json=payload)
        assert retry.status_code == 200
        assert retry.json() == first.json()
        changed = client.post(path, headers=headers, json={'selected_option': question['options'][1]})
        assert changed.status_code == 409
        with connection(get_settings().database_path) as db:
            assert dict(db.execute('SELECT * FROM questions WHERE id = ?', (question['id'],)).fetchone()) == before
        assert client.get(f"/v1/quizzes/{quiz['id']}/results", headers=headers).json()['answered'] == 1
    finally:
        client.__exit__(None, None, None)


@pytest.mark.parametrize('same_choice', [False, True])
def test_competing_answers_preserve_first_committed_choice(monkeypatch, tmp_path, same_choice):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        quiz = make_quiz(client, headers)
        question = quiz['first_question']
        path = f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/answer"
        gate = Barrier(2)
        def submit(choice):
            gate.wait(timeout=5)
            return client.post(path, headers=headers, json={'selected_option': choice})
        with ThreadPoolExecutor(max_workers=2) as workers:
            choices = [question['options'][0]] * 2 if same_choice else question['options'][:2]
            futures = [workers.submit(submit, choice) for choice in choices]
            responses = [future.result(timeout=15) for future in futures]
        assert sorted(response.status_code for response in responses) == ([200, 200] if same_choice else [200, 409])
        if same_choice:
            assert responses[0].json() == responses[1].json()
        winner = next(response.json() for response in responses if response.status_code == 200)
        state = client.get(f"/v1/quizzes/{quiz['id']}", headers=headers).json()
        assert state['answered'] == 1
        assert state['last_feedback']['selected_option'] == winner['selected_option']
    finally:
        client.__exit__(None, None, None)


def test_cannot_answer_future_question_or_replay_as_another_owner(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        quiz = make_quiz(client, headers)
        with connection(get_settings().database_path) as db:
            future = db.execute('SELECT * FROM questions WHERE quiz_id = ? AND ordinal = 3', (quiz['id'],)).fetchone()
        path = f"/v1/quizzes/{quiz['id']}/questions/{future['id']}/answer"
        assert client.post(path, headers=headers, json={'selected_option': future['correct_option']}).status_code == 409
        first = quiz['first_question']
        path = f"/v1/quizzes/{quiz['id']}/questions/{first['id']}/answer"
        payload = {'selected_option': first['options'][0]}
        assert client.post(path, headers=headers, json=payload).status_code == 200
        other = client.post('/v1/auth/register', json={'email': 'other-retry@example.com', 'password': 'long-enough-password'}).json()
        assert client.post(path, headers={'Authorization': f"Bearer {other['access_token']}"}, json=payload).status_code == 404
        assert client.post(path, json=payload).status_code == 401
    finally:
        client.__exit__(None, None, None)
