"""Tests d'ingestion des 10 types du payload N1 (202 + stockage hybride)."""

import pytest

from app.models import Heartbeat, Incident, RawPush, Report, SessionRecord

TS = "2026-05-23T14:00:00Z"

PAYLOADS: dict[str, dict] = {
    "heartbeat": {"type": "heartbeat", "timestamp": TS, "status": "ok"},
    "sante_systeme": {
        "type": "sante_systeme",
        "timestamp": TS,
        "status_global": "up",
        "uptime_seconds": 100000,
        "mac_serial": "C02ABC123",
        "cpu_percent": 12.5,
        "ram_used_mb": 8000,
        "ram_total_mb": 24000,
        "disk_used_gb": 120.0,
        "disk_total_gb": 460.0,
        "temperature_celsius": 45.0,
    },
    "ollama_status": {
        "type": "ollama_status",
        "timestamp": TS,
        "models_loaded": ["llama3.2", "llama-guard"],
        "ping_latency_ms": 12.0,
        "ram_used_mb": 6000,
        "last_inference_at": TS,
    },
    "dialeo_status": {
        "type": "dialeo_status",
        "timestamp": TS,
        "version": "1.4.0",
        "uvicorn_status": "up",
        "modes_active": ["maitre", "eleve"],
    },
    "sessions_live": {
        "type": "sessions_live",
        "timestamp": TS,
        "nb_classes_active": 3,
        "nb_eleves_connected": 42,
        "modes_in_use": ["dialogue"],
    },
    "sessions_historiques": {
        "type": "sessions_historiques",
        "timestamp": TS,
        "granularite": "jour",
        "periode": "2026-05-22",
        "nb_sessions": 12,
        "nb_eleves": 210,
        "duree_moyenne_min": 34.5,
        "modes_utilises": ["dialogue", "quiz"],
    },
    "incidents_moderation": {
        "type": "incidents_moderation",
        "timestamp": TS,
        "window_start": TS,
        "window_end": TS,
        "nb_refus_blacklist": 2,
        "nb_refus_llamaguard": 1,
        "nb_refus_systemprompt": 0,
    },
    "reports": {
        "type": "reports",
        "timestamp": TS,
        "reports": [
            {
                "date_jour": "2026-05-22",
                "question": "Pourquoi le ciel est bleu ?",
                "reponse": "À cause de la diffusion de la lumière.",
                "mode_pedagogique": "dialogue",
                "niveau_scolaire": ["CM1", "CM2"],
                "note_enseignant": "bonne question",
            }
        ],
    },
    "logs_critiques": {
        "type": "logs_critiques",
        "timestamp": TS,
        "logs": [
            {
                "niveau": "ERROR",
                "message": "ollama timeout",
                "timestamp": TS,
                "contexte": {"module": "ollama"},
            }
        ],
    },
    "inventaire": {
        "type": "inventaire",
        "timestamp": TS,
        "mac_mini_model": "Mac mini M4",
        "macos_version": "15.5",
        "capacite_declaree_sieges": 30,
        "formule_commerciale": "école",
        "last_changed_at": TS,
    },
}


@pytest.fixture()
def etab_auth(make_establishment):
    etab = make_establishment("École Types")
    return etab, {"Authorization": f"Bearer {etab['api_key']}"}


@pytest.mark.parametrize("ptype", list(PAYLOADS))
def test_ingest_each_type_is_202_and_logged_raw(ptype, client, etab_auth, db_session):
    etab, headers = etab_auth
    resp = client.post("/api/ingest", headers=headers, json=PAYLOADS[ptype])

    assert resp.status_code == 202, resp.text
    assert resp.json()["type"] == ptype
    # Tout push est consigne dans raw_pushes, sans exception.
    raws = (
        db_session.query(RawPush)
        .filter_by(etablissement_id=etab["id"], type=ptype)
        .all()
    )
    assert len(raws) == 1
    assert raws[0].payload["type"] == ptype


def test_dedicated_tables_are_populated(client, etab_auth, db_session):
    etab, headers = etab_auth
    for ptype in (
        "heartbeat",
        "sessions_live",
        "sessions_historiques",
        "incidents_moderation",
        "reports",
    ):
        assert client.post("/api/ingest", headers=headers, json=PAYLOADS[ptype]).status_code == 202

    eid = etab["id"]
    assert db_session.query(Heartbeat).filter_by(etablissement_id=eid).count() == 1
    assert db_session.query(SessionRecord).filter_by(etablissement_id=eid, kind="live").count() == 1
    assert (
        db_session.query(SessionRecord).filter_by(etablissement_id=eid, kind="historique").count()
        == 1
    )
    assert db_session.query(Incident).filter_by(etablissement_id=eid).count() == 1
    assert db_session.query(Report).filter_by(etablissement_id=eid).count() == 1


def test_non_dedicated_type_stays_in_raw_only(client, etab_auth, db_session):
    etab, headers = etab_auth
    resp = client.post("/api/ingest", headers=headers, json=PAYLOADS["ollama_status"])
    assert resp.status_code == 202

    eid = etab["id"]
    raw_count = (
        db_session.query(RawPush).filter_by(etablissement_id=eid, type="ollama_status").count()
    )
    assert raw_count == 1
    # Aucune table dediee n'est alimentee pour ce type.
    assert db_session.query(Heartbeat).filter_by(etablissement_id=eid).count() == 0
    assert db_session.query(SessionRecord).filter_by(etablissement_id=eid).count() == 0


def test_unknown_type_is_422(client, etab_auth):
    _, headers = etab_auth
    resp = client.post(
        "/api/ingest", headers=headers, json={"type": "inconnu", "timestamp": TS}
    )
    assert resp.status_code == 422
