import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from google.oauth2 import id_token
from google.auth.exceptions import TransportError

from app.config import get_settings
from app.database import connection
from test_mastery_loop import registered_client


@pytest.fixture
def google(monkeypatch, tmp_path):
    monkeypatch.setenv('LEARNING_GOOGLE_CLIENT_ID', 'fixture.apps.googleusercontent.com')
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    # Mock only Google's certificate network boundary; exercise real signature,
    # expiry, issuer and audience verification with locally signed test tokens.
    monkeypatch.setattr(id_token, '_fetch_certs', lambda *a, **k: {'fixture-key': public})
    client, owner = registered_client(monkeypatch, tmp_path)
    def token(**changes):
        now = int(time.time())
        claims = dict(iss='https://accounts.google.com', aud='fixture.apps.googleusercontent.com',
                      sub='google-fixture-subject', email='google-learner@gmail.com', email_verified=True,
                      iat=now, exp=now + 600)
        claims.update(changes)
        return jwt.encode(claims, key, algorithm='RS256', headers={'kid': 'fixture-key'})
    yield client, owner, token
    client.__exit__(None, None, None)


def test_google_creates_one_account_and_subject_survives_email_change(google):
    client, _, token = google
    first = client.post('/v1/auth/google', json={'id_token': token()})
    assert first.status_code == 200, first.text
    second = client.post('/v1/auth/google', json={'id_token': token(email='changed@gmail.com')})
    assert second.status_code == 200
    first_id = jwt.decode(first.json()['access_token'], options={'verify_signature': False})['sub']
    assert jwt.decode(second.json()['access_token'], options={'verify_signature': False})['sub'] == first_id
    with connection(get_settings().database_path) as db:
        assert db.execute('SELECT COUNT(*) FROM google_accounts').fetchone()[0] == 1
        assert db.execute('SELECT email FROM users WHERE id = ?', (first_id,)).fetchone()[0] == 'google-learner@gmail.com'
    assert client.post('/v1/auth/login', json={'email': 'google-learner@gmail.com', 'password': 'long-enough-password'}).status_code == 401
    headers = {'Authorization': f"Bearer {first.json()['access_token']}"}
    assert client.get('/v1/documents', headers=headers).status_code == 200
    assert client.delete('/v1/account', headers=headers).status_code == 204
    assert client.get('/v1/documents', headers=headers).status_code == 401
    with connection(get_settings().database_path) as db:
        assert db.execute('SELECT COUNT(*) FROM google_accounts').fetchone()[0] == 0


@pytest.mark.parametrize('changes', [
    {'aud': 'other-client'}, {'iss': 'https://attacker.invalid'}, {'exp': 1},
    {'iat': 4102444800}, {'sub': ''}, {'sub': 123}, {'email_verified': False},
    {'email_verified': 'true'}, {'email': 'invalid'},
])
def test_bad_claims_never_create_an_identity(google, changes):
    client, _, token = google
    response = client.post('/v1/auth/google', json={'id_token': token(**changes)})
    assert response.status_code == 401
    assert response.json() == {'detail': 'Invalid Google sign-in token'}
    with connection(get_settings().database_path) as db:
        assert db.execute('SELECT COUNT(*) FROM google_accounts').fetchone()[0] == 0


def test_bad_signature_disabled_config_and_provider_failure(google, monkeypatch):
    client, _, token = google
    good = token()
    header, payload, signature = good.split('.')
    changed = ('A' if signature[0] != 'A' else 'B') + signature[1:]
    assert client.post('/v1/auth/google', json={'id_token': '.'.join([header, payload, changed])}).status_code == 401
    monkeypatch.delenv('LEARNING_GOOGLE_CLIENT_ID')
    assert client.post('/v1/auth/google', json={'id_token': good}).status_code == 503
    monkeypatch.setenv('LEARNING_GOOGLE_CLIENT_ID', 'fixture.apps.googleusercontent.com')
    def unavailable(*args, **kwargs):
        raise TransportError('synthetic-private-provider-message')
    monkeypatch.setattr(id_token, '_fetch_certs', unavailable)
    response = client.post('/v1/auth/google', json={'id_token': good})
    assert response.status_code == 503 and 'synthetic-private' not in response.text


def test_email_collision_cannot_link_existing_password_account(google):
    client, _, token = google
    email = 'collision@example.com'
    assert client.post('/v1/auth/register', json={'email': email, 'password': 'long-enough-password'}).status_code == 201
    assert client.post('/v1/auth/google', json={'id_token': token(email=email)}).status_code == 409
    with connection(get_settings().database_path) as db:
        assert db.execute('SELECT COUNT(*) FROM google_accounts').fetchone()[0] == 0
