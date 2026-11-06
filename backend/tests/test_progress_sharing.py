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
