from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient


PASSWORD = 'long-enough-password'


def configured_client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv('LEARNING_RUNTIME_DIR', str(tmp_path / 'runtime'))
    monkeypatch.setenv('LEARNING_JWT_SECRET', 'test-secret-that-is-long-enough-32')
    from app.main import app
    client = TestClient(app)
    client.__enter__()
    return client


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post('/v1/auth/register', json={'email': email, 'password': PASSWORD})
    assert response.status_code == 201, response.text
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def profile(client: TestClient, headers: dict[str, str]) -> dict:
    return client.get('/v1/account', headers=headers).json()


def test_invitation_is_single_use_hashed_and_replaced(monkeypatch, tmp_path: Path) -> None:
    client = configured_client(monkeypatch, tmp_path)
    try:
        learner = register(client, 'learner@example.com')
        guardian = register(client, 'guardian@example.com')
        first = client.post('/v1/guardian/invitations', headers=learner).json()
        second = client.post('/v1/guardian/invitations', headers=learner).json()
        assert first['code'] != second['code']
        assert datetime.fromisoformat(second['expires_at']) > datetime.now(UTC)

        database = tmp_path / 'runtime' / 'learning.sqlite3'
        with sqlite3.connect(database) as db:
            stored = db.execute('SELECT code_digest FROM guardian_invitations').fetchall()
        assert len(stored) == 1
        assert second['code'] not in stored[0][0]
        assert len(stored[0][0]) == 64

        assert client.post('/v1/guardian/links', headers=guardian,
                           json={'code': first['code']}).status_code == 404
        linked = client.post('/v1/guardian/links', headers=guardian,
                             json={'code': second['code']})
        assert linked.status_code == 201, linked.text
        assert linked.json()['email'] == 'learner@example.com'
        assert client.post('/v1/guardian/links', headers=guardian,
                           json={'code': second['code']}).status_code == 404
    finally:
        client.__exit__(None, None, None)


def test_linked_guardian_has_only_read_only_report_access(monkeypatch, tmp_path: Path) -> None:
    client = configured_client(monkeypatch, tmp_path)
    try:
        learner = register(client, 'learner@example.com')
        guardian = register(client, 'guardian@example.com')
        outsider = register(client, 'outsider@example.com')
        learner_id = profile(client, learner)['id']
        invitation = client.post('/v1/guardian/invitations', headers=learner).json()
        assert client.post('/v1/guardian/links', headers=guardian,
                           json={'code': invitation['code']}).status_code == 201

        started = client.post('/v1/mastery/diagnostics', headers=learner,
                              json={'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'})
        assert started.status_code == 201
        session_id = started.json()['id']
        student_dashboard = client.get('/v1/progress/dashboard?grade=8', headers=learner).json()
        guardian_dashboard = client.get(
            f'/v1/guardian/learners/{learner_id}/progress/dashboard?grade=8', headers=guardian)
        assert guardian_dashboard.status_code == 200
        assert guardian_dashboard.json() == student_dashboard
        assert client.get(
            f'/v1/guardian/learners/{learner_id}/progress/weekly-report?grade=8',
            headers=guardian).status_code == 200
        assert client.get(f'/v1/mastery/sessions/{session_id}', headers=guardian).status_code == 404
        assert client.get('/v1/documents', headers=guardian).json() == []
        assert client.get(
            f'/v1/guardian/learners/{learner_id}/progress/dashboard?grade=8',
            headers=outsider).status_code == 404
        assert client.get('/v1/guardian/learners', headers=guardian).json()[0]['id'] == learner_id
        assert client.get('/v1/guardian/access', headers=learner).json()[0]['email'] == 'guardian@example.com'
    finally:
        client.__exit__(None, None, None)


def test_learner_revocation_immediately_removes_report_access(monkeypatch, tmp_path: Path) -> None:
    client = configured_client(monkeypatch, tmp_path)
    try:
        learner = register(client, 'learner@example.com')
        guardian = register(client, 'guardian@example.com')
        learner_id = profile(client, learner)['id']
        guardian_id = profile(client, guardian)['id']
        code = client.post('/v1/guardian/invitations', headers=learner).json()['code']
        client.post('/v1/guardian/links', headers=guardian, json={'code': code})

        revoked = client.delete(f'/v1/guardian/access/{guardian_id}', headers=learner)
        assert revoked.status_code == 204
        assert client.get('/v1/guardian/access', headers=learner).json() == []
        assert client.get('/v1/guardian/learners', headers=guardian).json() == []
        assert client.get(
            f'/v1/guardian/learners/{learner_id}/progress/dashboard?grade=8',
            headers=guardian).status_code == 404
        assert client.delete(f'/v1/guardian/access/{guardian_id}', headers=learner).status_code == 404
        history = client.get('/v1/guardian/access-history', headers=learner).json()
        assert [event['event_type'] for event in history] == ['granted', 'revoked_by_learner']
        assert all(event['guardian_id'] == guardian_id for event in history)
        assert all(event['guardian_email'] == 'guardian@example.com' for event in history)
    finally:
        client.__exit__(None, None, None)


def test_guardian_revocation_is_recorded_but_history_is_learner_only(monkeypatch, tmp_path: Path) -> None:
    client = configured_client(monkeypatch, tmp_path)
    try:
        learner = register(client, 'learner@example.com')
        guardian = register(client, 'guardian@example.com')
        learner_id = profile(client, learner)['id']
        code = client.post('/v1/guardian/invitations', headers=learner).json()['code']
        assert client.post('/v1/guardian/links', headers=guardian, json={'code': code}).status_code == 201
        assert client.delete(f'/v1/guardian/learners/{learner_id}', headers=guardian).status_code == 204
        assert client.get('/v1/guardian/access-history', headers=guardian).json() == []
        history = client.get('/v1/guardian/access-history', headers=learner).json()
        assert [event['event_type'] for event in history] == ['granted', 'revoked_by_guardian']
    finally:
        client.__exit__(None, None, None)


def test_access_history_minimizes_deleted_guardian_identity_and_cascades_with_learner(monkeypatch, tmp_path: Path) -> None:
    client = configured_client(monkeypatch, tmp_path)
    try:
        learner = register(client, 'learner@example.com')
        guardian = register(client, 'guardian@example.com')
        learner_id = profile(client, learner)['id']
        code = client.post('/v1/guardian/invitations', headers=learner).json()['code']
        assert client.post('/v1/guardian/links', headers=guardian, json={'code': code}).status_code == 201

        assert client.delete('/v1/account', headers=guardian).status_code == 204
        history = client.get('/v1/guardian/access-history', headers=learner).json()
        assert [event['event_type'] for event in history] == ['granted', 'revoked_by_guardian']
        assert all(event['guardian_id'] is None for event in history)
        assert all(event['guardian_email'] is None for event in history)

        assert client.delete('/v1/account', headers=learner).status_code == 204
        with sqlite3.connect(tmp_path / 'runtime' / 'learning.sqlite3') as db:
            assert db.execute('SELECT * FROM guardian_access_events WHERE learner_id = ?',
                              (learner_id,)).fetchall() == []
    finally:
        client.__exit__(None, None, None)


def test_expired_self_and_deleted_account_links_fail_closed(monkeypatch, tmp_path: Path) -> None:
    client = configured_client(monkeypatch, tmp_path)
    try:
        learner = register(client, 'learner@example.com')
        guardian = register(client, 'guardian@example.com')
        learner_id = profile(client, learner)['id']

        self_code = client.post('/v1/guardian/invitations', headers=learner).json()['code']
        assert client.post('/v1/guardian/links', headers=learner,
                           json={'code': self_code}).status_code == 422
        expired = client.post('/v1/guardian/invitations', headers=learner).json()['code']
        database = tmp_path / 'runtime' / 'learning.sqlite3'
        with sqlite3.connect(database) as db:
            db.execute('UPDATE guardian_invitations SET expires_at = ?',
                       ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(),))
        assert client.post('/v1/guardian/links', headers=guardian,
                           json={'code': expired}).status_code == 404

        active = client.post('/v1/guardian/invitations', headers=learner).json()['code']
        assert client.post('/v1/guardian/links', headers=guardian,
                           json={'code': active}).status_code == 201
        assert client.delete('/v1/account', headers=learner).status_code == 204
        assert client.get('/v1/guardian/learners', headers=guardian).json() == []
        assert client.get(
            f'/v1/guardian/learners/{learner_id}/progress/dashboard?grade=8',
            headers=guardian).status_code == 404
    finally:
        client.__exit__(None, None, None)


def test_invitation_retention_removes_only_rows_past_policy(monkeypatch, tmp_path: Path) -> None:
    client = configured_client(monkeypatch, tmp_path)
    try:
        learner = register(client, 'learner@example.com')
        learner_id = profile(client, learner)['id']
        reference = datetime(2026, 9, 4, tzinfo=UTC)
        database = tmp_path / 'runtime' / 'learning.sqlite3'
        with sqlite3.connect(database) as db:
            db.executemany(
                '''INSERT INTO guardian_invitations
                   (id, learner_id, code_digest, expires_at, created_at, redeemed_at)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                [
                    ('old', learner_id, 'a' * 64, (reference - timedelta(days=31)).isoformat(),
                     (reference - timedelta(days=32)).isoformat(), (reference - timedelta(days=31)).isoformat()),
                    ('kept', learner_id, 'b' * 64, (reference - timedelta(days=29)).isoformat(),
                     (reference - timedelta(days=30)).isoformat(), (reference - timedelta(days=29)).isoformat()),
                ],
            )
        from app.config import get_settings
        from app.guardian_access import cleanup_invitations
        assert cleanup_invitations(get_settings(), reference) == 1
        with sqlite3.connect(database) as db:
            assert db.execute('SELECT id FROM guardian_invitations').fetchall() == [('kept',)]
    finally:
        client.__exit__(None, None, None)
