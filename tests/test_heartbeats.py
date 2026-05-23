"""Tests de GET /api/establishments/{id}/heartbeats."""


def _auth(etab: dict) -> dict:
    return {"Authorization": f"Bearer {etab['api_key']}"}


def _heartbeat(status: str = "ok") -> dict:
    return {"type": "heartbeat", "timestamp": "2026-05-23T12:00:00Z", "status": status}


def test_get_heartbeats_returns_pushed_in_desc_order(client, make_establishment):
    etab = make_establishment("École Lecture")
    headers = _auth(etab)
    client.post("/api/ingest", headers=headers, json=_heartbeat("ok"))
    client.post("/api/ingest", headers=headers, json=_heartbeat("warning"))

    resp = client.get(f"/api/establishments/{etab['id']}/heartbeats", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    # Tri received_at DESC : le dernier pousse ("warning") arrive en tete.
    assert body[0]["status"] == "warning"
    assert body[1]["status"] == "ok"
    assert set(body[0]) == {"id", "timestamp", "status", "received_at"}


def test_get_heartbeats_of_other_establishment_is_403(client, make_establishment):
    etab_a = make_establishment("École A")
    etab_b = make_establishment("École B")

    # B tente de lire les heartbeats de A avec sa propre cle.
    resp = client.get(
        f"/api/establishments/{etab_a['id']}/heartbeats",
        headers=_auth(etab_b),
    )
    assert resp.status_code == 403


def test_get_heartbeats_respects_limit(client, make_establishment):
    etab = make_establishment("École Limite")
    headers = _auth(etab)
    for _ in range(5):
        client.post("/api/ingest", headers=headers, json=_heartbeat())

    resp = client.get(
        f"/api/establishments/{etab['id']}/heartbeats?limit=2", headers=headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2
