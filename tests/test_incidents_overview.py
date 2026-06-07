"""Tests HTTP de GET /api/incidents/overview (chantier N1 étape 3)."""

from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.models import Incident
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


def _add_incident(
    db, etab_id: int, days_ago: int, *, bl: int = 0, lg: int = 0, sp: int = 0
) -> None:
    ts = datetime.now(UTC) - timedelta(days=days_ago)
    db.add(Incident(
        etablissement_id=etab_id,
        timestamp_client=ts, received_at=ts,
        nb_refus_blacklist=bl, nb_refus_llamaguard=lg, nb_refus_systemprompt=sp,
    ))


# --- Verrouillage --------------------------------------------------------


def test_overview_without_session_is_401(client):
    assert client.get("/api/incidents/overview").status_code == 401


def test_overview_with_preauth_only_is_401(client, db_session):
    create_admin(_ADMIN_EMAIL, _ADMIN_PWD, db_session)
    client.post("/api/auth/login", json={"email": _ADMIN_EMAIL, "password": _ADMIN_PWD})
    assert client.get("/api/incidents/overview").status_code == 401


# --- Structure & cas vide -----------------------------------------------


def test_overview_empty_returns_zeros_and_empty_lists(client, db_session):
    _enroll_full(client, db_session)
    body = client.get("/api/incidents/overview").json()
    # Structure complète
    expected_keys = {
        "totals_7d", "totals_30d", "trend_30d",
        "top_establishments", "recent_incidents", "generated_at",
    }
    assert expected_keys <= set(body)
    # Cas vide : totaux à zéro
    assert body["totals_7d"] == {"blacklist": 0, "llamaguard": 0, "systemprompt": 0, "total": 0}
    assert body["totals_30d"] == {"blacklist": 0, "llamaguard": 0, "systemprompt": 0, "total": 0}
    # Trend : 30 zéros par catégorie
    for cat in ("blacklist", "llamaguard", "systemprompt"):
        assert body["trend_30d"][cat] == [0] * 30
    assert body["top_establishments"] == []
    assert body["recent_incidents"] == []
    assert body["generated_at"].endswith("Z")  # cohérence Phase 1


# --- Totaux 7j vs 30j -----------------------------------------------------


def test_overview_totals_window_correctness(client, db_session, make_establishment):
    etab = make_establishment("École Test")
    # Récent (3j) : doit compter dans 7j ET 30j
    _add_incident(db_session, etab["id"], days_ago=3, bl=2, lg=1, sp=0)
    # Moyen (10j) : seulement dans 30j
    _add_incident(db_session, etab["id"], days_ago=10, bl=0, lg=0, sp=5)
    # Hors fenêtre 30j : ignoré
    _add_incident(db_session, etab["id"], days_ago=45, bl=99, lg=99, sp=99)
    db_session.commit()
    _enroll_full(client, db_session)
    body = client.get("/api/incidents/overview").json()
    assert body["totals_7d"] == {"blacklist": 2, "llamaguard": 1, "systemprompt": 0, "total": 3}
    assert body["totals_30d"] == {"blacklist": 2, "llamaguard": 1, "systemprompt": 5, "total": 8}


# --- Trend par catégorie -------------------------------------------------


def test_overview_trend_per_category(client, db_session, make_establishment):
    etab = make_establishment("École Trend")
    # Aujourd'hui : 3 refus blacklist
    _add_incident(db_session, etab["id"], days_ago=0, bl=3, lg=0, sp=0)
    # Il y a 5j : 2 llamaguard
    _add_incident(db_session, etab["id"], days_ago=5, bl=0, lg=2, sp=0)
    db_session.commit()
    _enroll_full(client, db_session)
    trend = client.get("/api/incidents/overview").json()["trend_30d"]
    assert len(trend["blacklist"]) == 30
    assert len(trend["llamaguard"]) == 30
    assert len(trend["systemprompt"]) == 30
    # Index 29 = aujourd'hui, index 24 = il y a 5j
    assert trend["blacklist"][29] == 3
    assert trend["llamaguard"][24] == 2
    assert sum(trend["systemprompt"]) == 0


# --- Top établissements --------------------------------------------------


def test_overview_top_establishments_sorted_desc(
    client, db_session, make_establishment
):
    a = make_establishment("École A")
    b = make_establishment("École B")
    c = make_establishment("École C")
    _add_incident(db_session, a["id"], days_ago=2, bl=1, lg=0, sp=0)   # total 1
    _add_incident(db_session, b["id"], days_ago=2, bl=5, lg=2, sp=3)   # total 10
    _add_incident(db_session, c["id"], days_ago=2, bl=0, lg=4, sp=0)   # total 4
    db_session.commit()
    _enroll_full(client, db_session)
    top = client.get("/api/incidents/overview").json()["top_establishments"]
    assert [t["name"] for t in top] == ["École B", "École C", "École A"]
    assert top[0]["total"] == 10


# --- Recent incidents ----------------------------------------------------


def test_overview_recent_incidents_desc_with_z_suffix(
    client, db_session, make_establishment
):
    a = make_establishment("École R")
    _add_incident(db_session, a["id"], days_ago=2, bl=1, lg=0, sp=0)  # plus vieux
    _add_incident(db_session, a["id"], days_ago=0, bl=0, lg=0, sp=2)  # plus récent
    db_session.commit()
    _enroll_full(client, db_session)
    recent = client.get("/api/incidents/overview").json()["recent_incidents"]
    assert len(recent) == 2
    # Desc par received_at
    assert recent[0]["nb_refus_systemprompt"] == 2
    assert recent[1]["nb_refus_blacklist"] == 1
    # Fix fuseau : received_at en UTC explicite
    assert recent[0]["received_at"].endswith("Z")
    # Lien établissement utilisable côté UI
    assert recent[0]["etablissement_id"] == a["id"]
    assert recent[0]["etablissement_name"] == "École R"
