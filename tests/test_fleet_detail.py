"""Tests HTTP de GET /api/fleet/{id} (chantier N1 etape 2, page detail)."""

from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.models import Heartbeat, Incident, RawPush
from app.scripts.create_admin import create_admin

_ADMIN_EMAIL = "admin@example.com"
_ADMIN_PWD = "passphrase-longue-ok"


@pytest.fixture(autouse=True)
def _secrets(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "test-jwt-" + "x" * 24)
    monkeypatch.setattr(settings, "totp_at_rest_key", Fernet.generate_key().decode("utf-8"))


def _enroll_full(client, db_session) -> None:
    create_admin(_ADMIN_EMAIL, _ADMIN_PWD, db_session)
    assert client.post(
        "/api/auth/login", json={"email": _ADMIN_EMAIL, "password": _ADMIN_PWD}
    ).status_code == 200
    uri = client.post("/api/auth/totp/enroll").json()["otpauth_uri"]
    secret = uri.split("secret=")[1].split("&")[0]
    assert client.post(
        "/api/auth/totp/confirm", json={"code": pyotp.TOTP(secret).now()}
    ).status_code == 200


# --- Verrouillage / 404 ----------------------------------------------------


def test_detail_without_session_is_401(client):
    assert client.get("/api/fleet/1").status_code == 401


def test_detail_with_preauth_only_is_401(client, db_session):
    create_admin(_ADMIN_EMAIL, _ADMIN_PWD, db_session)
    client.post("/api/auth/login", json={"email": _ADMIN_EMAIL, "password": _ADMIN_PWD})
    # Pre_auth seul -> 401
    assert client.get("/api/fleet/1").status_code == 401


def test_detail_unknown_etab_is_404(client, db_session):
    _enroll_full(client, db_session)
    r = client.get("/api/fleet/9999")
    assert r.status_code == 404
    assert "introuvable" in r.json()["detail"].lower()


# --- Structure -------------------------------------------------------------


def test_detail_returns_full_shape_for_empty_etab(client, db_session, make_establishment):
    """Sans aucune donnee, tous les sous-objets existent mais sont vides/None."""
    etab = make_establishment("École Vide")
    _enroll_full(client, db_session)
    r = client.get(f"/api/fleet/{etab['id']}")
    assert r.status_code == 200
    body = r.json()
    # Identite
    assert body["id"] == etab["id"]
    assert body["name"] == "École Vide"
    # Sante : pas de heartbeat -> silent
    assert body["health"] == "silent"
    assert body["last_heartbeat_at"] is None
    # Snapshots tous presents, last_seen_at None.
    for key in ("machine", "ollama", "dialeo", "daemon"):
        assert body[key]["last_seen_at"] is None
    # Listes vides
    assert body["incidents_recent"] == []
    # Historique : 30 entrees zero
    assert len(body["usage_history"]) == 30
    assert all(d["nb_sessions"] == 0 for d in body["usage_history"])


# --- Parsing snapshots depuis raw_pushes ----------------------------------


def test_detail_parses_machine_health_from_sante_systeme_payload(
    client, db_session, make_establishment
):
    etab = make_establishment("École Machine")
    now = datetime.now(UTC)
    db_session.add(RawPush(
        etablissement_id=etab["id"],
        type="sante_systeme",
        timestamp_client=now, received_at=now,
        payload={
            "type": "sante_systeme",
            "timestamp": now.isoformat(),
            "status_global": "up",
            "uptime_seconds": 123456,
            "last_boot": "2026-06-01T10:00:00Z",
            "cpu_percent": 12.5,
            "ram_used_mb": 8000,
            "ram_total_mb": 24576,
            "disk_used_gb": 120.0,
            "disk_total_gb": 460.43,
            "mac_serial": "C02XYZ",
        },
    ))
    db_session.commit()
    _enroll_full(client, db_session)
    body = client.get(f"/api/fleet/{etab['id']}").json()
    m = body["machine"]
    assert m["last_seen_at"] is not None
    assert m["status_global"] == "up"
    assert m["cpu_percent"] == 12.5
    assert m["ram_used_mb"] == 8000
    assert m["disk_used_gb"] == 120.0
    assert m["mac_serial"] == "C02XYZ"
    # Fix fuseau : tous les datetimes de la reponse sortent avec Z.
    assert m["last_seen_at"].endswith("Z")
    assert m["last_boot"].endswith("Z")
    assert body["generated_at"].endswith("Z")
    assert body["created_at"].endswith("Z")


def test_detail_parses_dialeo_status(client, db_session, make_establishment):
    etab = make_establishment("École Dialeo")
    now = datetime.now(UTC)
    db_session.add(RawPush(
        etablissement_id=etab["id"],
        type="dialeo_status",
        timestamp_client=now, received_at=now,
        payload={
            "type": "dialeo_status",
            "timestamp": now.isoformat(),
            "version": "v0.10.1-test",
            "uvicorn_status": "up",
            "modes_active": ["aide_redaction", "exploration_libre"],
        },
    ))
    db_session.commit()
    _enroll_full(client, db_session)
    d = client.get(f"/api/fleet/{etab['id']}").json()["dialeo"]
    assert d["version"] == "v0.10.1-test"
    assert d["uvicorn_status"] == "up"
    assert "aide_redaction" in d["modes_active"]


def test_detail_lists_incidents_with_breakdown(client, db_session, make_establishment):
    etab = make_establishment("École Incidents")
    now = datetime.now(UTC)
    db_session.add(Incident(
        etablissement_id=etab["id"],
        timestamp_client=now - timedelta(days=1),
        received_at=now - timedelta(days=1),
        nb_refus_blacklist=3, nb_refus_llamaguard=1, nb_refus_systemprompt=0,
    ))
    db_session.add(Incident(
        etablissement_id=etab["id"],
        timestamp_client=now - timedelta(days=15),
        received_at=now - timedelta(days=15),
        nb_refus_blacklist=0, nb_refus_llamaguard=5, nb_refus_systemprompt=2,
    ))
    # Hors fenetre 30 j -> ne doit pas apparaitre
    db_session.add(Incident(
        etablissement_id=etab["id"],
        timestamp_client=now - timedelta(days=45),
        received_at=now - timedelta(days=45),
        nb_refus_blacklist=99, nb_refus_llamaguard=0, nb_refus_systemprompt=0,
    ))
    db_session.commit()
    _enroll_full(client, db_session)
    items = client.get(f"/api/fleet/{etab['id']}").json()["incidents_recent"]
    assert len(items) == 2  # le vieux 45j est exclu
    # Ordre desc par received_at -> plus recent en premier
    assert items[0]["nb_refus_blacklist"] == 3
    assert items[1]["nb_refus_llamaguard"] == 5
    # Fix fuseau : received_at de chaque incident sort avec Z.
    assert items[0]["received_at"].endswith("Z")
    assert items[1]["received_at"].endswith("Z")


def test_detail_health_uses_heartbeat_only_dette_consignee(
    client, db_session, make_establishment
):
    """Dette consignee : le health top-level depend du dernier heartbeat,
    PAS encore des signaux sante_systeme/dialeo/daemon en degraded.
    On verifie ici le comportement *actuel* (a faire evoluer plus tard)."""
    etab = make_establishment("École Pas Encore")
    now = datetime.now(UTC)
    db_session.add(Heartbeat(
        etablissement_id=etab["id"], timestamp=now, status="ok",
        payload={}, received_at=now,
    ))
    # Sante systeme degraded -> mais le health top-level reste online (dette).
    db_session.add(RawPush(
        etablissement_id=etab["id"], type="sante_systeme",
        timestamp_client=now, received_at=now,
        payload={"type": "sante_systeme", "timestamp": now.isoformat(),
                 "status_global": "degraded"},
    ))
    db_session.commit()
    _enroll_full(client, db_session)
    body = client.get(f"/api/fleet/{etab['id']}").json()
    assert body["health"] == "online"  # dette : ne reflete pas status_global
    # Mais l'UI peut le voir via machine.status_global
    assert body["machine"]["status_global"] == "degraded"
