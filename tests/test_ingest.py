"""Tests de l'endpoint POST /api/ingest (auth API key + reception heartbeat)."""

HEARTBEAT = {"type": "heartbeat", "timestamp": "2026-05-23T12:00:00Z", "status": "ok"}


def test_ingest_without_auth_is_401(client):
    resp = client.post("/api/ingest", json=HEARTBEAT)
    assert resp.status_code == 401


def test_ingest_with_bad_key_is_401(client):
    resp = client.post(
        "/api/ingest",
        headers={"Authorization": "Bearer not-a-real-key"},
        json=HEARTBEAT,
    )
    assert resp.status_code == 401


def test_ingest_with_valid_key_is_202(client, make_establishment):
    etab = make_establishment("École Ingest")
    resp = client.post(
        "/api/ingest",
        headers={"Authorization": f"Bearer {etab['api_key']}"},
        json=HEARTBEAT,
    )
    assert resp.status_code == 202
    assert "received_at" in resp.json()
