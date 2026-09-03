import pytest

from app.config import get_settings
from app.database import connection, initialize
from test_mastery_loop import registered_client


def test_mixed_plan_has_balanced_explicit_demands():
    from app.quiz_difficulty import difficulty_plan
    for count in range(5, 21):
        plan = difficulty_plan('mixed', count)
        counts = [plan.count(level) for level in ['easy', 'medium', 'hard']]
        assert len(plan) == count
        assert min(counts) > 0
        assert max(counts) - min(counts) <= 1
    assert difficulty_plan('hard', 5) == ['hard'] * 5
    assert difficulty_plan(None, 5) == []


def test_difficulty_is_validated_saved_and_resumed(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        text = ' '.join(f'Example {index}: plants convert sunlight into stored chemical energy through photosynthesis.' for index in range(5))
        document = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', text)}).json()
        path = f"/v1/documents/{document['id']}/quizzes"
        payload = {'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5}
        assert client.post(path, headers=headers, json=dict(payload, difficulty='expert')).status_code == 422
        for unsupported in ['medium', 'hard', 'mixed']:
            assert client.post(path, headers=headers, json=dict(payload, difficulty=unsupported)).status_code == 422
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 0
        for difficulty in [None, 'easy']:
            result = client.post(path, headers=headers, json=dict(payload, difficulty=difficulty))
            assert result.status_code == 201
            assert result.json()['difficulty'] == difficulty
            initialize(get_settings().database_path)  # Repeated initialization preserves metadata.
            resumed = client.get(f"/v1/quizzes/{result.json()['id']}", headers=headers)
            assert resumed.json()['difficulty'] == difficulty
    finally:
        client.__exit__(None, None, None)


def test_legacy_quiz_schema_migrates_without_inventing_difficulty(tmp_path):
    import sqlite3
    path = tmp_path / 'old.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE quizzes (id TEXT PRIMARY KEY, document_id TEXT, owner_id TEXT, title TEXT, created_at TEXT, completed_at TEXT)')
        db.execute("INSERT INTO quizzes (id, title) VALUES ('old', 'Existing quiz')")
    initialize(path)
    with connection(path) as db:
        row = db.execute("SELECT title, difficulty FROM quizzes WHERE id = 'old'").fetchone()
        assert row['title'] == 'Existing quiz'
        assert row['difficulty'] is None


@pytest.mark.parametrize('difficulty', ['medium', 'hard', 'mixed'])
def test_live_route_passes_and_persists_requested_difficulty(monkeypatch, tmp_path, difficulty):
    from app.quiz_service import generate_grounded_questions
    client, headers = registered_client(monkeypatch, tmp_path)
    seen = []
    def generated(text, chapters, ids, count, settings, requested):
        seen.append(requested)
        return generate_grounded_questions(text, chapters, ids, count)
    try:
        text = ' '.join(f'Example {index}: plants convert sunlight into stored chemical energy through photosynthesis.' for index in range(5))
        document = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', text)}).json()
        monkeypatch.setattr('app.main.generate_document_questions', generated)
        monkeypatch.setenv('LEARNING_AI_MODE', 'openai')
        result = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
            json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5, 'difficulty': difficulty})
        assert result.status_code == 201
        assert seen == [difficulty]
        assert result.json()['difficulty'] == difficulty
        resumed = client.get(f"/v1/quizzes/{result.json()['id']}", headers=headers)
        assert resumed.json()['difficulty'] == difficulty
    finally:
        client.__exit__(None, None, None)
