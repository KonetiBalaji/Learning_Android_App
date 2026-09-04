import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.database import connection, initialize
from app.mastery_service import FRACTION_DIAGNOSTIC, serialize_diagnostic_bank


def test_concurrent_workers_serialize_legacy_schema_migrations(tmp_path):
    path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE quizzes (id TEXT PRIMARY KEY)")

    with ThreadPoolExecutor(max_workers=8) as workers:
        list(workers.map(lambda _: initialize(path), range(8)))

    with sqlite3.connect(path) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(quizzes)")}
        assert {"source_ranges_json", "difficulty", "question_type"} <= columns


def test_legacy_premature_mastery_is_reopened_once_with_an_audit_record(tmp_path):
    path = tmp_path / "legacy.sqlite"
    initialize(path)
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?)",
            ("learner", "learner@example.com", "hash", "2026-09-01T00:00:00Z"),
        )
        db.execute(
            """INSERT INTO mastery_sessions
               (id, owner_id, grade, subject_id, chapter_id, current_question,
                correct_answers, status, started_at, completed_at, questions_json)
               VALUES (?, ?, 8, 'math', 'fractions', 1, 1, 'mastered', ?, ?, ?)""",
            ("premature", "learner", "2026-09-01T00:00:00Z", "2026-09-01T00:05:00Z",
             serialize_diagnostic_bank(FRACTION_DIAGNOSTIC)),
        )

    initialize(path)
    initialize(path)

    with sqlite3.connect(path) as db:
        assert db.execute(
            "SELECT status, completed_at, current_question FROM mastery_sessions WHERE id = 'premature'"
        ).fetchone() == ("diagnostic", None, 1)
        assert db.execute(
            """SELECT repair_kind, previous_status, previous_completed_at
               FROM mastery_session_repairs WHERE session_id = 'premature'"""
        ).fetchall() == [("premature-mastery-v1", "mastered", "2026-09-01T00:05:00Z")]

    with connection(path) as db:
        db.execute("DELETE FROM users WHERE id = 'learner'")
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM mastery_session_repairs").fetchone()[0] == 0


def test_completed_mastery_is_not_repaired(tmp_path):
    path = tmp_path / "database.sqlite"
    initialize(path)
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?)",
            ("learner", "learner@example.com", "hash", "2026-09-01T00:00:00Z"),
        )
        db.execute(
            """INSERT INTO mastery_sessions
               (id, owner_id, grade, subject_id, chapter_id, current_question,
                correct_answers, status, started_at, completed_at, questions_json)
               VALUES (?, ?, 8, 'math', 'fractions', ?, ?, 'mastered', ?, ?, ?)""",
            ("valid", "learner", len(FRACTION_DIAGNOSTIC), len(FRACTION_DIAGNOSTIC),
             "2026-09-01T00:00:00Z", "2026-09-01T00:05:00Z",
             serialize_diagnostic_bank(FRACTION_DIAGNOSTIC)),
        )

    initialize(path)

    with sqlite3.connect(path) as db:
        assert db.execute(
            "SELECT status, completed_at FROM mastery_sessions WHERE id = 'valid'"
        ).fetchone() == ("mastered", "2026-09-01T00:05:00Z")
        assert db.execute("SELECT count(*) FROM mastery_session_repairs").fetchone()[0] == 0


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
