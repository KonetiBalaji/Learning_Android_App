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
