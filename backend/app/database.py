from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  original_name TEXT NOT NULL, media_type TEXT NOT NULL, stored_path TEXT NOT NULL,
  extracted_text TEXT NOT NULL, chapters_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS google_accounts (
  subject TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS learner_preferences (
  owner_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  interests_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quizzes (
  id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, title TEXT NOT NULL,
  created_at TEXT NOT NULL, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS questions (
  id TEXT PRIMARY KEY, quiz_id TEXT NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL, prompt TEXT NOT NULL, options_json TEXT NOT NULL,
  correct_option TEXT NOT NULL, explanation TEXT NOT NULL, source_reference TEXT NOT NULL,
  answered_option TEXT, answered_at TEXT, UNIQUE(quiz_id, ordinal)
);
CREATE TABLE IF NOT EXISTS pending_file_deletions (
  stored_path TEXT PRIMARY KEY, attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT
);
CREATE TABLE IF NOT EXISTS quiz_creation_requests (
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  request_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
  quiz_id TEXT NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
  PRIMARY KEY(owner_id, request_id)
);
CREATE TABLE IF NOT EXISTS mastery_sessions (
  id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  grade INTEGER NOT NULL, subject_id TEXT NOT NULL, chapter_id TEXT NOT NULL,
  current_question INTEGER NOT NULL DEFAULT 0, correct_answers INTEGER NOT NULL DEFAULT 0,
  coaching_rounds INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'diagnostic',
  started_at TEXT NOT NULL, completed_at TEXT, questions_json TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS mastery_attempts (
  id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES mastery_sessions(id) ON DELETE CASCADE,
  phase TEXT NOT NULL, prompt TEXT NOT NULL, response TEXT NOT NULL,
  correct INTEGER NOT NULL, concept TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS study_presence (
  owner_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  session_id TEXT NOT NULL REFERENCES mastery_sessions(id) ON DELETE CASCADE,
  seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS study_time_intervals (
  id INTEGER PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES mastery_sessions(id) ON DELETE CASCADE,
  started_at TEXT NOT NULL, ended_at TEXT NOT NULL, seconds REAL NOT NULL CHECK(seconds > 0)
);
CREATE INDEX IF NOT EXISTS study_time_session_idx ON study_time_intervals(session_id);
CREATE INDEX IF NOT EXISTS mastery_sessions_owner_idx
  ON mastery_sessions(owner_id, subject_id, chapter_id, started_at);
CREATE INDEX IF NOT EXISTS mastery_attempts_session_idx
  ON mastery_attempts(session_id, created_at);
"""


def initialize(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
        quiz_columns = {row[1] for row in connection.execute("PRAGMA table_info(quizzes)")}
        if 'source_ranges_json' not in quiz_columns:
            connection.execute('ALTER TABLE quizzes ADD COLUMN source_ranges_json TEXT')
        if 'difficulty' not in quiz_columns:
            connection.execute('ALTER TABLE quizzes ADD COLUMN difficulty TEXT')
        if 'question_type' not in quiz_columns:
            connection.execute("ALTER TABLE quizzes ADD COLUMN question_type TEXT NOT NULL DEFAULT 'multiple_choice'")
        question_columns = {row[1] for row in connection.execute("PRAGMA table_info(questions)")}
        if 'question_type' not in question_columns:
            connection.execute("ALTER TABLE questions ADD COLUMN question_type TEXT NOT NULL DEFAULT 'multiple_choice'")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(mastery_sessions)")}
        if "questions_json" not in columns:
            connection.execute("ALTER TABLE mastery_sessions ADD COLUMN questions_json TEXT NOT NULL DEFAULT ''")
        if "tutor_json" not in columns:
            connection.execute("ALTER TABLE mastery_sessions ADD COLUMN tutor_json TEXT")
        attempt_columns = {row[1] for row in connection.execute("PRAGMA table_info(mastery_attempts)")}
        if "assessment_json" not in attempt_columns:
            connection.execute("ALTER TABLE mastery_attempts ADD COLUMN assessment_json TEXT")


@contextmanager
def connection(path: Path) -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        # This setting is connection-local, not persisted by schema initialization.
        db.execute("PRAGMA foreign_keys = ON")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def json_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_json(value: str) -> object:
    return json.loads(value)
