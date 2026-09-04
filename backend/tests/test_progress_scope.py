from test_mastery_loop import registered_client


def test_weak_area_clears_after_explanation_but_not_practice_alone(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        def start(grade):
            return client.post('/v1/mastery/diagnostics', headers=headers,
                json={'grade': grade, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()['id']
        path = f'/v1/mastery/sessions/{start(8)}'
        client.post(path + '/diagnostic-answer', headers=headers, json={'selected_option': '1/2'})
        weak = client.get('/v1/progress/dashboard?grade=8', headers=headers).json()['weak_areas']
        assert weak
        client.post(path + '/practice', headers=headers, json={'response': '6/8'})
        assert client.get('/v1/progress/dashboard?grade=8', headers=headers).json()['weak_areas'] == weak
        client.post(path + '/rewrite', headers=headers,
                    json={'response': 'We add the numerator parts with the same denominator to make one whole.'})
        recovered = client.get('/v1/progress/dashboard?grade=8', headers=headers).json()
        assert recovered['weak_areas'] == []
        assert [badge['id'] for badge in recovered['badges']] == ['first_answer', 'learn_from_mistakes']
        # A different grade's mistake cannot undo Grade 8 remediation.
        other_grade = f'/v1/mastery/sessions/{start(6)}'
        client.post(other_grade + '/diagnostic-answer', headers=headers, json={'selected_option': '1/2'})
        assert client.get('/v1/progress/dashboard?grade=8', headers=headers).json()['weak_areas'] == []
        assert client.get('/v1/progress/dashboard?grade=6', headers=headers).json()['weak_areas'] == weak
        # New evidence of difficulty in the same grade reactivates the recommendation.
        retry = f'/v1/mastery/sessions/{start(8)}'
        client.post(retry + '/diagnostic-answer', headers=headers, json={'selected_option': '1/2'})
        assert client.get('/v1/progress/dashboard?grade=8', headers=headers).json()['weak_areas'] == weak
    finally:
        client.__exit__(None, None, None)


def test_progress_is_grade_and_owner_scoped(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        for grade in (6, 8):
            session = client.post("/v1/mastery/diagnostics", headers=headers,
                                  json={"grade": grade, "subject_id": "math", "chapter_id": "fractions"}).json()
            if grade == 8:
                for answer in ("1", "3/6", "4/8"):
                    client.post(f"/v1/mastery/sessions/{session['id']}/diagnostic-answer",
                                headers=headers, json={"selected_option": answer})
        eight = client.get("/v1/progress/dashboard?grade=8", headers=headers).json()
        six = client.get("/v1/progress/dashboard?grade=6", headers=headers).json()
        assert eight["subjects"]["math"] == 1
        assert six["subjects"]["math"] == 0
        assert [badge['id'] for badge in eight['badges']] == ['first_answer', 'chapter_master']
        assert six['badges'] == []
        assert {row["grade"] for row in eight["chapters"]} == {8}
        assert len(client.get("/v1/progress/dashboard", headers=headers).json()["chapters"]) == 2
        assert client.get("/v1/progress/weekly-report?grade=8", headers=headers).json()["questions_answered"] == 3
        assert client.get("/v1/progress/weekly-report?grade=6", headers=headers).json()["questions_answered"] == 0
        token = client.post("/v1/auth/register", json={"email": "fresh-progress@example.com", "password": "long-enough-password"}).json()["access_token"]
        fresh = client.get("/v1/progress/dashboard?grade=8", headers={"Authorization": f"Bearer {token}"}).json()
        assert fresh["subjects"] == {}
        assert fresh['badges'] == []
        assert fresh['recommendations'] == ['Start Mathematics · Fractions as your next diagnostic']
        assert client.get("/v1/progress/dashboard?grade=13", headers=headers).status_code == 422
    finally:
        client.__exit__(None, None, None)


def test_recurring_independent_mistakes_drive_evidenced_next_step(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        paths = []
        for _ in range(2):
            started = client.post('/v1/mastery/diagnostics', headers=headers,
                json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
            path = f"/v1/mastery/sessions/{started['id']}"
            paths.append(path)
            client.post(path + '/diagnostic-answer', headers=headers, json={'selected_option': '1/2'})
        snapshot = client.get('/v1/progress/dashboard?grade=8', headers=headers).json()
        evidence = snapshot['weak_area_evidence']
        assert evidence == [{
            'concept': 'Adding like fractions', 'grade': 8, 'subject_id': 'math',
            'chapter_id': 'fractions', 'unresolved_independent_mistakes': 2,
        }]
        assert snapshot['recommendations'] == [
            'Review Adding like fractions in Mathematics · Fractions: 2 unresolved independent mistakes']

        latest = paths[-1]
        client.post(latest + '/practice', headers=headers, json={'response': '6/8'})
        client.post(latest + '/rewrite', headers=headers,
                    json={'response': 'We add numerator parts with the same denominator to make one whole.'})
        recovered = client.get('/v1/progress/dashboard?grade=8', headers=headers).json()
        assert recovered['weak_area_evidence'] == []
        assert recovered['recommendations'] == [
            'Continue Mathematics · Fractions from your saved diagnostic step']
    finally:
        client.__exit__(None, None, None)
