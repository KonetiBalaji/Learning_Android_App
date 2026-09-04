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
