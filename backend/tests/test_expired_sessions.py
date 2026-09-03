from datetime import UTC, datetime, timedelta

import jwt

from test_mastery_loop import registered_client


def test_expired_session_cannot_read_mutate_or_delete_and_login_restores_progress(monkeypatch, tmp_path):
    client, headers = registered_client(monkeypatch, tmp_path)
    try:
        started = client.post('/v1/mastery/diagnostics', headers=headers,
                              json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}).json()
        path = f"/v1/mastery/sessions/{started['id']}"
        assert client.post(path + '/diagnostic-answer', headers=headers,
                           json={'selected_option': '1/2'}).status_code == 200
        before = client.get(path, headers=headers).json()
        from app.config import get_settings
        settings = get_settings()
        claims = jwt.decode(headers['Authorization'].removeprefix('Bearer '), settings.jwt_secret,
                            algorithms=['HS256'], issuer=settings.jwt_issuer)
        claims['exp'] = datetime.now(UTC) - timedelta(seconds=1)
        expired = {'Authorization': 'Bearer ' + jwt.encode(claims, settings.jwt_secret, algorithm='HS256')}
        assert client.get(path, headers=expired).status_code == 401
        assert client.get('/v1/progress/dashboard?grade=8', headers=expired).status_code == 401
        assert client.post(path + '/practice', headers=expired, json={'response': '6/8'}).status_code == 401
        assert client.delete('/v1/account', headers=expired).status_code == 401
        login = client.post('/v1/auth/login', json={'email': f'student-{tmp_path.name}@example.com',
                                                  'password': 'long-enough-password'})
        assert login.status_code == 200
        renewed = {'Authorization': f"Bearer {login.json()['access_token']}"}
        assert client.get(path, headers=renewed).json() == before
        assert client.post(path + '/practice', headers=renewed, json={'response': '6/8'}).status_code == 200
        assert client.get(path, headers=renewed).json()['status'] == 'rewrite'
    finally:
        client.__exit__(None, None, None)
