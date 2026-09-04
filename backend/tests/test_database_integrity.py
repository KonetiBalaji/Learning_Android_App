import sqlite3

import pytest

from app.database import connection, initialize


def test_runtime_connections_enforce_foreign_keys(tmp_path):
    path = tmp_path / "database.sqlite"
    initialize(path)
    for _ in range(2):
        with connection(path) as db:
            assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO mastery_sessions (id, owner_id, grade, subject_id, chapter_id, started_at) VALUES (?, ?, ?, ?, ?, ?)",
                    ("orphan", "missing-user", 6, "math", "fractions", "2026-09-02"),
                )


def test_failed_transaction_rolls_back(tmp_path):
    path = tmp_path / "database.sqlite"
    initialize(path)
    with pytest.raises(RuntimeError):
        with connection(path) as db:
            db.execute("INSERT INTO users VALUES (?, ?, ?, ?)", ("u", "u@example.com", "hash", "2026-09-02"))
            raise RuntimeError("abort")
    with connection(path) as db:
        assert db.execute("SELECT count(*) FROM users").fetchone()[0] == 0


def test_question_attribution_migration_preserves_legacy_rows(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('''CREATE TABLE questions (
            id TEXT PRIMARY KEY, quiz_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
            prompt TEXT NOT NULL, options_json TEXT NOT NULL, correct_option TEXT NOT NULL,
            explanation TEXT NOT NULL, source_reference TEXT NOT NULL,
            answered_option TEXT, answered_at TEXT, question_type TEXT NOT NULL DEFAULT 'multiple_choice')''')
        db.execute("""INSERT INTO questions
            (id, quiz_id, ordinal, prompt, options_json, correct_option, explanation, source_reference)
            VALUES ('legacy', 'quiz', 1, 'Prompt', '[\"A\",\"B\"]', 'A', 'Why', 'Old source')""")
    initialize(path)
    with sqlite3.connect(path) as db:
        columns = {row[1] for row in db.execute('PRAGMA table_info(questions)')}
        assert {'chapter_id', 'concept'} <= columns
        assert db.execute("SELECT id, chapter_id, concept FROM questions WHERE id = 'legacy'").fetchone() == (
            'legacy', None, None)
