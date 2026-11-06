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

def test_full_readiness_preserves_short_result_and_reports_all_five_topics(client):
    student = account(client, "student")
    viewer = account(client, "teacher")
    short = "/curriculum/readiness/grade6-math"
    full = "/curriculum/readiness/grade6-math-full"
    assert client.post("/curriculum/readiness/unknown", headers=student).status_code == 404
    finish(client, student, "fractions", 1, "3/4", "Add the numerators and keep the denominator unchanged.")
    finish(client, student, "decimals", 0, "0.68", "Align the decimal points to add matching place values.")
    assert client.post(full, headers=student).status_code == 409

    def answer_check(path, choices):
        assert client.post(path, headers=student).json()["index"] == 0
        for index, choice in enumerate(choices):
            response = client.post(path + "/answers", headers=student, json={"index": index, "choice": choice})
            assert response.status_code == 200, response.text
            step = response.json()
            assert step["index"] == index + 1
            if index + 1 < len(choices):
                assert not step["complete"] and "correct" not in step
        assert step["complete"]
        return step

    original = answer_check(short, [1, 0, 3, 2, 1, 0])

    for chapter, choices, practice, explanation in (
        ("percentages", (1, 2, 1), "16", "Multiply sixty by 0.25 to find twenty-five percent."),
        ("grade6-algebra", (2, 1, 3), "9", "Subtract five from both sides and the value is seven."),
        ("grade6-geometry", (1, 1, 3), "30", "Multiply the base by the perpendicular height and take half."),
    ):
        lesson = f"/curriculum/{chapter}/lesson"
        current = client.post(lesson, headers=student).json()
        actions = [("diagnostic", {"choice": choice}) for choice in choices]
        actions += [("practice", {"response": practice}), ("rewrite", {"response": explanation})]
        for action, body in actions:
            response = client.post(lesson + "/actions", headers=student,
                                   json={"action": action, "version": current["version"], **body})
            assert response.status_code == 200, response.text
            current = response.json()
        assert current["phase"] == "mastered"

    assert client.post(full, headers=viewer).status_code == 409
    result = answer_check(full, [1, 2, 0, 3, 1, 2, 0, 3, 1, 2, 0, 3, 1, 2, 0])
    assert result["total"] == result["correct"] == 15
    assert set(result["by_chapter"]) == {"fractions", "decimals", "percentages", "grade6-algebra", "grade6-geometry"}
    assert all(topic == {"correct": 3, "total": 3} for topic in result["by_chapter"].values())
    assert client.post(short, headers=student).json() == original
    code = client.post("/progress-sharing/invitations", headers=student, json={"role": "teacher"}).json()["code"]
    link = client.post("/progress-sharing/redeem", headers=viewer, json={"code": code}).json()["id"]
    shared = client.get(f"/progress-sharing/{link}/report", headers=viewer).json()
    assert shared["readiness"]["total"] == 6
    assert shared["full_readiness"]["total"] == 15
    assert "answers" not in shared["full_readiness"]
