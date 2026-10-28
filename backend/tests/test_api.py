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
    result = response.json()
    assert [event["event_id"] for event in result["events"]] == ["evt-001", "evt-002", "evt-003"]
    assert [event["correlation_type"] for event in result["events"]] == [
        "direct",
        "discovered",
        "discovered",
    ]
    assert result["correlation_statistics"]["total_count"] == 3
    assert result["truncated"] is False
    assert result["status"] == "failures_detected"
    assert result["effective_time_window"]["duration_minutes"] == 15
    assert [event["event_id"] for event in result["timeline"]] == [
        "evt-001",
        "evt-002",
        "evt-003",
    ]
    assert result["findings"][0]["event_id"] == "evt-003"
    assert result["findings"][0]["evidence"] == [
        "severity=ERROR",
        "http.status_code=502 (HTTP 5xx)",
    ]
    assert "root cause is unknown" in result["summary"]


def test_unknown_identifier():
    response = client.post("/api/v1/investigations", json={"identifier_type": "transaction_id", "identifier_value": "missing"})
    assert response.status_code == 200
    assert response.json()["events"] == []
    assert response.json()["status"] == "no_events"


def test_invalid_request():
    response = client.post("/api/v1/investigations", json={"identifier_type": "", "identifier_value": "txn-123"})
    assert response.status_code == 422


def test_whitespace_request_is_invalid():
    response = client.post(
        "/api/v1/investigations",
        json={"identifier_type": " ", "identifier_value": "txn-123"},
    )
    assert response.status_code == 422


def test_naive_reference_timestamp_is_invalid():
    response = client.post(
        "/api/v1/investigations",
        json={
            "identifier_type": "transaction_id",
            "identifier_value": "txn-123",
            "reference_timestamp": "2026-10-28T10:15:00",
        },
    )
    assert response.status_code == 422
