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
"""


def initialize(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)


@contextmanager
def connection(path: Path) -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def json_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_json(value: str) -> object:
    return json.loads(value)
