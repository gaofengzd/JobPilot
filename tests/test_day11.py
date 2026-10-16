from fastapi.testclient import TestClient

from app.api.main import create_app


def test_health_does_not_initialize_services() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "jobpilot-api", "version": "1.0.0"}


def test_vue_frontend_entry_exists() -> None:
    from pathlib import Path

    assert Path("frontend/src/App.vue").is_file()
