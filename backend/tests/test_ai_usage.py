from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.ai_usage import consume_ai_operation
from app.config import Settings
from app.database import connection, initialize


def settings(tmp_path, *, mode='openai', limit=2):
    return Settings(runtime_dir=tmp_path, jwt_secret='secret', ai_mode=mode,
                    max_ai_operations_per_owner_per_day=limit)


def users(config):
    initialize(config.database_path)
    with connection(config.database_path) as db:
        for owner in ('one', 'two'):
            db.execute('INSERT INTO users(id,email,password_hash,created_at) VALUES(?,?,?,?)',
                       (owner, f'{owner}@example.com', 'hash', 'now'))


def test_daily_ai_limit_is_owner_scoped_and_returns_retry_guidance(tmp_path):
    config = settings(tmp_path)
    users(config)
    at = datetime(2026, 9, 5, 23, 59, 30, tzinfo=UTC)
    consume_ai_operation(config, 'one', at=at)
    consume_ai_operation(config, 'one', at=at)
    consume_ai_operation(config, 'two', at=at)
    with pytest.raises(HTTPException) as failure:
        consume_ai_operation(config, 'one', at=at)
    assert failure.value.status_code == 429
    assert failure.value.headers == {'Retry-After': '30', 'X-Learning-Error': 'daily_ai_limit'}
    assert 'tomorrow' in failure.value.detail
    consume_ai_operation(config, 'one', at=datetime(2026, 9, 6, tzinfo=UTC))


def test_deterministic_operations_do_not_consume_provider_quota(tmp_path):
    config = settings(tmp_path, mode='deterministic', limit=1)
    users(config)
    consume_ai_operation(config, 'one')
    with connection(config.database_path) as db:
        assert db.execute('SELECT COUNT(*) FROM ai_usage_days').fetchone()[0] == 0


@pytest.mark.parametrize('limit', [0, 100_001])
def test_unsafe_daily_ai_limits_are_rejected(tmp_path, limit):
    with pytest.raises(ValueError, match='Daily per-owner AI operation limit'):
        settings(tmp_path, limit=limit)


def test_diagnostic_admission_is_limited_before_provider_work_and_owner_scoped(monkeypatch, tmp_path):
    monkeypatch.setenv('LEARNING_AI_MODE', 'openai')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic')
    monkeypatch.setenv('LEARNING_MAX_AI_OPERATIONS_PER_OWNER_PER_DAY', '1')
    from test_mastery_loop import registered_client
    from app import main
    from app.tutor_provider import DeterministicTutorProvider

    calls = []
    provider = DeterministicTutorProvider()
    original = provider.diagnostic_bank
    provider.diagnostic_bank = lambda *args: (calls.append(args), original(*args))[1]
    monkeypatch.setattr(main, 'tutor_provider', lambda settings, interests=(): provider)
    client, headers = registered_client(monkeypatch, tmp_path)
    body = {'grade': 8, 'subject_id': 'math', 'chapter_id': 'fractions'}
    try:
        assert client.post('/v1/mastery/diagnostics', headers=headers, json=body).status_code == 201
        limited = client.post('/v1/mastery/diagnostics', headers=headers, json=body)
        assert limited.status_code == 429
        assert int(limited.headers['Retry-After']) in range(1, 86_401)
        assert len(calls) == 1
        other = client.post('/v1/auth/register', json={
            'email': 'other-ai-quota@example.com', 'password': 'long-enough-password'}).json()['access_token']
        assert client.post('/v1/mastery/diagnostics', headers={'Authorization': f'Bearer {other}'}, json=body).status_code == 201
        assert len(calls) == 2
    finally:
        client.__exit__(None, None, None)
