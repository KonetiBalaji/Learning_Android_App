from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from app.config import get_settings
from app.database import connection, initialize
from app.quiz_service import generate_grounded_questions
from test_mastery_loop import registered_client

SOURCE = ' '.join(f'Example {i}: plants convert sunlight into stored chemical energy through photosynthesis.' for i in range(5))


def upload(client, headers):
    doc = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', SOURCE)}).json()
    return f"/v1/documents/{doc['id']}/quizzes", {
        'chapter_ids': [doc['chapters'][0]['id']], 'question_count': 5, 'request_id': str(uuid4())}


def test_committed_creation_retry_skips_generation_and_preserves_answers(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        path, payload = upload(client, headers)
        first = client.post(path, headers=headers, json=payload)
        assert first.status_code == 201
        quiz = first.json()
        question = quiz['first_question']
        client.post(f"/v1/quizzes/{quiz['id']}/questions/{question['id']}/answer", headers=headers,
                    json={'selected_option': question['options'][0]})
        def fail(*args):
            raise AssertionError('Committed retry must not regenerate')
        monkeypatch.setattr('app.main.generate_grounded_questions', fail)
        initialize(get_settings().database_path)
        replay = client.post(path, headers=headers, json=payload)
        assert replay.status_code == 201
        assert replay.json() == quiz
        assert client.get(f"/v1/quizzes/{quiz['id']}", headers=headers).json()['answered'] == 1
        for change in [{'question_count': 6}, {'difficulty': 'easy'}, {'question_type': 'true_false'},
                       {'chapter_ids': ['different-chapter']}]:
            assert client.post(path, headers=headers, json={**payload, **change}).status_code == 409
        assert client.post(path, headers=headers, json=dict(payload, request_id='not-a-uuid')).status_code == 422
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 1
            assert db.execute('SELECT COUNT(*) FROM questions').fetchone()[0] == 5
    finally:
        client.__exit__(None, None, None)


def test_concurrent_generation_commits_only_one_quiz(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        path, payload = upload(client, headers)
        barrier = Barrier(2)
        def generate(*args):
            barrier.wait(timeout=5)
            return generate_grounded_questions(*args)
        monkeypatch.setattr('app.main.generate_grounded_questions', generate)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(client.post, path, headers=headers, json=payload) for _ in range(2)]
            responses = [future.result(timeout=15) for future in futures]
        assert [response.status_code for response in responses] == [201, 201]
        assert responses[0].json() == responses[1].json()
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 1
            assert db.execute('SELECT COUNT(*) FROM quiz_creation_requests').fetchone()[0] == 1
    finally:
        client.__exit__(None, None, None)


def test_request_ids_are_owner_scoped_and_deleted_with_document(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        path, payload = upload(client, headers)
        assert client.post(path, headers=headers, json=payload).status_code == 201
        token = client.post('/v1/auth/register', json={'email': 'other@example.com', 'password': 'long-enough-password'}).json()['access_token']
        other = {'Authorization': f'Bearer {token}'}
        assert client.post(path, headers=other, json=payload).status_code == 404
        other_path, other_payload = upload(client, other)
        other_payload['request_id'] = payload['request_id']
        assert client.post(other_path, headers=other, json=other_payload).status_code == 201
        assert client.delete(path.removesuffix('/quizzes'), headers=headers).status_code == 204
        assert client.post(path, headers=headers, json=payload).status_code == 404
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quiz_creation_requests').fetchone()[0] == 1
    finally:
        client.__exit__(None, None, None)


def test_failed_attempt_does_not_consume_key_and_legacy_creations_stay_distinct(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        path, payload = upload(client, headers)
        def fail(*args):
            raise ValueError('Synthetic failure')
        monkeypatch.setattr('app.main.generate_grounded_questions', fail)
        assert client.post(path, headers=headers, json=payload).status_code == 422
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quiz_creation_requests').fetchone()[0] == 0
        monkeypatch.setattr('app.main.generate_grounded_questions', generate_grounded_questions)
        first = client.post(path, headers=headers, json=payload)
        assert first.status_code == 201
        payload.pop('request_id')
        second = client.post(path, headers=headers, json=payload)
        third = client.post(path, headers=headers, json=payload)
        assert len({first.json()['id'], second.json()['id'], third.json()['id']}) == 3
    finally:
        client.__exit__(None, None, None)
