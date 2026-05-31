"""Tests de POST /api/establishments — verrouillage admin (chantier 4 phase C)."""

import pyotp
import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.crypto import decrypt_at_rest
from app.scripts.create_admin import create_admin

_ADMIN_EMAIL = "admin@example.com"
_ADMIN_PWD = "passphrase-longue-ok"


@pytest.fixture(autouse=True)
def _secrets(monkeypatch):
    """Active JWT + Fernet pour ce module (sinon /api/auth/* -> 503)."""
    monkeypatch.setattr(settings, "jwt_secret", "test-jwt-" + "x" * 24)
    monkeypatch.setattr(settings, "totp_at_rest_key", Fernet.generate_key().decode("utf-8"))


def _enroll_full(client, db_session) -> None:
    """Cree un admin et l'amene jusqu'a une session complete (cookie session pose)."""
    create_admin(_ADMIN_EMAIL, _ADMIN_PWD, db_session)
    # Etape 1 : mdp -> pre_auth
    r = client.post("/api/auth/login", json={"email": _ADMIN_EMAIL, "password": _ADMIN_PWD})
    assert r.status_code == 200 and r.json()["status"] == "enrolement_requis"
    # Enroll TOTP
    enroll = client.post("/api/auth/totp/enroll")
    assert enroll.status_code == 200
    secret = enroll.json()["otpauth_uri"].split("secret=")[1].split("&")[0]
    # Confirm avec code courant -> session
    confirm = client.post("/api/auth/totp/confirm", json={"code": pyotp.TOTP(secret).now()})
    assert confirm.status_code == 200
    # Verif : /me 200
    assert client.get("/api/auth/me").status_code == 200


# --- Verrouillage ----------------------------------------------------------


def test_create_without_session_is_401(client):
    """Sans cookie -> 401 (la dette du commentaire phase 3.1 est levee)."""
    resp = client.post("/api/establishments", json={"name": "École Test"})
    assert resp.status_code == 401


def test_create_with_preauth_only_is_401(client, db_session):
    """Un cookie pre_auth (mdp seul, MFA non passe) ne suffit pas."""
    create_admin(_ADMIN_EMAIL, _ADMIN_PWD, db_session)
    # Login -> cookie pre_auth pose mais session pas etablie
    r = client.post("/api/auth/login", json={"email": _ADMIN_EMAIL, "password": _ADMIN_PWD})
    assert r.status_code == 200
    # Avec pre_auth seul -> 401 sur l'endpoint admin
    resp = client.post("/api/establishments", json={"name": "École Test"})
    assert resp.status_code == 401


def test_create_with_admin_session_is_201(client, db_session):
    """Session complete (mdp + TOTP) -> 201 et l'api_key est renvoyee."""
    _enroll_full(client, db_session)
    resp = client.post("/api/establishments", json={"name": "École Saint-Pierre"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "École Saint-Pierre"
    assert isinstance(body["api_key"], str) and len(body["api_key"]) >= 40


def test_create_duplicate_with_session_is_409(client, db_session):
    """La regle 409 d'unicite de nom reste active sous auth."""
    _enroll_full(client, db_session)
    assert client.post("/api/establishments", json={"name": "École Doublon"}).status_code == 201
    assert client.post("/api/establishments", json={"name": "École Doublon"}).status_code == 409


def test_decrypt_works_for_test_secret(db_session):
    """Sanity : la cle Fernet de test permet bien de chiffrer/dechiffrer (utilise par _enroll)."""
    from app.core.crypto import encrypt_at_rest

    blob = encrypt_at_rest("hello")
    assert decrypt_at_rest(blob) == "hello"
