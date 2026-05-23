"""Tests de l'endpoint POST /api/establishments."""


def test_create_establishment_returns_api_key_once(client):
    resp = client.post("/api/establishments", json={"name": "École Saint-Pierre"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] >= 1
    assert body["name"] == "École Saint-Pierre"
    assert isinstance(body["api_key"], str) and len(body["api_key"]) >= 40
    assert "created_at" in body


def test_create_establishment_duplicate_name_is_409(client):
    client.post("/api/establishments", json={"name": "École Doublon"})
    resp = client.post("/api/establishments", json={"name": "École Doublon"})

    assert resp.status_code == 409
