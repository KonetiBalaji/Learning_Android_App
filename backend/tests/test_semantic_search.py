import copy
import numpy as np
import pytest

from study.semantic import SemanticUnavailable, build_index, search
from test_learning_flow import account, client, upload


class FixtureEncoder:
    def passage_embed(self, texts, **kwargs):
        for text in texts:
            yield [1, 0, 0] if "Mitochondria" in text else [0, 1, 0] if "Ribosomes" in text else [0, 0, 1]

    def query_embed(self, text, **kwargs):
        yield [1, 0, 0]


PASSAGES = [
    {"id": "energy", "section_id": "cells", "page": 1, "text": "Mitochondria produce usable energy through cellular respiration inside living cells."},
    {"id": "protein", "section_id": "cells", "page": 2, "text": "Ribosomes assemble proteins using instructions from messenger molecules."},
]


def test_vector_search_returns_exact_source_and_respects_selected_scope():
    model = FixtureEncoder()
    index = build_index(PASSAGES, model)
    hits = search(PASSAGES, index, "cell power factory", model=model)
    assert hits[0]["source_id"] == "energy"
    assert hits[0]["quote"] == PASSAGES[0]["text"][hits[0]["start"]:hits[0]["end"]]
    assert search(PASSAGES[1:], index, "cell power factory", model=model) == []


def test_invalid_vectors_and_corrupted_index_fail_closed():
    invalid = FixtureEncoder()
    invalid.passage_embed = lambda texts, **kwargs: [[float("nan"), 0, 1] for _ in texts]
    with pytest.raises(SemanticUnavailable):
        build_index(PASSAGES, invalid)
    model = FixtureEncoder()
    index = build_index(PASSAGES, model)
    corrupted = copy.deepcopy(index)
    corrupted["shape"][0] += 1
    with pytest.raises(SemanticUnavailable):
        search(PASSAGES, corrupted, "cell power", model=model)
    model.query_embed = lambda text: [[0, 0, 0]]
    with pytest.raises(SemanticUnavailable):
        search(PASSAGES, index, "cell power", model=model)


def test_semantic_api_cache_topic_quiz_owner_boundaries_and_deletion(client, monkeypatch):
    monkeypatch.setattr("study.semantic.encoder", lambda: FixtureEncoder())
    owner = account(client, "search-owner")
    other = account(client, "search-other")
    document = upload(client, owner)
    path = f'/documents/{document["id"]}'
    body = {"query": "cell power factory", "selection": {"section_ids": []}}
    assert client.post(path + "/search", headers=other, json=body).status_code == 404
    response = client.post(path + "/search", headers=owner, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["mode"] == "local_semantic"
    assert response.json()["hits"][0]["source_id"] == "p0"
    second_section = document["sections"][1]["id"]
    response = client.post(path + "/search", headers=owner, json={**body, "selection": {"section_ids": [second_section]}})
    assert response.json()["hits"] == []
    quiz = client.post(path + "/quizzes", headers=owner, json={"count": 1, "selection": {"topic": "cell power factory"}})
    assert quiz.status_code == 201, quiz.text
    assert quiz.json()["question"]["source_id"] == "p0"
    assert client.get(path, headers=owner).json()["source_locked"]
    store = client.app.state.store
    rows = store.db.execute("SELECT payload FROM records WHERE kind='embedding' AND document=?", (document["id"],)).fetchall()
    assert len(rows) == 1 and b"Mitochondria" not in rows[0][0]
    assert client.delete(path, headers=owner).status_code == 204
    assert store.db.execute("SELECT COUNT(*) FROM records WHERE kind='embedding'").fetchone()[0] == 0


def test_single_passage_local_practice_has_source_supported_choices():
    from study.quizzes import generate_local
    question = generate_local(PASSAGES[:1], 1, "multiple_choice", "easy")[0]
    assert len(set(choice.casefold() for choice in question["choices"])) == 4
    assert question["choices"][question["answer"]] in question["quote"]
