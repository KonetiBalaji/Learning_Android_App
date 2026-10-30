import json
import os
import sqlite3
import threading
from pathlib import Path

from cryptography.fernet import Fernet


class Store:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        key_path = directory / "storage.key"
        if not key_path.exists():
            if (directory / "study.sqlite3").exists():
                raise RuntimeError("The storage encryption key is missing. Restore storage.key before opening the existing database.")
            with key_path.open("xb") as file:
                file.write(Fernet.generate_key())
            os.chmod(key_path, 0o600)
        self.cipher = Fernet(key_path.read_bytes())
        self.lock = threading.RLock()
        self.db = sqlite3.connect(directory / "study.sqlite3", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT UNIQUE, salt BLOB, password BLOB);
            CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, owner TEXT REFERENCES users(id) ON DELETE CASCADE, expires REAL);
            CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, owner TEXT REFERENCES users(id) ON DELETE CASCADE,
                kind TEXT, document TEXT, created REAL, payload BLOB);
            CREATE INDEX IF NOT EXISTS owner_document_records ON records(owner, kind, document, created);
        """)
        self.db.commit()

    def encode(self, value):
        return self.cipher.encrypt(json.dumps(value).encode())

    def decode(self, value):
        return json.loads(self.cipher.decrypt(value))

    def save(self, identifier, owner, kind, document, created, value):
        self.db.execute("INSERT OR REPLACE INTO records VALUES (?,?,?,?,?,?)",
                        (identifier, owner, kind, document, created, self.encode(value)))
        self.db.commit()

    def get(self, identifier, owner, kind):
        row = self.db.execute("SELECT payload FROM records WHERE id=? AND owner=? AND kind=?", (identifier, owner, kind)).fetchone()
        return self.decode(row[0]) if row else None

    def all(self, owner, kind):
        return [self.decode(r[0]) for r in self.db.execute(
            "SELECT payload FROM records WHERE owner=? AND kind=? ORDER BY created DESC", (owner, kind)).fetchall()]

    def for_document(self, owner, kind, document, limit=50):
        return [self.decode(row[0]) for row in self.db.execute(
            "SELECT payload FROM records WHERE owner=? AND kind=? AND document=? ORDER BY created DESC LIMIT ?",
            (owner, kind, document, limit)).fetchall()]
