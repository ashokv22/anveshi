from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_direct_investigation():
    response = client.post("/api/v1/investigations", json={"identifier_type": "transaction_id", "identifier_value": "txn-123"})
    assert response.status_code == 200
    assert len(response.json()["events"]) == 2
    assert all(e["identifiers"]["transaction_id"] == "txn-123" for e in response.json()["events"])


def test_unknown_identifier():
    response = client.post("/api/v1/investigations", json={"identifier_type": "transaction_id", "identifier_value": "missing"})
    assert response.status_code == 200
    assert response.json()["events"] == []


def test_invalid_request():
    response = client.post("/api/v1/investigations", json={"identifier_type": "", "identifier_value": "txn-123"})
    assert response.status_code == 422
