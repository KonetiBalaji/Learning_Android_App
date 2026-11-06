import time

import pytest

from study.storage import DOCUMENT_RETENTION_SECONDS
from test_learning_flow import account, client, upload
from test_offline_sync import prepared
from test_semantic_search import FixtureEncoder


@pytest.mark.parametrize("removal", ["document", "retention", "account"])
def test_all_study_records_follow_owner_and_document_lifecycle(client, monkeypatch, removal):
    monkeypatch.setattr("study.semantic.encoder", lambda: FixtureEncoder())
    owner = account(client, "lifecycle-owner")
    outsider = account(client, "lifecycle-other")
    document, attempt = prepared(client, owner)
    doc_id = document["id"]
    root = f"/documents/{doc_id}"
    other_id = upload(client, outsider)["id"]
    query = {"query": "cell power factory"}
    assert client.post(root + "/search", json=query, headers=owner).status_code == 200
    assert client.post(root + "/tutor", json={"question": query["query"], "request_id": "lifecycle-turn"}, headers=owner).status_code == 201
    imported = client.post(root + "/offline-attempts", json=attempt, headers=owner)
    assert imported.status_code == 201
    quiz = f'/quizzes/{imported.json()["id"]}'
    cards = client.post(quiz + "/flashcards", json={}, headers=owner)
    assert cards.status_code == 201 and cards.json()
    for path in (root, root + "/tutor", root + "/offline-bundle", root + "/offline-status", quiz, quiz + "/results"):
        assert client.get(path, headers=outsider).status_code == 404
    assert client.get("/flashcards", headers=outsider).json() == []
    assert client.post(root + "/search", json=query, headers=outsider).status_code == 404
    assert client.post(root + "/offline-attempts", json=attempt, headers=outsider).status_code == 404
    assert client.delete(root, headers=outsider).status_code == 404

    store = client.app.state.store
    with store.lock:
        kinds = {row[0] for row in store.db.execute("SELECT kind FROM records WHERE document=? OR id=?", (doc_id, doc_id))}
    assert kinds == {"document", "embedding", "tutor", "quiz", "flashcard"}
    if removal == "document":
        assert client.delete(root, headers=owner).status_code == 204
    elif removal == "retention":
        now = time.time()
        with store.lock, store.db:
            store.db.execute("UPDATE records SET created=? WHERE id=?", (now - DOCUMENT_RETENTION_SECONDS, doc_id))
        store.purge_expired(now)
    else:
        assert client.delete("/account", headers=owner).status_code == 204
        assert client.get("/account", headers=owner).status_code == 401
    with store.lock:
        assert not store.db.execute("SELECT id FROM records WHERE document=? OR id=?", (doc_id, doc_id)).fetchall()
    assert client.get(f"/documents/{other_id}", headers=outsider).status_code == 200


def test_encrypted_backup_restores_email_login_and_owner_data(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import closing

    from cryptography.fernet import Fernet
    from fastapi.testclient import TestClient
    from study.api import create_app

    original_key = tmp_path / "mounted.key"
    original_key.write_bytes(Fernet.generate_key())
    monkeypatch.setenv("STUDY_STORAGE_KEY_FILE", str(original_key))
    credentials = {"username": "backup-test@example.test", "password": "disposable-backup-password"}
    source = tmp_path / "source"
    restored = tmp_path / "restored"
    restored.mkdir()

    with TestClient(create_app(source)) as original:
        identity = original.post("/auth/register", json=credentials)
        assert identity.status_code == 200
        owner = {"Authorization": "Bearer " + identity.json()["token"]}
        document = original.post(
            "/documents", headers=owner,
            files={"file": ("recovery.txt", b"Mitochondria produce energy. Ribosomes assemble proteins.")},
        )
        assert document.status_code == 201
        document_path = "/documents/" + document.json()["id"]
        with closing(sqlite3.connect(restored / "study.sqlite3")) as backup:
            original.app.state.store.db.backup(backup)
            assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert backup.execute("PRAGMA foreign_key_check").fetchall() == []
            payload = backup.execute("SELECT payload FROM records WHERE kind='document'").fetchone()[0]
            assert b"Mitochondria" not in payload

    wrong_key = tmp_path / "wrong.key"
    wrong_key.write_bytes(Fernet.generate_key())
    monkeypatch.setenv("STUDY_STORAGE_KEY_FILE", str(wrong_key))
    with pytest.raises(RuntimeError, match="does not match"):
        create_app(restored)

    monkeypatch.setenv("STUDY_STORAGE_KEY_FILE", str(original_key))
    with TestClient(create_app(restored)) as recovery:
        signed_in = recovery.post("/auth/login", json=credentials)
        assert signed_in.status_code == 200
        assert signed_in.json()["owner_id"] == identity.json()["owner_id"]
        auth = {"Authorization": "Bearer " + signed_in.json()["token"]}
        assert recovery.get(document_path, headers=auth).json()["filename"] == "recovery.txt"
        outsider = account(recovery, "restore-outsider")
        assert recovery.get(document_path, headers=outsider).status_code == 404
