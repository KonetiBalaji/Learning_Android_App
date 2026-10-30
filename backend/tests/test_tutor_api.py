from test_learning_flow import account, client, upload
from test_semantic_search import FixtureEncoder
from study.document_tutor import NO_SUPPORT


def test_tutor_owned_scoped_encrypted_idempotent_and_deleted(client, monkeypatch):
    monkeypatch.setattr("study.semantic.encoder", lambda: FixtureEncoder())
    owner = account(client, "tutor-owner")
    other = account(client, "tutor-other")
    doc = upload(client, owner)
    path = f'/documents/{doc["id"]}/tutor'
    body = {"question": "cell power factory", "request_id": "question-001"}
    assert client.post(path, headers=other, json=body).status_code == 404
    assert client.get(path, headers=other).status_code == 404
    result = client.post(path, headers=owner, json=body)
    assert result.status_code == 201, result.text
    turn = result.json()
    assert turn["mode"] == "source_excerpt"
    assert "Mitochondria" in turn["answer"]
    assert turn["citations"][0]["source_id"] == "p0"
    assert not any(k.startswith("_") for k in turn)
    assert client.post(path, headers=owner, json=body).json() == turn
    assert client.post(path, headers=owner, json={**body, "question": "different question"}).status_code == 409
    excluded = client.post(path, headers=owner, json={**body, "request_id": "question-002",
        "selection": {"section_ids": [doc["sections"][1]["id"]]}}).json()
    assert excluded["answer"] == NO_SUPPORT and excluded["citations"] == []
    assert len(client.get(path, headers=owner).json()) == 2
    store = client.app.state.store
    rows = store.db.execute("SELECT payload FROM records WHERE kind='tutor'").fetchall()
    assert len(rows) == 2 and all(b"Mitochondria" not in row[0] for row in rows)
    assert client.delete(f'/documents/{doc["id"]}', headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
    assert store.db.execute("SELECT COUNT(*) FROM records WHERE kind='tutor'").fetchone()[0] == 0


def test_tutor_rejects_stale_inference_and_invalid_scope(client, monkeypatch):
    monkeypatch.setattr("study.semantic.encoder", lambda: FixtureEncoder())
    owner = account(client, "tutor-revision")
    doc = upload(client, owner)
    path = f'/documents/{doc["id"]}/tutor'
    body = {"question": "cell power factory", "request_id": "question-001"}
    assert client.post(path, headers=owner, json={**body, "question": "  "}).status_code == 422
    assert client.post(path, headers=owner, json={**body, "selection": {"topic": "energy"}}).status_code == 422
    assert client.post(path, headers=owner, json={**body, "selection": {"section_ids": ["missing"]}}).status_code == 422
    store = client.app.state.store

    def mutate_source(*args, **kwargs):
        with store.lock:
            row = store.db.execute("SELECT owner FROM records WHERE id=?", (doc["id"],)).fetchone()
            value = store.get(doc["id"], row[0], "document")
            value["passages"][0]["text"] += " Changed source."
            store.save(doc["id"], row[0], "document", doc["id"], value["created"], value)
        return {"answer": "discard this stale response"}

    monkeypatch.setattr("study.api.tutor_reply", mutate_source)
    assert client.post(path, headers=owner, json=body).status_code == 409
    assert client.get(path, headers=owner).json() == []


def test_tutor_replay_and_history_reject_old_sources(client, monkeypatch):
    monkeypatch.setattr("study.semantic.encoder", lambda: FixtureEncoder())
    owner = account(client, "tutor-stale")
    doc = upload(client, owner)
    path = f'/documents/{doc["id"]}/tutor'
    body = {"question": "cell power factory", "request_id": "question-001"}
    assert client.post(path, headers=owner, json=body).status_code == 201
    store = client.app.state.store
    with store.lock:
        row = store.db.execute("SELECT owner FROM records WHERE id=?", (doc["id"],)).fetchone()
        value = store.get(doc["id"], row[0], "document")
        value["passages"][0]["text"] += " Source correction."
        store.save(doc["id"], row[0], "document", doc["id"], value["created"], value)
    assert client.post(path, headers=owner, json=body).status_code == 409
    assert client.get(path, headers=owner).json() == []
    with store.lock:
        value["processing_state"] = "needs_review"
        store.save(doc["id"], row[0], "document", doc["id"], value["created"], value)
    assert client.post(path, headers=owner, json={**body, "request_id": "question-002"}).status_code == 409
