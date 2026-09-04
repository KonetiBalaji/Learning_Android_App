from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


def test_adaptive_mutations_replay_identical_results_without_duplicate_attempts(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post('/v1/mastery/diagnostics', headers=headers,
                              json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        session_id = started['id']
        path = f'/v1/mastery/sessions/{session_id}'

        diagnostic_body = {'expected_state': started['state_token'], 'selected_option': '1/2'}
        diagnostic = client.post(path + '/diagnostic-answer', headers=headers, json=diagnostic_body)
        assert diagnostic.status_code == 200
        assert client.post(path + '/diagnostic-answer', headers=headers, json=diagnostic_body).json() == diagnostic.json()
        assert client.post(path + '/diagnostic-answer', headers=headers,
                           json={**diagnostic_body, 'selected_option': '1'}).status_code == 409

        practice_body = {'expected_state': diagnostic.json()['state_token'], 'response': '6/8', 'fresh_practice': True}
        practice = client.post(path + '/practice', headers=headers, json=practice_body)
        assert practice.status_code == 200
        assert client.post(path + '/practice', headers=headers, json=practice_body).json() == practice.json()
        assert client.post(path + '/practice', headers=headers,
                           json={**practice_body, 'response': '7/8'}).status_code == 409

        rewrite_body = {
            'expected_state': practice.json()['state_token'],
            'response': 'Add the numerator parts while the common denominator stays the same, making one whole.',
            'fresh_practice': True,
        }
        rewrite = client.post(path + '/rewrite', headers=headers, json=rewrite_body)
        assert rewrite.status_code == 200
        assert client.post(path + '/rewrite', headers=headers, json=rewrite_body).json() == rewrite.json()
        assert client.post(path + '/rewrite', headers=headers,
                           json={**rewrite_body, 'response': 'Different delayed content'}).status_code == 409

        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM mastery_attempts WHERE session_id = ?', (session_id,)).fetchone()[0] == 3
            rows = db.execute(
                'SELECT operation, fingerprint, response_json FROM mastery_mutation_results WHERE session_id = ?',
                (session_id,),
            ).fetchall()
            assert {row['operation'] for row in rows} == {'diagnostic-answer', 'practice', 'rewrite'}
            assert all(len(row['fingerprint']) == 64 and row['response_json'] for row in rows)
    finally:
        client.__exit__(None, None, None)


def test_adaptive_replay_is_owner_scoped_and_deleted_with_session(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post('/v1/mastery/diagnostics', headers=headers,
                              json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        body = {'expected_state': started['state_token'], 'selected_option': '1'}
        route = f"/v1/mastery/sessions/{started['id']}/diagnostic-answer"
        assert client.post(route, headers=headers, json=body).status_code == 200

        other = client.post('/v1/auth/register', json={
            'email': 'idempotency-other@example.com', 'password': 'long-enough-password'}).json()['access_token']
        assert client.post(route, headers={'Authorization': f'Bearer {other}'}, json=body).status_code == 404
        assert client.delete('/v1/account', headers=headers).status_code == 204
        with connection(get_settings().database_path) as db:
            assert db.execute('SELECT COUNT(*) FROM mastery_mutation_results').fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)
