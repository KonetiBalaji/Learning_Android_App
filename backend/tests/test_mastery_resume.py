from fastapi.testclient import TestClient

from test_mastery_loop import registered_client


def test_resume_tracks_phases_without_answer_leakage_or_provider_calls(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post("/v1/mastery/diagnostics", headers=headers,
                              json={"grade": 8, "subject_id": "math", "chapter_id": "fractions"}).json()
        path = f"/v1/mastery/sessions/{started['id']}"
        initial = client.get(path, headers=headers).json()
        assert initial["status"] == "diagnostic"
        assert initial["catalog_version"] == "open-oer-foundation-2026-09"
        assert initial["grade"] == 8
        assert initial["question"]["ordinal"] == 1
        assert "correct_option" not in initial["question"]
        assert initial["tutor"] is None
        outcome = client.post(path + "/diagnostic-answer", headers=headers, json={"selected_option": "1/2"}).json()
        coaching = client.get(path, headers=headers).json()
        assert coaching["status"] == "tutor"
        assert coaching["tutor"] == outcome["tutor"]
        assert coaching["selected_option"] == "1/2"

        # Reads recover committed state from the database even through another app lifecycle.
        from app.main import app
        with TestClient(app) as restarted:
            assert restarted.get(path, headers=headers).json() == coaching

        assert client.post(path + "/practice", headers=headers, json={"response": "7/8"}).status_code == 200
        assert client.get(path, headers=headers).json()["status"] == "practice"
        client.post(path + "/practice", headers=headers, json={"response": "6/8"})
        assert client.get(path, headers=headers).json()["status"] == "rewrite"
        client.post(path + "/rewrite", headers=headers, json={"response": "Because it does."})
        retry = client.get(path, headers=headers).json()
        assert retry["status"] == "tutor"
        assert "Explain the key idea" in retry["tutor"]["explanation"]
        client.post(path + "/practice", headers=headers, json={"response": "6/8"})
        client.post(path + "/rewrite", headers=headers,
                    json={"response": "We add the numerator parts with the same denominator to make one whole."})
        resumed = client.get(path, headers=headers).json()
        assert resumed["status"] == "diagnostic"
        assert resumed["question"]["ordinal"] == 2
        assert resumed["tutor"] is None
        assert resumed["mastery_score"] == 1 / 3
        for answer in ("3/6", "4/8"):
            client.post(path + "/diagnostic-answer", headers=headers, json={"selected_option": answer})
        mastered = client.get(path, headers=headers).json()
        assert mastered["status"] == "mastered"
        assert mastered["question"] is None
        assert mastered["mastery_score"] == 1
        other_token = client.post("/v1/auth/register", json={"email": "other-resume@example.com", "password": "long-enough-password"}).json()["access_token"]
        assert client.get(path, headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
        assert client.get(path).status_code == 401
    finally:
        client.__exit__(None, None, None)


def test_existing_database_sessions_gain_explicit_catalog_version(monkeypatch, tmp_path):
    from app.database import initialize, connection
    from app.learning_path import CATALOG_VERSION
    import sqlite3

    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as db:
        db.executescript('''
            CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE mastery_sessions (
              id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
              grade INTEGER NOT NULL, subject_id TEXT NOT NULL, chapter_id TEXT NOT NULL,
              current_question INTEGER NOT NULL DEFAULT 0, correct_answers INTEGER NOT NULL DEFAULT 0,
              coaching_rounds INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'diagnostic',
              started_at TEXT NOT NULL, completed_at TEXT, questions_json TEXT NOT NULL DEFAULT '',
              tutor_json TEXT);
            INSERT INTO users VALUES ('u', 'legacy@example.com', 'hash', 'now');
            INSERT INTO mastery_sessions
              (id, owner_id, grade, subject_id, chapter_id, started_at)
              VALUES ('s', 'u', 8, 'math', 'fractions', 'now');
        ''')
    initialize(path)
    with connection(path) as db:
        row = db.execute("SELECT catalog_version FROM mastery_sessions WHERE id = 's'").fetchone()
    assert row['catalog_version'] == CATALOG_VERSION


def test_saved_session_keeps_creation_catalog_version_after_catalog_changes(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post('/v1/mastery/diagnostics', headers=headers,
                              json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        from app import main
        monkeypatch.setattr(main, 'CATALOG_VERSION', 'foundation-next')
        assert client.get('/v1/catalog?grade=8', headers=headers).json()['version'] == 'foundation-next'
        saved = client.get(f"/v1/mastery/sessions/{started['id']}", headers=headers).json()
        assert saved['catalog_version'] == 'open-oer-foundation-2026-09'
    finally:
        client.__exit__(None, None, None)


def test_tutor_generation_failure_does_not_commit_an_unrecoverable_transition(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post("/v1/mastery/diagnostics", headers=headers,
                              json={"grade": 8, "subject_id": "math", "chapter_id": "fractions"}).json()
        from app.tutor_provider import DeterministicTutorProvider
        import pytest

        def fail(*args, **kwargs):
            raise RuntimeError("provider unavailable")

        monkeypatch.setattr(DeterministicTutorProvider, "explain", fail)
        path = f"/v1/mastery/sessions/{started['id']}"
        with pytest.raises(RuntimeError, match="provider unavailable"):
            client.post(path + "/diagnostic-answer", headers=headers, json={"selected_option": "1/2"})
        recovered = client.get(path, headers=headers).json()
        assert recovered["status"] == "diagnostic"
        assert recovered["question"]["ordinal"] == 1
        assert client.get("/v1/progress/dashboard", headers=headers).json()["chapters"][0]["attempts"] == 0
    finally:
        client.__exit__(None, None, None)
