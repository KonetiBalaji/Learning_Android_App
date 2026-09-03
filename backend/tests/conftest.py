import pytest


@pytest.fixture(autouse=True)
def deterministic_ai(monkeypatch):
    """Unit and API tests never spend API credits or depend on external availability."""
    monkeypatch.setenv("LEARNING_AI_MODE", "deterministic")
