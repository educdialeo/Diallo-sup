"""Tests HTTP de GET /api/inventory/overview (chantier N1 étape 4)."""

from datetime import UTC, datetime

import pyotp
import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.models import RawPush
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


def _add_inventaire(
    db, etab_id: int, model: str, macos: str, sieges: int, formule: str
) -> None:
    now = datetime.now(UTC)
    db.add(RawPush(
        etablissement_id=etab_id,
        type="inventaire",
        timestamp_client=now, received_at=now,
        payload={
            "type": "inventaire",
            "timestamp": now.isoformat(),
            "mac_mini_model": model,
            "macos_version": macos,
            "capacite_declaree_sieges": sieges,
            "formule_commerciale": formule,
            "last_changed_at": now.isoformat(),
        },
    ))


# --- Verrouillage ---------------------------------------------------------


def test_inventory_without_session_is_401(client):
    assert client.get("/api/inventory/overview").status_code == 401


def test_inventory_with_preauth_only_is_401(client, db_session):
    create_admin(_ADMIN_EMAIL, _ADMIN_PWD, db_session)
    client.post("/api/auth/login", json={"email": _ADMIN_EMAIL, "password": _ADMIN_PWD})
    assert client.get("/api/inventory/overview").status_code == 401


# --- Structure & cas vide ------------------------------------------------


def test_inventory_empty_has_zero_totals_and_z_suffix(client, db_session):
    _enroll_full(client, db_session)
    body = client.get("/api/inventory/overview").json()
    assert set(body) >= {"items", "totals", "generated_at"}
    assert body["items"] == []
    assert body["totals"] == {
        "nb_etablissements": 0,
        "nb_etablissements_renseignes": 0,
        "total_sieges": 0,
        "par_formule": {},
    }
    assert body["generated_at"].endswith("Z")


# --- Agrégats et structure -----------------------------------------------


def test_inventory_aggregates_seats_and_per_formule(
    client, db_session, make_establishment
):
    a = make_establishment("École A")
    b = make_establishment("Collège B")
    c = make_establishment("Lycée C")
    make_establishment("École D sans inventaire")  # sans raw_push (juste créé)
    _add_inventaire(db_session, a["id"], "Mac mini M4", "15.5", 30, "Essentiel")
    _add_inventaire(db_session, b["id"], "Mac mini M4", "15.4", 50, "Confort")
    _add_inventaire(db_session, c["id"], "Mac mini M4", "15.5", 80, "Maîtrise")
    db_session.commit()
    _enroll_full(client, db_session)

    body = client.get("/api/inventory/overview").json()
    assert body["totals"]["nb_etablissements"] == 4
    assert body["totals"]["nb_etablissements_renseignes"] == 3
    assert body["totals"]["total_sieges"] == 160
    assert body["totals"]["par_formule"] == {"Essentiel": 1, "Confort": 1, "Maîtrise": 1}

    # 4 items dont 3 renseignés et 1 vide
    items = {it["name"]: it for it in body["items"]}
    assert items["École A"]["capacite_declaree_sieges"] == 30
    assert items["École A"]["formule_commerciale"] == "Essentiel"
    assert items["École A"]["last_seen_at"].endswith("Z")
    assert items["École D sans inventaire"]["last_seen_at"] is None
    assert items["École D sans inventaire"]["capacite_declaree_sieges"] is None
