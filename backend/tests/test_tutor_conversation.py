import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.config import get_settings
from app.database import connection
from app.mastery_service import FRACTION_DIAGNOSTIC
from app.tutor_conversation import generate_tutor_answer
from test_mastery_loop import registered_client


@pytest.fixture
def lesson(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    started = client.post('/v1/mastery/diagnostics', headers=headers,
        json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
    path = f"/v1/mastery/sessions/{started['id']}"
    state = client.post(path + '/diagnostic-answer', headers=headers, json={'selected_option': '1/2'}).json()
    calls = []
    def answer(*args):
        calls.append(args)
        return {'answer': 'The denominator names the size of the equal parts.', 'supported': True}
    monkeypatch.setattr('app.main.tutor_provider', lambda settings: SimpleNamespace(answer_question=answer))
    yield client, headers, path, state['state_token'], calls
    client.__exit__(None, None, None)


def ask(client, headers, path, token, **changes):
    body = dict(request_id=str(uuid4()), expected_state=token, question='Why keep the denominator?')
    body.update(changes)
    return client.post(path + '/tutor-questions', headers=headers, json=body), body


def test_conversation_persists_replays_once_and_does_not_grade(lesson):
    client, headers, path, token, calls = lesson
    before = client.get(path, headers=headers).json()
    result, body = ask(client, headers, path, token)
    assert result.status_code == 200 and result.json()['status'] == 'complete'
    assert client.post(path + '/tutor-questions', headers=headers, json=body).json() == result.json()
    assert len(calls) == 1
    assert client.get(path, headers=headers).json() == before
    assert client.get(path + '/tutor-questions', headers=headers).json() == [result.json()]
    ask(client, headers, path, token, question='Could you explain that again?')
    assert calls[-1][-1] == [{'question': body['question'], 'answer': result.json()['reply']['answer']}]
    body['question'] = 'Different question'
    assert client.post(path + '/tutor-questions', headers=headers, json=body).status_code == 409


def test_ownership_stale_state_and_blank_questions_fail_before_provider(lesson):
    client, headers, path, token, calls = lesson
    other = client.post('/v1/auth/register', json={'email': 'other-chat@example.com', 'password': 'long-password-test'}).json()['access_token']
    assert ask(client, {'Authorization': f'Bearer {other}'}, path, token)[0].status_code == 404
    assert client.get(path + '/tutor-questions', headers={'Authorization': f'Bearer {other}'}).status_code == 404
    assert ask(client, headers, path, 'stale')[0].status_code == 409
    assert ask(client, headers, path, token, question='   ')[0].status_code == 422
    assert calls == []


def test_failure_is_persisted_redacted_and_not_retried_implicitly(lesson, monkeypatch):
    client, headers, path, token, calls = lesson
    def fail(*args):
        calls.append(args)
        raise RuntimeError('private provider details')
    monkeypatch.setattr('app.main.tutor_provider', lambda settings: SimpleNamespace(answer_question=fail))
    result, body = ask(client, headers, path, token)
    assert result.json()['status'] == 'failed' and result.json()['reply'] is None
    assert 'private' not in result.text
    client.post(path + '/tutor-questions', headers=headers, json=body)
    assert len(calls) == 1


def test_changed_lesson_discards_provider_reply(lesson, monkeypatch):
    client, headers, path, token, calls = lesson
    def change(*args):
        with connection(get_settings().database_path) as db:
            db.execute("UPDATE mastery_sessions SET coaching_rounds = coaching_rounds + 1")
        return {'answer': 'Old context answer', 'supported': True}
    monkeypatch.setattr('app.main.tutor_provider', lambda settings: SimpleNamespace(answer_question=change))
    assert ask(client, headers, path, token)[0].json()['status'] == 'failed'
    assert client.get(path + '/tutor-questions', headers=headers).json() == []


def test_limit_bounds_calls_and_deletion_cascades(lesson):
    client, headers, path, token, calls = lesson
    for _ in range(20):
        assert ask(client, headers, path, token)[0].json()['status'] == 'complete'
    assert ask(client, headers, path, token)[0].status_code == 429
    assert len(calls) == 20
    assert all(len(args[-1]) <= 6 for args in calls)
    with connection(get_settings().database_path) as db:
        db.execute('DELETE FROM users')
        assert db.execute('SELECT COUNT(*) FROM tutor_turns').fetchone()[0] == 0


def test_pending_crash_can_expire_without_repeating_old_request(lesson):
    client, headers, path, token, calls = lesson
    request_id = str(uuid4())
    with connection(get_settings().database_path) as db:
        db.execute("INSERT INTO tutor_turns VALUES (?, ?, ?, ?, 'pending', NULL, ?)",
                   (path.rsplit('/', 1)[1], request_id, token, 'Why keep the denominator?', '2000-01-01T00:00:00+00:00'))
    result, _ = ask(client, headers, path, token, request_id=request_id)
    assert result.json()['status'] == 'failed' and not calls
    assert ask(client, headers, path, token)[0].json()['status'] == 'complete'


def test_provider_receives_only_current_lesson_not_assessment_keys():
    captured = []
    def create(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(output_text=json.dumps({'answer': 'Ask about the lesson.', 'supported': False}))
    result = generate_tutor_answer(SimpleNamespace(responses=SimpleNamespace(create=create)), 'fixture', 8,
                                   FRACTION_DIAGNOSTIC[0], 'What is next?', [])
    payload = json.loads(captured[0]['input'])
    assert set(payload['lesson']) == {'concept', 'explanation', 'worked_example', 'hint'}
    assert captured[0]['store'] is False and not result.supported


def test_pending_request_prevents_concurrent_provider_work(lesson, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    client, headers, path, token, calls = lesson
    entered, release = Event(), Event()
    def blocked(*args):
        calls.append(args)
        entered.set()
        assert release.wait(10)
        return {'answer': 'Equal parts have the same size.', 'supported': True}
    monkeypatch.setattr('app.main.tutor_provider', lambda settings: SimpleNamespace(answer_question=blocked))
    request_id = str(uuid4())
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(ask, client, headers, path, token, request_id=request_id)
        try:
            assert entered.wait(5)
            assert ask(client, headers, path, token, request_id=request_id)[0].json()['status'] == 'pending'
            assert ask(client, headers, path, token)[0].status_code == 409
            assert len(calls) == 1
        finally:
            release.set()
        assert pending.result(timeout=5)[0].json()['status'] == 'complete'


@pytest.mark.parametrize('reply', [{'answer': ' ', 'supported': True}, {'answer': 'Hello', 'supported': 'true'}])
def test_invalid_provider_answer_never_persists_as_complete(lesson, monkeypatch, reply):
    client, headers, path, token, calls = lesson
    monkeypatch.setattr('app.main.tutor_provider', lambda settings: SimpleNamespace(answer_question=lambda *args: reply))
    result, _ = ask(client, headers, path, token)
    assert result.json()['status'] == 'failed' and result.json()['reply'] is None
