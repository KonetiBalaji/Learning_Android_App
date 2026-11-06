from test_learning_flow import account, client


def finish(client, headers, chapter, choice, practice, explanation):
    path = f"/curriculum/{chapter}/lesson"
    assert client.post(path, headers=headers).status_code == 200
    steps = [("diagnostic", {"choice": choice}), ("practice", {"response": practice}),
             ("rewrite", {"response": explanation})]
    for version, (action, data) in enumerate(steps):
        reply = client.post(path + "/actions", headers=headers, json={"action": action, "version": version, **data})
        assert reply.status_code == 200, reply.text
    assert reply.json()["phase"] == "mastered"


def test_readiness_is_held_out_owned_resumable_and_scored_without_leaking_answers(client):
    student = account(client, "student")
    other = account(client, "viewer")
    path = "/curriculum/readiness/grade6-math"
    assert client.post(path, headers=student).status_code == 409
    finish(client, student, "fractions", 1, "3/4", "Add the numerators and keep the denominator unchanged.")
    assert client.post(path, headers=student).status_code == 409
    finish(client, student, "decimals", 0, "0.68", "Align the decimal points to add matching place values.")
    first = client.post(path, headers=student).json()
    assert first["index"] == 0 and "correct" not in first and "by_chapter" not in first
    assert client.post(path, headers=other).status_code == 409
    assert client.post(path + "/answers", headers=other, json={"index": 0, "choice": 1}).status_code == 404
    assert client.post(path + "/answers", headers=student, json={"index": 1, "choice": 1}).status_code == 409

    for index, choice in enumerate([1, 0, 3, 0, 1, 0]):
        response = client.post(path + "/answers", headers=student, json={"index": index, "choice": choice})
        assert response.status_code == 200
        step = response.json()
        assert step["index"] == index + 1
        if index < 5:
            assert "correct" not in step and not step["complete"]
        assert client.post(path, headers=student).json() == step
    assert step["complete"] and step["correct"] == 5
    assert step["by_chapter"] == {"fractions": {"correct": 3, "total": 3}, "decimals": {"correct": 2, "total": 3}}
    assert "choices" not in step and "answers" not in step
    assert client.post(path + "/answers", headers=student, json={"index": 0, "choice": 1}).json() == step
    assert client.post(path + "/answers", headers=student, json={"index": 0, "choice": 2}).status_code == 409

    invitation = client.post("/progress-sharing/invitations", headers=student, json={"role": "parent"}).json()
    link = client.post("/progress-sharing/redeem", headers=other, json={"code": invitation["code"]}).json()
    shared = client.get(f"/progress-sharing/{link['id']}/report", headers=other).json()["readiness"]
    assert shared == {"correct": 5, "total": 6, "by_chapter": step["by_chapter"]}
    assert client.delete("/account", headers=student).status_code == 204
    assert client.app.state.store.db.execute("SELECT COUNT(*) FROM records WHERE kind='readiness'").fetchone()[0] == 0
