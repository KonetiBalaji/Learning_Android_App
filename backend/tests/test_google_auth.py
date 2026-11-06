import json
import time
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from google.auth import crypt, jwt

from study import api


AUDIENCE = "test.apps.googleusercontent.com"


@pytest.fixture
def google(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDY_GOOGLE_CLIENT_ID", AUDIENCE)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.PEM,
                                           serialization.PublicFormat.SubjectPublicKeyInfo)
    signer = crypt.RSASigner.from_string(private, key_id="test-key")
    certs = json.dumps({"test-key": public.decode()}).encode()
    monkeypatch.setattr(api, "GoogleRequest", lambda: lambda *args, **kwargs: SimpleNamespace(status=200, data=certs))

    def issue(**claims):
        now = int(time.time())
        payload = {"iss": "https://accounts.google.com", "aud": AUDIENCE, "sub": "google-account-a",
                   "iat": now - 1, "exp": now + 300, **claims}
        return jwt.encode(signer, payload).decode()

    app = api.create_app(tmp_path)
    with TestClient(app) as client:
        yield client, app.state.store, issue


def challenge(client):
    reply = client.post("/auth/google/challenge")
    assert reply.status_code == 200
    assert reply.json()["client_id"] == AUDIENCE
    return reply.json()["nonce"]


def sign_in(client, token):
    return client.post("/auth/google", json={"id_token": token})


def authorization(reply):
    return {"Authorization": "Bearer " + reply.json()["token"]}


def test_google_account_reuses_subject_keeps_owners_separate_and_revokes_sessions(google):
    client, store, issue = google
    password_account = client.post("/auth/register", json={"username": "account", "password": "disposable-password"})
    first = sign_in(client, issue(nonce=challenge(client), email="account@example.test"))
    assert first.status_code == 200
    first_owner = first.json()["owner_id"]
    assert first_owner != password_account.json()["owner_id"]
    first_auth = authorization(first)
    document = client.post("/documents", headers=first_auth,
                           files={"file": ("cells.txt", b"Cells use energy from cellular respiration.")})
    assert document.status_code == 201

    other = sign_in(client, issue(nonce=challenge(client), sub="google-account-b", email="account@example.test"))
    assert other.status_code == 200
    assert other.json()["owner_id"] != first_owner
    assert client.get("/documents/" + document.json()["id"], headers=authorization(other)).status_code == 404
    assert client.delete("/auth/session", headers=first_auth).status_code == 204
    assert client.get("/account", headers=first_auth).status_code == 401

    again = sign_in(client, issue(nonce=challenge(client), email="changed@example.test"))
    assert again.status_code == 200
    assert again.json()["owner_id"] == first_owner
    assert client.delete("/account", headers=authorization(again)).status_code == 204
    assert store.db.execute("SELECT owner FROM google_accounts WHERE owner=?", (first_owner,)).fetchone() is None
    assert client.get("/account", headers=authorization(again)).status_code == 401


@pytest.mark.parametrize("claims", [{"aud": "wrong"}, {"exp": 1}, {"iss": "https://invalid.example"}, {"nonce": "x" * 43}])
def test_google_rejects_invalid_claims(google, claims):
    client, _, issue = google
    token = issue(**({"nonce": challenge(client)} | claims))
    reply = sign_in(client, token)
    assert reply.status_code == 401
    assert token not in reply.text


def test_google_rejects_bad_signature_replay_and_expired_challenge(google):
    client, store, issue = google
    nonce = challenge(client)
    token = issue(nonce=nonce)
    prefix, signature = token.rsplit(".", 1)
    corrupted = prefix + "." + ("B" if signature[0] == "A" else "A") + signature[1:]
    assert sign_in(client, corrupted).status_code == 401
    assert sign_in(client, token).status_code == 200
    assert sign_in(client, token).status_code == 401
    expired = issue(nonce=challenge(client))
    with store.db:
        store.db.execute("UPDATE google_challenges SET expires=0")
    assert sign_in(client, expired).status_code == 401


def test_google_is_disabled_without_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("STUDY_GOOGLE_CLIENT_ID", raising=False)
    with TestClient(api.create_app(tmp_path)) as client:
        assert client.post("/auth/google/challenge").status_code == 503
        assert sign_in(client, "unused-token").status_code == 503
