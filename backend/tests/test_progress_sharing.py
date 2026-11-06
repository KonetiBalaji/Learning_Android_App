import time

import pytest

from test_learning_flow import account, client


def invite(client, auth, role):
    response = client.post("/progress-sharing/invitations", headers=auth, json={"role": role})
    assert response.status_code == 201
    return response.json()["code"]


def redeem(client, auth, code):
    return client.post("/progress-sharing/redeem", headers=auth, json={"code": code})


@pytest.mark.parametrize("role", ["parent", "teacher"])
def test_shared_report_is_opt_in_scoped_and_revocable(client, role):
    student = account(client, "student")
    viewer = account(client, "viewer")
    stranger = account(client, "stranger")
    lesson = "/curriculum/fractions/lesson"
    assert client.post(lesson, headers=student).status_code == 200
    assert client.post(lesson + "/actions", headers=student,
                       json={"version": 0, "action": "diagnostic", "choice": 0}).status_code == 200
    code = invite(client, student, role)
    store = client.app.state.store
    assert store.db.execute("SELECT digest FROM progress_invitations").fetchone()[0] != code
    assert redeem(client, student, code).status_code == 409
    accepted = redeem(client, viewer, code)
    assert accepted.status_code == 201
    identifier = accepted.json()["id"]
    path = "/progress-sharing/" + identifier
    assert redeem(client, stranger, code).status_code == 404
    assert client.get(path + "/report", headers=stranger).status_code == 404
    assert client.get(path + "/report", headers=student).status_code == 404
    assert client.delete(path, headers=stranger).status_code == 404
    assert client.get("/progress-sharing", headers=student).json() == [
        {"id": identifier, "role": role, "direction": "shared"}
    ]
    assert client.get("/progress-sharing", headers=viewer).json() == [
        {"id": identifier, "role": role, "direction": "received"}
    ]
    report = client.get(path + "/report", headers=viewer)
    assert report.status_code == 200
    summary = report.json()
    assert summary["role"] == role
    assert summary["week"] == {"chapters_active": 1, "chapters_mastered": 0}
    math = next(row for row in summary["subjects"] if row["grade"] == 6 and row["subject"] == "Mathematics")
    assert math == {"grade": 6, "subject": "Mathematics", "available": 5, "mastered": 0,
                    "week_active": 1, "week_mastered": 0}
    assert summary["weak_areas"] == [{"grade": 6, "subject": "Mathematics", "title": "Adding fractions"}]
    assert "Adding fractions" in summary["recommendation"]
    assert set(summary) == {"role", "subjects", "weak_areas", "week", "recommendation"}
    assert client.delete(path, headers=student).status_code == 204
    assert client.get(path + "/report", headers=viewer).status_code == 404


def test_invitation_replacement_cancellation_expiry_and_account_deletion(client):
    student = account(client, "student")
    viewer = account(client, "viewer")
    old = invite(client, student, "parent")
    current = invite(client, student, "parent")
    assert redeem(client, viewer, old).status_code == 404
    assert client.delete("/progress-sharing/invitations/parent", headers=student).status_code == 204
    assert redeem(client, viewer, current).status_code == 404
    expired = invite(client, student, "parent")
    store = client.app.state.store
    with store.db:
        store.db.execute("UPDATE progress_invitations SET expires=?", (time.time() - 1,))
    assert redeem(client, viewer, expired).status_code == 404
    link = redeem(client, viewer, invite(client, student, "teacher")).json()["id"]
    invite(client, student, "parent")
    assert client.delete("/account", headers=student).status_code == 204
    assert client.get(f"/progress-sharing/{link}/report", headers=viewer).status_code == 404
    assert store.db.execute("SELECT COUNT(*) FROM progress_invitations").fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM progress_links").fetchone()[0] == 0


def test_concurrent_redeem_consumes_code_across_backend_instances(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from fastapi.testclient import TestClient
    from study.api import create_app

    monkeypatch.setenv("STUDY_GENERATION_MODE", "local_practice")
    with TestClient(create_app(tmp_path)) as first, TestClient(create_app(tmp_path)) as second:
        student = account(first, "student")
        parent_a = account(first, "parenta")
        parent_b = account(second, "parentb")
        code = invite(first, student, "parent")
        ready = Barrier(2)

        def accept(client, auth):
            ready.wait(timeout=10)
            return redeem(client, auth, code).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(accept, first, parent_a), pool.submit(accept, second, parent_b)]
            assert sorted(task.result(timeout=15) for task in results) == [201, 404]
        assert len(first.get("/progress-sharing", headers=student).json()) == 1


def test_report_prioritizes_repeated_difficulty_without_sharing_attempt_counts():
    from study.progress_sharing import report

    lessons = [
        {"chapter_id": "fractions", "phase": "coach", "correct": False},
        {"chapter_id": "water-cycle", "phase": "coach", "correct": False,
         "diagnostic_index": 1, "diagnostic_hits": 0, "practice_misses": 1},
        {"chapter_id": "decimals", "phase": "mastered", "correct": False, "practice_misses": 5},
    ]
    shared = report(lessons, "parent", 1_800_000_000)
    assert shared["weak_areas"] == [
        {"grade": 6, "subject": "Science", "title": "The water cycle"},
        {"grade": 6, "subject": "Mathematics", "title": "Adding fractions"},
    ]
    assert "The water cycle" in shared["recommendation"]


def test_weekly_report_counts_new_starts_and_honors_both_time_boundaries():
    from study.mastery import new_lesson
    from study.progress_sharing import report

    now = 1_800_000_000
    cutoff = now - 7 * 86400
    lessons = [
        new_lesson("fractions", now),
        {"chapter_id": "evaporation", "phase": "mastered", "last_activity": cutoff, "mastered_at": cutoff},
        {"chapter_id": "complete-sentences", "phase": "mastered", "last_activity": cutoff - 1, "mastered_at": cutoff - 1},
        {"chapter_id": "primary-sources", "phase": "mastered", "last_activity": now + 1, "mastered_at": now + 1},
        {"chapter_id": "counting-on", "phase": "mastered"},
    ]
    shared = report(lessons, "teacher", now)
    assert shared["week"] == {"chapters_active": 2, "chapters_mastered": 1}
    assert sum(subject["mastered"] for subject in shared["subjects"]) == 4
    active = {(row["grade"], row["subject"]): (row["week_active"], row["week_mastered"])
              for row in shared["subjects"] if row["week_active"] or row["week_mastered"]}
    assert active == {(6, "Mathematics"): (1, 0), (6, "Science"): (1, 1)}
