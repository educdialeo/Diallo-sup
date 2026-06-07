"""Tests HTTP de GET /api/fleet (chantier N1, fleet view)."""

from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.models import Heartbeat, Incident, SessionRecord
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


# --- Verrouillage --------------------------------------------------------


def test_fleet_without_session_is_401(client):
    assert client.get("/api/fleet").status_code == 401


# --- Structure de reponse -----------------------------------------------


def test_fleet_returns_one_item_per_establishment_with_full_shape(
    client, db_session, make_establishment
):
    make_establishment("École Test 1")
    make_establishment("École Test 2")
    _enroll_full(client, db_session)

    resp = client.get("/api/fleet")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body and "generated_at" in body
    items = body["items"]
    assert len(items) == 2
    expected_keys = {
        "id", "name", "status", "health", "last_heartbeat_at",
        "nb_eleves_connected", "nb_classes_active",
        "sessions_total", "sessions_7j", "nb_eleves", "duree_moyenne_min",
        "trend_14d", "incidents_recent", "is_dormant",
    }
    for item in items:
        assert expected_keys <= set(item)
        assert len(item["trend_14d"]) == 14


# --- Sante calculee -----------------------------------------------------


def test_fleet_without_heartbeat_is_silent(client, db_session, make_establishment):
    make_establishment("École Sans Signal")
    _enroll_full(client, db_session)
    item = client.get("/api/fleet").json()["items"][0]
    assert item["health"] == "silent"
    assert item["last_heartbeat_at"] is None
    assert item["is_dormant"] is False  # silent != online


def test_fleet_dormant_detection(client, db_session, make_establishment):
    """Heartbeat recent ok + zero session sur 14 j -> online + dormant.

    Verifie aussi (fix fuseau, 2026-06-07) que les datetimes de reponse sortent
    en UTC explicite (suffixe Z) : `last_heartbeat_at` lu de DB (donc naïf)
    et `generated_at` aware doivent etre coherents.
    """
    etab = make_establishment("École Dormante")
    now = datetime.now(UTC)
    db_session.add(Heartbeat(
        etablissement_id=etab["id"], timestamp=now, status="ok",
        payload={}, received_at=now,
    ))
    db_session.commit()
    _enroll_full(client, db_session)
    body = client.get("/api/fleet").json()
    item = body["items"][0]
    assert item["health"] == "online"
    assert item["is_dormant"] is True
    assert item["last_heartbeat_at"].endswith("Z")
    assert body["generated_at"].endswith("Z")


def test_fleet_aggregates_usage_and_trend(client, db_session, make_establishment):
    """Lignes historiques jour -> sessions_total/7j/trend_14d coherents."""
    etab = make_establishment("École Active")
    now = datetime.now(UTC)
    today = now.date()
    # 3 jours d'historique : J-1 (5 sessions), J-3 (3 sessions), J-10 (2 sessions).
    fixtures = [(1, 5, 60, 30.0), (3, 3, 40, 25.0), (10, 2, 20, 20.0)]
    for days_back, n_sess, n_el, dur in fixtures:
        d = today - timedelta(days=days_back)
        db_session.add(SessionRecord(
            etablissement_id=etab["id"], kind="historique",
            timestamp_client=now - timedelta(days=days_back),
            received_at=now - timedelta(days=days_back),
            granularite="jour", periode=d.isoformat(),
            nb_sessions=n_sess, nb_eleves=n_el, duree_moyenne_min=dur,
        ))
    # + 1 live session
    db_session.add(SessionRecord(
        etablissement_id=etab["id"], kind="live",
        timestamp_client=now, received_at=now,
        nb_eleves_connected=42, nb_classes_active=3,
    ))
    db_session.commit()
    _enroll_full(client, db_session)

    item = client.get("/api/fleet").json()["items"][0]
    assert item["sessions_total"] == 10        # 5+3+2
    assert item["sessions_7j"] == 8            # J-1 + J-3 (J-10 hors fenetre)
    assert item["nb_eleves"] == 120            # 60+40+20
    assert item["nb_eleves_connected"] == 42
    assert item["nb_classes_active"] == 3
    # trend_14d : index 13 = aujourd'hui, 12 = J-1, ..., 3 = J-10
    assert item["trend_14d"][12] == 5
    assert item["trend_14d"][10] == 3
    assert item["trend_14d"][3] == 2
    assert sum(item["trend_14d"]) == 10
    # Pas dormant (sessions > 0). Mais silent car pas de heartbeat.
    assert item["is_dormant"] is False


def test_fleet_counts_recent_incidents(client, db_session, make_establishment):
    etab = make_establishment("École avec incident")
    now = datetime.now(UTC)
    # Un incident recent (1 j) avec 3+1+2 = 6 refus.
    db_session.add(Incident(
        etablissement_id=etab["id"],
        timestamp_client=now - timedelta(days=1),
        received_at=now - timedelta(days=1),
        nb_refus_blacklist=3, nb_refus_llamaguard=1, nb_refus_systemprompt=2,
    ))
    # Un incident vieux (10 j) -> hors fenetre 7j.
    db_session.add(Incident(
        etablissement_id=etab["id"],
        timestamp_client=now - timedelta(days=10),
        received_at=now - timedelta(days=10),
        nb_refus_blacklist=99, nb_refus_llamaguard=0, nb_refus_systemprompt=0,
    ))
    db_session.commit()
    _enroll_full(client, db_session)
    item = client.get("/api/fleet").json()["items"][0]
    assert item["incidents_recent"] == 6
