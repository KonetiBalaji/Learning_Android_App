from test_learning_flow import account, upload, client


def completed_quiz(client, headers):
    document = upload(client, headers)
    quiz = client.post(f'/documents/{document["id"]}/quizzes', headers=headers, json={"count": 5}).json()
    for index in range(5):
        question = client.get(f'/quizzes/{quiz["id"]}', headers=headers).json()["question"]
        assert client.post(f'/quizzes/{quiz["id"]}/answers', headers=headers, json={"question_id": question["id"], "choice": 0}).status_code == 200
        assert client.post(f'/quizzes/{quiz["id"]}/next', headers=headers, json={"expected_index": index}).status_code == 200
    return document, quiz


def test_create_rate_retry_due_filter_and_owner_scope(client):
    first = account(client, "cards-owner")
    second = account(client, "cards-other")
    document, quiz = completed_quiz(client, first)
    path = f'/quizzes/{quiz["id"]}/flashcards'
    assert client.post(path, headers=second, json={}).status_code == 404
    created = client.post(path, headers=first, json={})
    assert created.status_code == 201, created.text
    cards = created.json()
    assert len(cards) == 5 and all(card["quote"] for card in cards)
    assert [c["id"] for c in client.post(path, headers=first, json={}).json()] == [c["id"] for c in cards]
    assert client.get("/flashcards", headers=second).json() == []
    assert client.get(f'/flashcards?document_id={document["id"]}', headers=second).status_code == 404
    card = cards[0]
    rating = {"quality": 4, "expected_version": 0, "request_id": "rating-request-1"}
    route = f'/flashcards/{card["id"]}/reviews'
    assert client.post(route, headers=second, json=rating).status_code == 404
    rated = client.post(route, headers=first, json=rating)
    assert rated.status_code == 200, rated.text
    assert rated.json()["review"]["interval_days"] == 1
    assert client.post(route, headers=first, json=rating).json() == rated.json()
    assert client.post(route, headers=first, json={**rating, "quality": 5}).status_code == 409
    assert client.post(route, headers=first, json={**rating, "request_id": "new-request-stale"}).status_code == 409
    assert client.post(route, headers=first, json={**rating, "quality": True}).status_code == 422
    assert len(client.get("/flashcards", headers=first).json()) == 4
    assert len(client.get("/flashcards?due_only=false", headers=first).json()) == 5
    client.post(path, headers=first, json={})
    assert len(client.get("/flashcards", headers=first).json()) == 4  # creation never resets scheduling
    assert client.delete(f'/documents/{document["id"]}', headers=first).status_code == 204
    assert client.get("/flashcards?due_only=false", headers=first).json() == []
    assert client.post(route, headers=first, json=rating).status_code == 404


def test_lapsed_card_stays_in_today_learning_queue(client):
    headers = account(client)
    _, quiz = completed_quiz(client, headers)
    card = client.post(f'/quizzes/{quiz["id"]}/flashcards', headers=headers, json={}).json()[0]
    route = f'/flashcards/{card["id"]}/reviews'
    failed = client.post(route, headers=headers, json={"quality": 0, "expected_version": 0, "request_id": "failed-recall-1"}).json()
    assert failed["repeat_today"] is True and failed["review"]["lapses"] == 1
    assert card["id"] in [c["id"] for c in client.get("/flashcards", headers=headers).json()]
    recovered = client.post(route, headers=headers, json={"quality": 4, "expected_version": 1, "request_id": "recovered-recall-1"}).json()
    assert recovered["repeat_today"] is False
    assert card["id"] not in [c["id"] for c in client.get("/flashcards", headers=headers).json()]
