"""Tests de l'auth admin (login/logout/me) + attributs cookie + 503 sans JWT."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.scripts.create_admin import create_admin

_PWD = "passphrase-longue-ok"
_EMAIL = "admin@example.com"
_TEST_SECRET = "test-secret-" + "x" * 24


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    """Secret JWT par defaut pour tous les tests de ce module."""
    monkeypatch.setattr(settings, "jwt_secret", _TEST_SECRET)


@pytest.fixture()
def admin_user(db_session):
    return create_admin(_EMAIL, _PWD, db_session)


def _login(client, email=_EMAIL, password=_PWD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# --- login -----------------------------------------------------------------

def test_login_ok_sets_preauth_cookie_with_correct_attributes(client, admin_user):
    """Phase B : /login emet desormais un JWT pre_auth (TTL court), PAS une session."""
    resp = _login(client)
    assert resp.status_code == 200
    # Phase B : body porte le statut "totp_requis" | "enrolement_requis"
    assert resp.json()["status"] in ("totp_requis", "enrolement_requis")
    sc = resp.headers["set-cookie"]
    sc_lower = sc.lower()
    assert sc.startswith("diallosup_session=")
    assert "httponly" in sc_lower
    assert "samesite=strict" in sc_lower
    assert "path=/" in sc_lower
    # Max-Age = PREAUTH_TTL_MINUTES * 60 (defaut 5 min).
    assert f"max-age={settings.preauth_ttl_minutes * 60}" in sc_lower
    # Secure suit la conf (False par défaut en local).
    assert "secure" not in sc_lower


def test_login_bad_password_is_401_generic(client, admin_user):
    resp = _login(client, password="mauvais-mdp-12+")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides."


def test_login_unknown_email_returns_same_generic_message(client):
    """Anti-enumeration : meme message qu'un mauvais mot de passe."""
    resp = _login(client, email="ghost@nowhere.test", password="anything-12-chars")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides."


def test_login_inactive_user_is_401(client, admin_user, db_session):
    admin_user.is_active = False
    db_session.commit()
    assert _login(client).status_code == 401


def test_login_updates_last_login_at(client, admin_user, db_session):
    assert admin_user.last_login_at is None
    _login(client)
    db_session.refresh(admin_user)
    assert admin_user.last_login_at is not None


def test_secure_cookie_when_configured(client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "session_cookie_secure", True)
    resp = _login(client)
    assert "Secure" in resp.headers["set-cookie"]


# --- /me -------------------------------------------------------------------

def test_me_without_cookie_is_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_preauth_cookie_is_401(client, admin_user):
    """Phase B : /login pose un cookie pre_auth qui n'ouvre PAS /me. Il faut
    passer par /verify-totp (couvert dans tests/test_auth_mfa_flow.py)."""
    _login(client)
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_garbled_cookie_is_401(client, admin_user):
    client.cookies.set("diallosup_session", "not-a-jwt")
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_pre_auth_purpose(client, admin_user):
    """Futur-proof : un JWT 'pre_auth' (phase B) ne doit jamais ouvrir /me."""
    token = jwt.encode(
        {
            "sub": str(admin_user.id),
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            "purpose": "pre_auth",
        },
        _TEST_SECRET,
        algorithm="HS256",
    )
    client.cookies.set("diallosup_session", token)
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_expired_cookie(client, admin_user):
    token = jwt.encode(
        {
            "sub": str(admin_user.id),
            "exp": int((datetime.now(UTC) - timedelta(seconds=1)).timestamp()),
            "purpose": "session",
        },
        _TEST_SECRET,
        algorithm="HS256",
    )
    client.cookies.set("diallosup_session", token)
    assert client.get("/api/auth/me").status_code == 401


# --- logout ----------------------------------------------------------------

def test_logout_emits_cookie_clear_header(client, admin_user):
    """Logout efface le cookie via Set-Cookie Max-Age=0 (independant du purpose)."""
    _login(client)
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
    sc = resp.headers["set-cookie"]
    assert "diallosup_session=" in sc
    assert "Max-Age=0" in sc
    # /me reste 401 (l'etait deja avec un cookie pre_auth ; doublement vrai apres logout).
    assert client.get("/api/auth/me").status_code == 401


# --- JWT_SECRET manquant ---------------------------------------------------

def test_login_returns_503_when_jwt_secret_missing(client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", None)
    resp = _login(client)
    assert resp.status_code == 503
    assert "JWT_SECRET" in resp.json()["detail"]


def test_ingest_still_works_when_jwt_secret_missing(
    client, monkeypatch, make_establishment
):
    """L'auth admin ne doit pas casser l'ingestion : decouplage strict."""
    monkeypatch.setattr(settings, "jwt_secret", None)
    etab = make_establishment("École Ingest 4A")
    resp = client.post(
        "/api/ingest",
        headers={"Authorization": f"Bearer {etab['api_key']}"},
        json={"type": "heartbeat", "timestamp": "2026-05-31T10:00:00Z", "status": "ok"},
    )
    assert resp.status_code == 202
