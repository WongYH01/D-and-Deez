from fastapi.testclient import TestClient

from pidm.app import create_app

from conftest import FakeClaude


def test_health_returns_200(factory, tmp_path):
    app = create_app(factory, turn_client=FakeClaude(), plan_client=FakeClaude(), recap_client=FakeClaude(),
                     backup_dir=tmp_path)
    assert TestClient(app).get("/health").status_code == 200
