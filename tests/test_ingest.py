"""Test du stub /api/ingest : doit repondre 501 tant que non implemente."""


def test_ingest_not_implemented(client):
    response = client.post("/api/ingest")
    assert response.status_code == 501
