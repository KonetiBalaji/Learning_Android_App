from fastapi.testclient import TestClient


def test_service_root_is_a_safe_non_error_landing_response(monkeypatch, tmp_path):
    monkeypatch.setenv("LEARNING_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("LEARNING_JWT_SECRET", "test-secret-that-is-long-enough-32")
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "Learning API",
        "status": "ok",
        "health": "/health",
        "documentation": "/docs",
    }
