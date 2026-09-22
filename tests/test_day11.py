from fastapi.testclient import TestClient

from app.api.main import create_app


def test_health_does_not_initialize_services() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "jobpilot-api", "version": "1.0.0"}


def test_ui_module_compiles() -> None:
    source = open("ui/app.py", encoding="utf-8").read()
    compile(source, "ui/app.py", "exec")
