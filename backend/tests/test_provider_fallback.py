import httpx
import pytest
from fastapi.testclient import TestClient

from study.api import create_app
from study.provider import OpenAIProvider
from test_learning_flow import account, upload
from test_provider import completed, QUESTION


@pytest.mark.parametrize("failure", [401, 429, 503, "timeout"])
def test_unavailable_provider_falls_back_to_scoped_easy_practice(tmp_path, monkeypatch, failure):
    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("sensitive diagnostic", request=request)
        return httpx.Response(failure, text="private provider body")

    provider = OpenAIProvider("not-a-real-key", "fixture-model", httpx.MockTransport(respond))
    monkeypatch.setattr("study.api.configured_provider", lambda: provider)
    with TestClient(create_app(tmp_path)) as client:
        owner = account(client)
        doc = upload(client, owner)
        section = doc["sections"][1]["id"]
        response = client.post(f'/documents/{doc["id"]}/quizzes', headers=owner,
            json={"count": 2, "difficulty": "hard", "selection": {"section_ids": [section]}})
        assert response.status_code == 201, response.text
        quiz = response.json()
        assert quiz["mode"] == "local_practice"
        assert "Easy difficulty" in quiz["notice"]
        assert quiz["question"]["difficulty"] == "easy"
        assert quiz["question"]["section_id"] == section
        assert "private" not in response.text and "sensitive" not in response.text
        path = f'/quizzes/{quiz["id"]}'
        assert client.get(path, headers=owner).json()["notice"] == quiz["notice"]
        store = client.app.state.store
        user = store.db.execute("SELECT id FROM users").fetchone()[0]
        saved = store.get(quiz["id"], user, "quiz")
        assert all(q["section_id"] == section and q["difficulty"] == "easy" for q in saved["questions"])
        for index, question in enumerate(saved["questions"]):
            answer = (question["answer"] + 1) % len(question["choices"])
            assert client.post(path + "/answers", headers=owner, json={"question_id": question["id"], "choice": answer}).status_code == 200
            assert client.post(path + "/next", headers=owner, json={"expected_index": index}).status_code == 200
        assert client.get(path + "/results", headers=owner).json()["notice"] == quiz["notice"]
        assert client.post(path + "/retry", headers=owner).json()["notice"] == quiz["notice"]


@pytest.mark.parametrize("failure", ["malformed", "bad-source", "review-rejected"])
def test_invalid_provider_output_never_becomes_fallback(tmp_path, monkeypatch, failure):
    question = {**QUESTION, "quote": "Mitochondria produce usable energy through cellular respiration inside living cells."}
    replies = iter([completed({"questions": [{**question, "source_id": "invented"}]})] if failure == "bad-source" else
                   [completed({"questions": [question]}), completed({"approved": [False]})])
    calls = []
    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"unexpected": "invalid"} if failure == "malformed" else next(replies))
    provider = OpenAIProvider("not-a-real-key", "fixture-model", httpx.MockTransport(respond))
    monkeypatch.setattr("study.api.configured_provider", lambda: provider)
    with TestClient(create_app(tmp_path)) as client:
        owner = account(client)
        doc = upload(client, owner)
        response = client.post(f'/documents/{doc["id"]}/quizzes', headers=owner, json={"count": 1})
        assert response.status_code == 422
        assert len(calls) == (2 if failure == "review-rejected" else 1)
        assert client.app.state.store.db.execute("SELECT COUNT(*) FROM records WHERE kind='quiz'").fetchone()[0] == 0
