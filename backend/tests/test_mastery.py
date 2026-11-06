import pytest

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
    assert coaching["feedback"] == (
        "You chose 1/2. Adding one quarter to three quarters must give more than three quarters."
    )
    assert client.post(fractions, headers=first).json() == coaching
    assert action(0, "diagnostic", choice=0) == coaching
    practice = action(1, "continue")
    assert practice["phase"] == "practice" and "hint" in practice and "answer" not in practice
    assert practice["feedback"] == ""
    assert action(2, "practice", response="1/0")["phase"] == "coach"
    assert action(3, "continue")["prompt"] != practice["prompt"]
    assert action(4, "practice", response="8/14")["phase"] == "rewrite"
    assert action(5, "rewrite", response="Just add the fractions")["phase"] == "rewrite"
    progress = client.get("/curriculum", headers=first).json()[0]
    assert progress["needs_practice"] and progress["practice_misses"] == 1 and progress["rewrite_revisions"] == 1
    assert progress["review_events"] == 3
    assert client.get("/curriculum", headers=second).json()[0]["started"] is False
    assert action(6, "rewrite", response="Add the numerators and keep the denominator unchanged.")["phase"] == "mastered"
    progress = client.get("/curriculum", headers=first).json()[0]
    assert progress["mastered"] and not progress["needs_practice"]
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

@pytest.mark.parametrize("chapter, choice, first_answer, second_answer, rewrite", [
    ("counting-on", 2, "7", "9", "Start at four and count two steps to six."),
    ("place-value", 1, "53", "72", "Four tens make forty, and seven ones make forty-seven altogether."),
    ("equal-groups", 2, "12", "20", "Add four for each of the three groups to get twelve."),
    ("rectangle-perimeter", 2, "20", "18", "Add all four sides, using each measurement twice."),
    ("volume", 2, "30", "32", "There are twelve cubes per layer, so two layers contain twenty-four cubes."),
    ("evaporation", 2, "Condensation.", "evaporation", "Evaporation changes liquid to vapor. Condensation changes vapor to liquid."),
    ("complete-sentences", 1, "glowed", "rang", "Birds is the subject and sang is the verb."),
    ("primary-sources", 1, "secondary", "Primary", "The sailor wrote the diary during the voyage as a direct witness."),
    ("unit-rates", 1, "7", "6", "Divide twelve dollars by three notebooks to find the cost per notebook."),
    ("linear-equations", 2, "6", "5", "Subtract two on both sides, then divide both sides by three."),
    ("linear-slope", 1, "3", "0.5", "Divide the vertical change in y by the horizontal change in x."),
    ("right-triangles", 0, "13", "17", "Add the squares of the legs and take the square root."),
    ("exponential-growth", 3, "120", "135", "Multiply by the factor two once for each of the three days."),
    ("expected-value", 2, "3", "6", "Multiply the ten dollar payout by probability one half to get five."),
])
def test_authored_starter_chapter_diagnostic_practice_and_rewrite(client, chapter, choice, first_answer, second_answer, rewrite):
    auth = account(client)
    path = f"/curriculum/{chapter}/lesson"

    def act(lesson, action, **fields):
        reply = client.post(path + "/actions", headers=auth, json={"version": lesson["version"], "action": action, **fields})
        assert reply.status_code == 200, reply.text
        return reply.json()

    initial = client.post(path, headers=auth).json()
    practice = act(initial, "diagnostic", choice=choice)
    assert practice["phase"] == "practice"
    writing = act(practice, "practice", response=first_answer)
    assert writing["phase"] == "rewrite"
    assert act(writing, "rewrite", response="I guessed the right answer.")["phase"] == "rewrite"
    current = client.post(path, headers=auth).json()
    coached = act(current, "review")
    assert coached["phase"] == "coach"
    original = act(coached, "continue")
    wrong = act(original, "practice", response="irrelevant")
    alternate = act(wrong, "continue")
    assert alternate["prompt"] != original["prompt"]
    writing = act(alternate, "practice", response=second_answer)
    assert writing["phase"] == "rewrite"
    assert act(writing, "rewrite", response=rewrite)["phase"] == "mastered"


def test_catalog_offers_all_grades_and_the_four_grade_six_subjects(client):
    chapters = client.get("/curriculum", headers=account(client)).json()
    assert {chapter["grade"] for chapter in chapters} == set(range(1, 13))
    assert {chapter["subject"] for chapter in chapters if chapter["grade"] == 6} == {
        "Mathematics", "Science", "English", "Social Studies"
    }

def test_grade_six_math_path_requires_mastery_and_resumes_multi_question_diagnostics(client):
    from test_readiness import finish

    auth = account(client)
    percentages = "/curriculum/percentages/lesson"
    algebra = "/curriculum/grade6-algebra/lesson"
    geometry = "/curriculum/grade6-geometry/lesson"
    assert all(client.post(path, headers=auth).status_code == 409 for path in (percentages, algebra, geometry))
    finish(client, auth, "fractions", 1, "3/4", "Add the numerators and keep the denominator unchanged.")
    finish(client, auth, "decimals", 0, "0.68", "Align the decimal points to add matching place values.")

    def open_lesson(path):
        reply = client.post(path, headers=auth)
        assert reply.status_code == 200, reply.text
        return reply.json()

    def advance(path, current, action, **fields):
        reply = client.post(path + "/actions", headers=auth,
                            json={"version": current["version"], "action": action, **fields})
        assert reply.status_code == 200, reply.text
        return reply.json()

    def after_two_misses(path, practice, expected_prompt):
        prompts = [practice["prompt"]]
        for _ in range(2):
            coach = advance(path, practice, "practice", response="0")
            assert coach["phase"] == "coach"
            assert advance(path, practice, "practice", response="0") == coach
            practice = advance(path, coach, "continue")
            prompts.append(practice["prompt"])
        assert len(set(prompts)) == 3 and prompts[-1] == expected_prompt
        assert open_lesson(path) == practice
        assert "answer" not in practice
        return practice

    initial = open_lesson(percentages)
    assert (initial["diagnostic_index"], initial["diagnostic_total"]) == (0, 3)
    second = advance(percentages, initial, "diagnostic", choice=1)
    assert second["phase"] == "diagnostic" and second["diagnostic_index"] == 1
    assert advance(percentages, initial, "diagnostic", choice=1) == second
    assert open_lesson(percentages) == second
    coach = advance(percentages, second, "diagnostic", choice=0)
    assert coach["phase"] == "coach" and coach["diagnostic_remaining"]
    assert coach["feedback"] == "You chose 0.05. Review the worked example, then continue."
    third = advance(percentages, coach, "continue")
    assert third["phase"] == "diagnostic" and third["diagnostic_index"] == 2
    practice = advance(percentages, third, "diagnostic", choice=1)
    assert practice["phase"] == "practice" and "answer" not in practice
    practice = after_two_misses(percentages, practice, "Enter 25% of 20.")
    rewrite = advance(percentages, practice, "practice", response="5")
    mastered = advance(percentages, rewrite, "rewrite", response="Multiply sixty by 0.25 to find twenty-five percent.")
    assert mastered["phase"] == "mastered" and not mastered["diagnostic_correct"]
    assert mastered["diagnostic_score"] == {"correct": 2, "total": 3}
    assert open_lesson(percentages) == mastered
    assert client.post(geometry, headers=auth).status_code == 409

    lesson = open_lesson(algebra)
    for choice in (2, 1, 3):
        lesson = advance(algebra, lesson, "diagnostic", choice=choice)
    assert lesson["phase"] == "practice"
    lesson = after_two_misses(algebra, lesson, "Enter x in x + 2 = 16.")
    lesson = advance(algebra, lesson, "practice", response="14")
    lesson = advance(algebra, lesson, "rewrite", response="Subtract five from both sides and the value is seven.")
    assert lesson["phase"] == "mastered"
    lesson = open_lesson(geometry)
    for choice in (1, 1, 3):
        lesson = advance(geometry, lesson, "diagnostic", choice=choice)
    lesson = after_two_misses(
        geometry, lesson, "Enter the area in square centimeters for base 5 cm and height 3 cm."
    )
    lesson = advance(geometry, lesson, "practice", response="7.5")
    lesson = advance(geometry, lesson, "rewrite", response="Multiply the base by the perpendicular height and take half.")
    assert lesson["phase"] == "mastered"


@pytest.mark.parametrize("subject, prerequisite, next_chapter", [
    (
        "Science",
        ("evaporation", 2, "condensation", "Evaporation turns liquid into vapor. Condensation reverses it."),
        ("water-cycle", 2, "condensation", "Water evaporates, condenses into clouds, and falls as rain."),
    ),
    (
        "English",
        ("complete-sentences", 1, "glowed", "Birds is the subject and sang is the verb."),
        ("combining-sentences", 1, "but", "But signals contrast because they reached the top despite the steep trail."),
    ),
    (
        "Social Studies",
        ("primary-sources", 1, "secondary", "The sailor wrote the diary during the voyage."),
        ("corroborating-sources", 2, "dependent", "The city record is an independent source for the opening date."),
    ),
])
def test_grade_six_subject_paths_unlock_for_the_student_only(client, subject, prerequisite, next_chapter):
    from test_readiness import finish

    student = account(client, "student")
    other = account(client, "other")
    path = f"/curriculum/{next_chapter[0]}/lesson"

    def subject_chapters(headers):
        return [chapter for chapter in client.get("/curriculum", headers=headers).json()
                if chapter["grade"] == 6 and chapter["subject"] == subject]

    first, second = subject_chapters(student)
    assert (first["id"], second["id"]) == (prerequisite[0], next_chapter[0])
    assert not first["locked"] and second["locked"]
    assert client.post(path, headers=student).status_code == 409

    finish(client, student, *prerequisite)
    first, second = subject_chapters(student)
    assert first["mastered"] and not second["locked"]
    assert client.post(path, headers=other).status_code == 409
    finish(client, student, *next_chapter)
    assert subject_chapters(student)[1]["mastered"]
    assert not subject_chapters(other)[1]["started"]


def test_legacy_partial_diagnostic_completes_without_inventing_a_score():
    from study.mastery import advance, new_lesson, snapshot

    lesson = new_lesson("percentages", 0)
    lesson.update(diagnostic_index=1, correct=False)
    advance(lesson, "diagnostic", 2, None, 1)
    advance(lesson, "diagnostic", 1, None, 2)
    advance(lesson, "practice", None, "16", 3)
    advance(lesson, "rewrite", None, "Multiply sixty by 0.25 to find twenty-five percent.", 4)
    result = snapshot(lesson)
    assert result["phase"] == "mastered"
    assert "diagnostic_score" not in result


@pytest.mark.parametrize("chapter, choice, third_prompt, equivalent", [
    ("fractions", 1, "What is 2/5 + 2/5?", "8/10"),
    ("decimals", 0, "What is 0.12 + 0.14?", "26/100"),
])
def test_math_practice_uses_a_third_question_after_two_misses(client, chapter, choice, third_prompt, equivalent):
    from test_readiness import finish

    auth = account(client)
    if chapter == "decimals":
        finish(client, auth, "fractions", 1, "3/4", "Add the numerators and keep the denominator unchanged.")
    path = f"/curriculum/{chapter}/lesson"
    lesson = client.post(path, headers=auth).json()

    def act(current, action, **fields):
        result = client.post(path + "/actions", headers=auth,
                             json={"version": current["version"], "action": action, **fields})
        assert result.status_code == 200, result.text
        return result.json()

    practice = act(lesson, "diagnostic", choice=choice)
    prompts = [practice["prompt"]]
    for _ in range(2):
        coach = act(practice, "practice", response="0")
        assert coach["phase"] == "coach"
        assert act(practice, "practice", response="0") == coach
        practice = act(coach, "continue")
        prompts.append(practice["prompt"])
    assert len(set(prompts)) == 3 and prompts[-1] == third_prompt
    assert client.post(path, headers=auth).json() == practice
    assert "answer" not in practice
    assert act(practice, "practice", response=equivalent)["phase"] == "rewrite"


@pytest.mark.parametrize("chapter, choice, third_answer", [
    ("evaporation", 2, "Condensation."),
    ("water-cycle", 2, "Precipitation"),
    ("complete-sentences", 1, "flooded"),
    ("combining-sentences", 1, "but"),
    ("primary-sources", 1, "secondary"),
    ("corroborating-sources", 2, "dependent"),
])
def test_grade_six_subject_practice_moves_through_five_distinct_prompts(chapter, choice, third_answer):
    from study.mastery import advance, new_lesson, snapshot

    def attempt():
        lesson = new_lesson(chapter, 0)
        advance(lesson, "diagnostic", choice, None, 1)
        assert snapshot(lesson)["phase"] == "practice"
        return lesson

    def miss(lesson):
        advance(lesson, "practice", None, "irrelevant", 2)
        assert snapshot(lesson)["phase"] == "coach"
        advance(lesson, "continue", None, None, 3)
        return snapshot(lesson)["prompt"]

    lesson = attempt()
    prompts = [snapshot(lesson)["prompt"]]
    prompts.extend(miss(lesson) for _ in range(4))
    assert len(set(prompts)) == 5
    assert miss(lesson) == prompts[0]

    lesson = attempt()
    miss(lesson)
    assert miss(lesson) == prompts[2]
    advance(lesson, "practice", None, third_answer, 4)
    assert snapshot(lesson)["phase"] == "rewrite"
