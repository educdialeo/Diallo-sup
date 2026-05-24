"""Tests du 11e type d'ingestion : daemon_uvicorn_health (sous-phase 3.4.C)."""

import pytest

from app.models import RawPush, SessionRecord

TS = "2026-05-24T09:00:00Z"


@pytest.fixture()
def etab_auth(make_establishment):
    etab = make_establishment("École Daemon")
    return etab, {"Authorization": f"Bearer {etab['api_key']}"}


def _payload(**overrides) -> dict:
    base = {
        "type": "daemon_uvicorn_health",
        "timestamp": TS,
        "uvicorn_status": "ok",
        "response_time_ms": 12,
        "http_status": 200,
        "consecutive_failures": 0,
        "daemon_uptime_seconds": 3600,
        "last_success_iso": "2026-05-24T08:59:00Z",
    }
    base.update(overrides)
    return base


def test_daemon_health_ok_is_202_and_logged_raw(client, etab_auth, db_session):
    etab, headers = etab_auth
    resp = client.post("/api/ingest", headers=headers, json=_payload())

    assert resp.status_code == 202
    assert resp.json()["type"] == "daemon_uvicorn_health"
    raws = (
        db_session.query(RawPush)
        .filter_by(etablissement_id=etab["id"], type="daemon_uvicorn_health")
        .all()
    )
    assert len(raws) == 1
    assert raws[0].payload["uvicorn_status"] == "ok"


def test_daemon_health_ko_with_null_fields_is_202(client, etab_auth):
    _, headers = etab_auth
    payload = _payload(
        uvicorn_status="ko",
        response_time_ms=None,
        http_status=None,
        consecutive_failures=3,
        last_success_iso=None,
    )
    assert client.post("/api/ingest", headers=headers, json=payload).status_code == 202


def test_daemon_health_unknown_is_202(client, etab_auth):
    _, headers = etab_auth
    payload = _payload(uvicorn_status="unknown", response_time_ms=None, http_status=None)
    assert client.post("/api/ingest", headers=headers, json=payload).status_code == 202


def test_daemon_health_invalid_status_is_422(client, etab_auth):
    _, headers = etab_auth
    resp = client.post("/api/ingest", headers=headers, json=_payload(uvicorn_status="lol"))
    assert resp.status_code == 422


def test_daemon_health_missing_required_field_is_422(client, etab_auth):
    _, headers = etab_auth
    payload = _payload()
    del payload["consecutive_failures"]
    resp = client.post("/api/ingest", headers=headers, json=payload)
    assert resp.status_code == 422


def test_daemon_health_extra_field_is_400(client, etab_auth):
    _, headers = etab_auth
    resp = client.post("/api/ingest", headers=headers, json=_payload(champ_en_trop="x"))
    assert resp.status_code == 400


def test_daemon_health_no_dedicated_table(client, etab_auth, db_session):
    etab, headers = etab_auth
    assert client.post("/api/ingest", headers=headers, json=_payload()).status_code == 202
    # Signal "status" : raw_pushes uniquement, aucune table dediee alimentee.
    assert db_session.query(SessionRecord).filter_by(etablissement_id=etab["id"]).count() == 0
