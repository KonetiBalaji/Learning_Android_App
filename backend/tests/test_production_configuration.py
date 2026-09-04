import pytest

from app.config import get_settings
from app.main import health


REVISION = 'a' * 40


def production_environment(monkeypatch, tmp_path):
    monkeypatch.setenv('LEARNING_ENVIRONMENT', 'production')
    monkeypatch.setenv('LEARNING_RUNTIME_DIR', str(tmp_path.resolve()))
    monkeypatch.setenv('LEARNING_JWT_SECRET', 'production-test-secret-at-least-32-characters')
    monkeypatch.setenv('LEARNING_RELEASE_REVISION', REVISION)
    monkeypatch.setenv('LEARNING_AI_MODE', 'openai')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-provider-key-never-used')


def test_complete_production_configuration_is_traceable(monkeypatch, tmp_path):
    production_environment(monkeypatch, tmp_path)
    settings = get_settings()
    assert settings.environment == 'production'
    assert settings.release_revision == REVISION
    assert settings.openai_api_key not in repr(settings)
    response = health(settings)
    assert response['environment'] == 'production' and response['revision'] == REVISION
    assert response['ai_provider'] == 'openai'


@pytest.mark.parametrize('missing, message', [
    ('LEARNING_JWT_SECRET', 'JWT secret'),
    ('LEARNING_RUNTIME_DIR', 'runtime directory'),
    ('LEARNING_RELEASE_REVISION', 'Git release revision'),
    ('OPENAI_API_KEY', 'reviewed OpenAI provider'),
])
def test_production_refuses_missing_release_inputs(monkeypatch, tmp_path, missing, message):
    production_environment(monkeypatch, tmp_path)
    monkeypatch.delenv(missing)
    with pytest.raises(ValueError, match=message):
        get_settings()


def test_staging_allows_deterministic_provider_but_requires_revision_and_secret(monkeypatch, tmp_path):
    monkeypatch.setenv('LEARNING_ENVIRONMENT', 'staging')
    monkeypatch.setenv('LEARNING_RUNTIME_DIR', str(tmp_path.resolve()))
    monkeypatch.setenv('LEARNING_JWT_SECRET', 'staging-test-secret-at-least-32-characters')
    monkeypatch.setenv('LEARNING_RELEASE_REVISION', REVISION)
    monkeypatch.setenv('LEARNING_AI_MODE', 'deterministic')
    assert get_settings().ai_mode == 'deterministic'


def test_unknown_environment_is_rejected(monkeypatch):
    monkeypatch.setenv('LEARNING_ENVIRONMENT', 'prod-ish')
    with pytest.raises(ValueError):
        get_settings()


@pytest.mark.parametrize('minutes', ['0', '43201'])
def test_unsafe_token_lifetime_is_rejected(monkeypatch, minutes):
    monkeypatch.setenv('LEARNING_TOKEN_MINUTES', minutes)
    with pytest.raises(ValueError, match='Token lifetime'):
        get_settings()


@pytest.mark.parametrize('name,value,message', [
    ('LEARNING_MAX_DOCUMENTS_PER_OWNER', '0', 'document count'),
    ('LEARNING_MAX_DOCUMENTS_PER_OWNER', '10001', 'document count'),
    ('LEARNING_MAX_UPLOAD_BYTES', '0', 'upload bytes'),
    ('LEARNING_MAX_UPLOAD_BYTES', str(1024 ** 3 + 1), 'upload bytes'),
    ('LEARNING_MAX_DOCUMENT_BYTES_PER_OWNER', str(1024), 'document bytes'),
    ('LEARNING_MAX_DOCUMENT_BYTES_PER_OWNER', str(1024 ** 4 + 1), 'document bytes'),
])
def test_unsafe_document_quota_is_rejected(monkeypatch, name, value, message):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=message):
        get_settings()


@pytest.mark.parametrize('days', ['0', '366'])
def test_unsafe_guardian_invitation_retention_is_rejected(monkeypatch, days):
    monkeypatch.setenv('LEARNING_GUARDIAN_INVITATION_RETENTION_DAYS', days)
    with pytest.raises(ValueError, match='Guardian invitation retention'):
        get_settings()
