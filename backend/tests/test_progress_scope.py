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
        assert client.get('/v1/progress/dashboard?grade=8', headers=headers).json()['weak_areas'] == []
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
        assert {row["grade"] for row in eight["chapters"]} == {8}
        assert len(client.get("/v1/progress/dashboard", headers=headers).json()["chapters"]) == 2
        assert client.get("/v1/progress/weekly-report?grade=8", headers=headers).json()["questions_answered"] == 3
        assert client.get("/v1/progress/weekly-report?grade=6", headers=headers).json()["questions_answered"] == 0
        token = client.post("/v1/auth/register", json={"email": "fresh-progress@example.com", "password": "long-enough-password"}).json()["access_token"]
        assert client.get("/v1/progress/dashboard?grade=8", headers={"Authorization": f"Bearer {token}"}).json()["subjects"] == {}
        assert client.get("/v1/progress/dashboard?grade=13", headers=headers).status_code == 422
    finally:
        client.__exit__(None, None, None)
