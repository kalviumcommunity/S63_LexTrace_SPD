from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "project": "ChronoLex",
        "status": "running",
        "message": "ChronoLex API is initialized",
    }


def test_get_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }
