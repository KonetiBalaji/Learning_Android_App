import pytest

from study.adaptive import recommend
from study.documents import DocumentError
from test_learning_flow import account, client, upload


DOCUMENT = {"id": "document", "sections": [{"id": "a", "title": "Cells"}, {"id": "b", "title": "Plants"}],
            "passages": [{"id": str(i), "section_id": section, "text": f"Mitochondria generate usable cellular energy during respiration example {i}."}
                         for section in ["a", "b"] for i in range(12)]}


def attempt(section, correct, count, created=1):
    return {"document_id": "document", "created": created, "index": count,
            "questions": [{"prompt": f"Source question {i}", "concept": section, "section_id": section} for i in range(count)],
            "answers": [{"correct": i < correct} for i in range(count)]}


def test_weak_sections_receive_priority_over_stronger_evidence():
    advice = recommend(DOCUMENT, [attempt("a", 2, 10), attempt("b", 9, 10)], ai_configured=True)
    assert advice["section_ids"] == ["a"] and advice["difficulty"] == "easy"
    assert advice["evidence"]["answered"] == 10


@pytest.mark.parametrize("correct,count,expected", [(2, 5, "easy"), (4, 6, "medium"), (9, 10, "hard")])
def test_levels_follow_evidence_and_local_mode_never_claims_semantic_difficulty(correct, count, expected):
    doc = {**DOCUMENT, "sections": DOCUMENT["sections"][:1], "passages": [p for p in DOCUMENT["passages"] if p["section_id"] == "a"]}
    assert recommend(doc, [attempt("a", correct, count)], ai_configured=True)["difficulty"] == expected
    local = recommend(doc, [attempt("a", correct, count)], ai_configured=False)
    assert local["difficulty"] == "easy" and local["notice"]


def test_retry_answers_replace_prior_evidence_instead_of_inflating_mastery():
    doc = {**DOCUMENT, "sections": DOCUMENT["sections"][:1], "passages": [p for p in DOCUMENT["passages"] if p["section_id"] == "a"]}
    advice = recommend(doc, [attempt("a", 10, 10, created=2), attempt("a", 0, 10, created=1)], ai_configured=True)
    assert advice["evidence"] == {"correct": 10, "answered": 10, "distinct_questions": True}
    unrelated = {**attempt("a", 0, 10), "document_id": "other-document"}
    assert recommend(doc, [unrelated], ai_configured=True)["evidence"]["answered"] == 0


def test_recommendation_api_is_owned_and_immediately_startable(client):
    first = account(client, "adaptive-owner")
    other = account(client, "adaptive-other")
    document = upload(client, first)
    root = f'/documents/{document["id"]}'
    assert client.get(root + "/next-practice", headers=other).status_code == 404
    response = client.get(root + "/next-practice", headers=first)
    assert response.status_code == 200, response.text
    advice = response.json()
    quiz = client.post(root + "/quizzes", headers=first, json={"selection": {"section_ids": advice["section_ids"]},
                       "count": advice["count"], "difficulty": advice["difficulty"]})
    assert quiz.status_code == 201, quiz.text
    assert quiz.json()["count"] == advice["count"]


def test_no_recommendation_is_invented_for_unusable_material():
    with pytest.raises(DocumentError):
        recommend({**DOCUMENT, "passages": [{"section_id": "a", "text": "a b c a b c a b c"}]}, [], ai_configured=False)
