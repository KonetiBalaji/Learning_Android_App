from test_mastery_loop import registered_client


def test_uploaded_document_can_resume_before_quiz_creation(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        upload = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt',
            'Chapter 1 Cells\nCells are the basic units of living organisms. Ribosomes build proteins inside cells.\n'
            'Chapter 2 Plants\nPlants convert light energy into chemical energy through photosynthesis.')})
        assert upload.status_code == 201
        document = upload.json()
        path = f"/v1/documents/{document['id']}"
        restored = client.get(path, headers=headers)
        assert restored.status_code == 200
        assert restored.json() == document
        assert set(restored.json()) == {'id', 'original_name', 'chapters'}
        assert client.get('/v1/documents', headers=headers).json() == [document]
        assert client.get('/v1/documents').status_code == 401
        assert client.get(path).status_code == 401
        other = client.post('/v1/auth/register', json={'email': 'other-upload@example.com', 'password': 'long-enough-password'}).json()
        assert client.get('/v1/documents', headers={'Authorization': f"Bearer {other['access_token']}"}).json() == []
        assert client.get(path, headers={'Authorization': f"Bearer {other['access_token']}"}).status_code == 404
        assert client.get('/v1/documents/missing', headers=headers).status_code == 404
        assert client.delete(path, headers=headers).status_code == 204
        assert client.get(path, headers=headers).status_code == 404
        assert client.get('/v1/documents', headers=headers).json() == []
    finally:
        client.__exit__(None, None, None)


def test_document_quiz_restores_committed_answers_without_leaking_pending_answers(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        text = ('Cells are the basic units of life in living organisms. Mitochondria release usable energy for cellular work. '
                'Ribosomes support protein synthesis inside cells. Cell membranes regulate what enters and leaves the cell. '
                'Photosynthesis converts light energy into chemical energy in plants.')
        document = client.post('/v1/documents', headers=headers, files={'file': ('notes.txt', text)}).json()
        quiz = client.post(f"/v1/documents/{document['id']}/quizzes", headers=headers,
                           json={'chapter_ids': [document['chapters'][0]['id']], 'question_count': 5}).json()
        path = f"/v1/quizzes/{quiz['id']}"
        initial = client.get(path, headers=headers).json()
        assert initial['answered'] == 0 and initial['total'] == 5
        assert initial['last_feedback'] is None
        assert initial['question'] == quiz['first_question']
        question = initial['question']
        outcome = client.post(path + f"/questions/{question['id']}/answer", headers=headers,
                              json={'selected_option': question['options'][0]}).json()
        resumed = client.get(path, headers=headers).json()
        assert resumed['answered'] == 1
        assert resumed['last_feedback'] == outcome
        assert resumed['question']['ordinal'] == 2
        assert 'correct_option' not in resumed['question'] and 'explanation' not in resumed['question']
        assert resumed['document'] == document
        other = client.post('/v1/auth/register', json={'email': 'other-doc-resume@example.com', 'password': 'long-enough-password'}).json()
        assert client.get(path, headers={'Authorization': f"Bearer {other['access_token']}"}).status_code == 404
        assert client.get(path).status_code == 401
        for _ in range(4):
            question = client.get(path, headers=headers).json()['question']
            assert client.post(path + f"/questions/{question['id']}/answer", headers=headers,
                               json={'selected_option': question['options'][0]}).status_code == 200
        final = client.get(path, headers=headers).json()
        assert final['question'] is None and final['answered'] == final['total'] == 5
        assert client.get(path + '/results', headers=headers).json()['answered'] == 5
        assert client.delete(f"/v1/documents/{document['id']}", headers=headers).status_code == 204
        assert client.get(path, headers=headers).status_code == 404
    finally:
        client.__exit__(None, None, None)
