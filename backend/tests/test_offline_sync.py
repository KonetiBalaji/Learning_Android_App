import copy

import pytest

from study.documents import retrieve
from study.quizzes import generate_local
from test_learning_flow import account, client, upload


def prepared(client, owner, kind="multiple_choice"):
    doc = upload(client, owner)
    bundle = client.get(f'/documents/{doc["id"]}/offline-bundle', headers=owner).json()
    selection = {"section_ids": [doc["sections"][0]["id"]]}
    selected = retrieve({**bundle["document"], "passages": bundle["passages"]}, selection)
    questions = generate_local(selected, 2, kind, "easy")
    body = {"local_id": "local-session-001", "source_fingerprint": bundle["source_fingerprint"], "selection": selection,
            "questions": [{k: q[k] for k in ("source_id", "prompt", "choices", "type")} | {"selected": q["answer"] if i == 0 else (q["answer"] + 1) % len(q["choices"])} for i, q in enumerate(questions)]}
    return doc, body


@pytest.mark.parametrize("kind", ["multiple_choice", "true_false", "yes_no"])
def test_import_is_validated_owned_idempotent_and_in_authoritative_progress(client, kind):
    owner = account(client, "offline-import")
    other = account(client, "offline-other")
    doc, body = prepared(client, owner, kind)
    path = f'/documents/{doc["id"]}/offline-attempts'
    status_path = f'/documents/{doc["id"]}/offline-status'
    assert client.get(status_path, headers=other).status_code == 404
    assert client.get(status_path, headers=owner).json()["source_fingerprint"] == body["source_fingerprint"]
    assert client.post(path, headers=other, json=body).status_code == 404
    assert client.post(path, json=body).status_code == 401
    response = client.post(path, headers=owner, json=body)
    assert response.status_code == 201, response.text
    quiz = response.json()
    assert quiz["complete"] and quiz["mode"] == "local_practice"
    assert "validated" in quiz["notice"]
    assert client.post(path, headers=owner, json=body).json() == quiz
    changed = copy.deepcopy(body)
    changed["questions"][0]["selected"] = (changed["questions"][0]["selected"] + 1) % len(changed["questions"][0]["choices"])
    assert client.post(path, headers=owner, json=changed).status_code == 409
    results = client.get(f'/quizzes/{quiz["id"]}/results', headers=owner).json()
    assert results["correct"] == 1 and results["total"] == 2 and results["accuracy"] == 50
    progress = client.get("/progress", headers=owner).json()
    assert progress["quizzes_completed"] == 1 and progress["questions_answered"] == 2
    assert client.get(f'/documents/{doc["id"]}', headers=owner).json()["source_locked"]
    assert client.post(f'/quizzes/{quiz["id"]}/flashcards', headers=owner, json={}).status_code == 201
    assert client.delete(f'/documents/{doc["id"]}', headers=owner).status_code == 204
    assert client.get(f'/quizzes/{quiz["id"]}', headers=owner).status_code == 404
    assert client.post(path, headers=owner, json=body).status_code == 404
    assert client.get(status_path, headers=owner).status_code == 404


@pytest.mark.parametrize("tamper", ["source", "scope", "prompt", "distractor", "duplicate", "score", "answer-key", "stale"])
def test_malformed_or_stale_offline_work_never_creates_progress(client, tamper):
    owner = account(client)
    doc, body = prepared(client, owner)
    question = body["questions"][0]
    if tamper == "source":
        question["source_id"] = "invented"
    elif tamper == "scope":
        body["selection"]["section_ids"] = [doc["sections"][1]["id"]]
    elif tamper == "prompt":
        question["prompt"] += " invented claim"
    elif tamper == "distractor":
        question["choices"][0] = "outside-the-material"
    elif tamper == "duplicate":
        body["questions"][1] = copy.deepcopy(question)
    elif tamper == "score":
        body["accuracy"] = 100
    elif tamper == "answer-key":
        question["answer"] = question["selected"]
    else:
        body["source_fingerprint"] = "0" * 64
    response = client.post(f'/documents/{doc["id"]}/offline-attempts', headers=owner, json=body)
    assert response.status_code == (409 if tamper == "stale" else 422), response.text
    assert client.get("/progress", headers=owner).json()["quizzes_completed"] == 0


def test_binary_changes_and_out_of_range_answers_are_rejected(client):
    owner = account(client)
    doc, body = prepared(client, owner, "yes_no")
    path = f'/documents/{doc["id"]}/offline-attempts'
    altered = copy.deepcopy(body)
    altered["questions"][0]["selected"] = 3
    assert client.post(path, headers=owner, json=altered).status_code == 422
    body["questions"][0]["prompt"] = 'Does this exactly match the source passage?\n“An invented sentence.”'
    assert client.post(path, headers=owner, json=body).status_code == 422
    assert client.post(path, headers={**owner, "Content-Length": str(17 * 1024 * 1024)}, content=b"{}").status_code == 413


def test_linked_records_roll_back_together(client, monkeypatch):
    owner = account(client)
    doc, body = prepared(client, owner)
    store = client.app.state.store
    encode = store.encode
    def fail_source_lock(value):
        if value.get("source_locked"):
            raise ValueError("simulated write failure")
        return encode(value)
    monkeypatch.setattr(store, "encode", fail_source_lock)
    with pytest.raises(ValueError, match="simulated write"):
        client.post(f'/documents/{doc["id"]}/offline-attempts', headers=owner, json=body)
    assert store.db.execute("SELECT COUNT(*) FROM records WHERE kind='quiz'").fetchone()[0] == 0
    assert not client.get(f'/documents/{doc["id"]}', headers=owner).json()["source_locked"]


def test_changed_or_uncertain_source_blocks_offline_import(client):
    owner = account(client)
    doc, body = prepared(client, owner)
    store = client.app.state.store
    user = client.get("/account", headers=owner).json()["owner_id"]
    source = store.get(doc["id"], user, "document")
    source["passages"][0]["text"] += " Corrected material."
    store.save(doc["id"], user, "document", doc["id"], source["created"], source)
    status = client.get(f'/documents/{doc["id"]}/offline-status', headers=owner).json()
    assert status["source_fingerprint"] != body["source_fingerprint"]
    path = f'/documents/{doc["id"]}/offline-attempts'
    assert client.post(path, headers=owner, json=body).status_code == 409
    body["source_fingerprint"] = status["source_fingerprint"]
    source["processing_state"] = "needs_review"
    store.save(doc["id"], user, "document", doc["id"], source["created"], source)
    assert client.post(path, headers=owner, json=body).status_code == 409
    assert client.get("/progress", headers=owner).json()["quizzes_completed"] == 0
