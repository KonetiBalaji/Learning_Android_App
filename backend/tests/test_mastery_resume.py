from fastapi.testclient import TestClient

from test_mastery_loop import registered_client


def test_resume_tracks_phases_without_answer_leakage_or_provider_calls(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post("/v1/mastery/diagnostics", headers=headers,
                              json={"grade": 8, "subject_id": "math", "chapter_id": "fractions"}).json()
        path = f"/v1/mastery/sessions/{started['id']}"
        initial = client.get(path, headers=headers).json()
        assert initial["status"] == "diagnostic"
        assert initial["grade"] == 8
        assert initial["question"]["ordinal"] == 1
        assert "correct_option" not in initial["question"]
        assert initial["tutor"] is None
        outcome = client.post(path + "/diagnostic-answer", headers=headers, json={"selected_option": "1/2"}).json()
        coaching = client.get(path, headers=headers).json()
        assert coaching["status"] == "tutor"
        assert coaching["tutor"] == outcome["tutor"]
        assert coaching["selected_option"] == "1/2"

        # Reads recover committed state from the database even through another app lifecycle.
        from app.main import app
        with TestClient(app) as restarted:
            assert restarted.get(path, headers=headers).json() == coaching

        assert client.post(path + "/practice", headers=headers, json={"response": "7/8"}).status_code == 200
        assert client.get(path, headers=headers).json()["status"] == "practice"
        client.post(path + "/practice", headers=headers, json={"response": "6/8"})
        assert client.get(path, headers=headers).json()["status"] == "rewrite"
        client.post(path + "/rewrite", headers=headers, json={"response": "Because it does."})
        retry = client.get(path, headers=headers).json()
        assert retry["status"] == "tutor"
        assert "Explain the key idea" in retry["tutor"]["explanation"]
        client.post(path + "/practice", headers=headers, json={"response": "6/8"})
        client.post(path + "/rewrite", headers=headers,
                    json={"response": "We add the numerator parts with the same denominator to make one whole."})
        resumed = client.get(path, headers=headers).json()
        assert resumed["status"] == "diagnostic"
        assert resumed["question"]["ordinal"] == 2
        assert resumed["tutor"] is None
        assert resumed["mastery_score"] == 1 / 3
        for answer in ("3/6", "4/8"):
            client.post(path + "/diagnostic-answer", headers=headers, json={"selected_option": answer})
        mastered = client.get(path, headers=headers).json()
        assert mastered["status"] == "mastered"
        assert mastered["question"] is None
        assert mastered["mastery_score"] == 1
        other_token = client.post("/v1/auth/register", json={"email": "other-resume@example.com", "password": "long-enough-password"}).json()["access_token"]
        assert client.get(path, headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
        assert client.get(path).status_code == 401
    finally:
        client.__exit__(None, None, None)


def test_tutor_generation_failure_does_not_commit_an_unrecoverable_transition(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post("/v1/mastery/diagnostics", headers=headers,
                              json={"grade": 8, "subject_id": "math", "chapter_id": "fractions"}).json()
        from app.tutor_provider import DeterministicTutorProvider
        import pytest

        def fail(*args, **kwargs):
            raise RuntimeError("provider unavailable")

        monkeypatch.setattr(DeterministicTutorProvider, "explain", fail)
        path = f"/v1/mastery/sessions/{started['id']}"
        with pytest.raises(RuntimeError, match="provider unavailable"):
            client.post(path + "/diagnostic-answer", headers=headers, json={"selected_option": "1/2"})
        recovered = client.get(path, headers=headers).json()
        assert recovered["status"] == "diagnostic"
        assert recovered["question"]["ordinal"] == 1
        assert client.get("/v1/progress/dashboard", headers=headers).json()["chapters"][0]["attempts"] == 0
    finally:
        client.__exit__(None, None, None)
