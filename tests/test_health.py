from fastapi.testclient import TestClient

from pidm.app import app


def test_health_returns_200():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
