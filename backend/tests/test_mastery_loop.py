from pathlib import Path

from fastapi.testclient import TestClient


def registered_client(monkeypatch, tmp_path: Path) -> tuple[TestClient, dict[str, str]]:
    monkeypatch.setenv("LEARNING_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("LEARNING_JWT_SECRET", "test-secret-that-is-long-enough-32")
    from app.main import app

    client = TestClient(app)
    client.__enter__()
    token = client.post(
        "/v1/auth/register",
        json={"email": f"student-{tmp_path.name}@example.com", "password": "long-enough-password"},
    ).json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_wrong_answer_routes_through_tutor_practice_rewrite_and_mastery(monkeypatch, tmp_path: Path) -> None:
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post(
            "/v1/mastery/diagnostics",
            json={"grade": 6, "subject_id": "math", "chapter_id": "fractions"},
            headers=headers,
        )
        assert started.status_code == 201, started.text
        session = started.json()
        outcome = client.post(
            f"/v1/mastery/sessions/{session['id']}/diagnostic-answer",
            json={"selected_option": "1/2"}, headers=headers,
        )
        assert outcome.status_code == 200, outcome.text
        assert outcome.json()["next_action"] == "tutor"
        assert outcome.json()["tutor"]["worked_example"]

        practice = client.post(
            f"/v1/mastery/sessions/{session['id']}/practice",
            json={"response": "6/8"}, headers=headers,
        )
        assert practice.json()["next_action"] == "rewrite"
        rewrite = client.post(
            f"/v1/mastery/sessions/{session['id']}/rewrite",
            json={"response": "The denominator stays the same and we add the numerator parts to make 4/4, one whole."},
            headers=headers,
        )
        assert rewrite.status_code == 200, rewrite.text
        assert rewrite.json()["mastery_achieved"] is True
        assert rewrite.json()["next_chapter_unlocked"] is True
        assert rewrite.json()["mastery_score"] >= 0.85

        dashboard = client.get("/v1/progress/dashboard", headers=headers)
        assert dashboard.status_code == 200, dashboard.text
        assert "Adding like fractions" in dashboard.json()["weak_areas"]
        assert dashboard.json()["chapters"][0]["status"] == "mastered"
        assert dashboard.json()["chapters"][0]["mastery"] >= 0.85
    finally:
        client.__exit__(None, None, None)


def test_diagnostic_validation_and_owner_scope(monkeypatch, tmp_path: Path) -> None:
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        unsupported = client.post(
            "/v1/mastery/diagnostics",
            json={"grade": 6, "subject_id": "science", "chapter_id": "cells"}, headers=headers,
        )
        assert unsupported.status_code == 422
        started = client.post(
            "/v1/mastery/diagnostics",
            json={"grade": 6, "subject_id": "math", "chapter_id": "fractions"}, headers=headers,
        ).json()
        other = client.post(
            "/v1/auth/register",
            json={"email": "other@example.com", "password": "long-enough-password"},
        ).json()["access_token"]
        forbidden = client.post(
            f"/v1/mastery/sessions/{started['id']}/diagnostic-answer",
            json={"selected_option": "1"}, headers={"Authorization": f"Bearer {other}"},
        )
        assert forbidden.status_code == 404
        invalid = client.post(
            f"/v1/mastery/sessions/{started['id']}/diagnostic-answer",
            json={"selected_option": "not an option"}, headers=headers,
        )
        assert invalid.status_code == 422
    finally:
        client.__exit__(None, None, None)


def test_all_correct_diagnostic_reaches_mastery_without_revealing_answers(monkeypatch, tmp_path: Path) -> None:
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post(
            "/v1/mastery/diagnostics",
            json={"grade": 6, "subject_id": "math", "chapter_id": "fractions"}, headers=headers,
        ).json()
        session_id = started["id"]
        question = started["question"]
        assert "correct_option" not in question
        for answer in ("1", "3/6", "4/8"):
            outcome = client.post(
                f"/v1/mastery/sessions/{session_id}/diagnostic-answer",
                json={"selected_option": answer}, headers=headers,
            )
            assert outcome.status_code == 200, outcome.text
        assert outcome.json()["next_action"] == "mastery"
        assert outcome.json()["mastery_score"] == 1.0
    finally:
        client.__exit__(None, None, None)


def test_failed_practice_and_rewrite_return_more_coaching(monkeypatch, tmp_path: Path) -> None:
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post(
            "/v1/mastery/diagnostics",
            json={"grade": 6, "subject_id": "math", "chapter_id": "fractions"}, headers=headers,
        ).json()
        session_id = started["id"]
        client.post(
            f"/v1/mastery/sessions/{session_id}/diagnostic-answer",
            json={"selected_option": "1/2"}, headers=headers,
        )
        practice = client.post(
            f"/v1/mastery/sessions/{session_id}/practice",
            json={"response": "7/8"}, headers=headers,
        )
        assert practice.json()["next_action"] == "more_practice"
        assert practice.json()["hint"]
        client.post(
            f"/v1/mastery/sessions/{session_id}/practice",
            json={"response": "3/4"}, headers=headers,
        )
        rewrite = client.post(
            f"/v1/mastery/sessions/{session_id}/rewrite",
            json={"response": "Because it does."}, headers=headers,
        )
        assert rewrite.status_code == 200, rewrite.text
        assert rewrite.json()["mastery_achieved"] is False
        assert rewrite.json()["coaching"]
        retry = client.post(
            f"/v1/mastery/sessions/{session_id}/practice",
            json={"response": "6/8"}, headers=headers,
        )
        assert retry.status_code == 200
    finally:
        client.__exit__(None, None, None)


def test_weekly_report_and_account_deletion_cover_owned_data(monkeypatch, tmp_path: Path) -> None:
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        profile = client.get("/v1/account", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["email"].endswith("@example.com")
        started = client.post(
            "/v1/mastery/diagnostics",
            json={"grade": 6, "subject_id": "math", "chapter_id": "fractions"}, headers=headers,
        ).json()
        client.post(
            f"/v1/mastery/sessions/{started['id']}/diagnostic-answer",
            json={"selected_option": "1"}, headers=headers,
        )
        report = client.get("/v1/progress/weekly-report", headers=headers)
        assert report.status_code == 200, report.text
        assert report.json()["questions_answered"] == 1
        assert 0 <= report.json()["estimated_exam_readiness"] <= 100
        deleted = client.delete("/v1/account", headers=headers)
        assert deleted.status_code == 204
        assert client.get("/v1/account", headers=headers).status_code == 401
    finally:
        client.__exit__(None, None, None)
