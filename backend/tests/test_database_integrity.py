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
