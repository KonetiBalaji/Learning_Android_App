from test_learning_flow import account, client


def test_curriculum_coaching_retries_mastery_and_owner_isolation(client):
    assert client.get("/curriculum").status_code == 401
    first = account(client, "curriculum-student")
    second = account(client, "another-student")
    fractions = "/curriculum/fractions/lesson"
    decimals = "/curriculum/decimals/lesson"
    assert client.post(decimals, headers=first).status_code == 409
    assert client.post("/curriculum/missing/lesson", headers=first).status_code == 404

    def action(version, step, **body):
        result = client.post(fractions + "/actions", headers=first, json={"version": version, "action": step, **body})
        assert result.status_code == 200, result.text
        return result.json()

    lesson = client.post(fractions, headers=first).json()
    assert lesson["phase"] == "diagnostic"
    assert "answer" not in lesson and "explanation" not in lesson
    assert client.post(fractions + "/actions", headers=second, json={"version": 0, "action": "continue"}).status_code == 404
    assert client.post(fractions + "/actions", headers=first, json={"version": 0, "action": "rewrite"}).status_code == 422
    coaching = action(0, "diagnostic", choice=0)
    assert coaching["phase"] == "coach" and "5/5" in coaching["example"]
    assert action(0, "diagnostic", choice=0) == coaching
    practice = action(1, "continue")
    assert practice["phase"] == "practice" and "hint" in practice and "answer" not in practice
    assert action(2, "practice", response="1/0")["phase"] == "coach"
    assert action(3, "continue")["prompt"] != practice["prompt"]
    assert action(4, "practice", response="8/14")["phase"] == "rewrite"
    assert action(5, "rewrite", response="Just add the fractions")["phase"] == "rewrite"
    assert action(6, "rewrite", response="Add the numerators and keep the denominator unchanged.")["phase"] == "mastered"
    assert client.post(fractions, headers=first).json()["phase"] == "mastered"
    assert client.post(decimals, headers=first).json()["phase"] == "diagnostic"
    assert client.post(decimals, headers=second).status_code == 409
    assert client.get("/curriculum", headers=second).json()[0]["mastered"] is False
    assert client.delete("/account", headers=first).status_code == 204
    assert client.app.state.store.db.execute("SELECT count(*) FROM records WHERE kind='mastery'").fetchone()[0] == 0


def test_correct_diagnostic_moves_straight_to_practice(client):
    student = account(client)
    path = "/curriculum/fractions/lesson"
    assert client.post(path, headers=student).status_code == 200
    result = client.post(path + "/actions", headers=student, json={"version": 0, "action": "diagnostic", "choice": 1})
    assert result.status_code == 200
    assert result.json()["phase"] == "practice"
