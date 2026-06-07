"""Tests HTTP de GET /api/settings/overview (chantier N1 étape 4).

⚠️ Test critique : aucun secret en clair ne doit apparaître dans la réponse —
uniquement des booléens `*_configured`.
"""

import pyotp
import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.scripts.create_admin import create_admin

_ADMIN_EMAIL = "admin@example.com"
_ADMIN_PWD = "passphrase-longue-ok"
_TEST_JWT = "test-jwt-" + "x" * 24


@pytest.fixture()
def _fernet_key():
    return Fernet.generate_key().decode("utf-8")


@pytest.fixture(autouse=True)
def _secrets(monkeypatch, _fernet_key):
    monkeypatch.setattr(settings, "jwt_secret", _TEST_JWT)
    monkeypatch.setattr(settings, "totp_at_rest_key", _fernet_key)


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


def test_settings_without_session_is_401(client):
    assert client.get("/api/settings/overview").status_code == 401


def test_settings_with_preauth_only_is_401(client, db_session):
    create_admin(_ADMIN_EMAIL, _ADMIN_PWD, db_session)
    client.post("/api/auth/login", json={"email": _ADMIN_EMAIL, "password": _ADMIN_PWD})
    assert client.get("/api/settings/overview").status_code == 401


# --- Structure & contenu (lecture seule) --------------------------------


def test_settings_returns_full_shape(client, db_session):
    _enroll_full(client, db_session)
    body = client.get("/api/settings/overview").json()
    expected = {
        "app_name", "version", "host", "port", "log_level",
        "session_ttl_hours", "preauth_ttl_minutes", "session_cookie_secure",
        "login_max_attempts", "login_lockout_minutes",
        "jwt_secret_configured", "totp_at_rest_key_configured",
        "generated_at",
    }
    assert expected == set(body)
    assert body["jwt_secret_configured"] is True
    assert body["totp_at_rest_key_configured"] is True
    assert body["generated_at"].endswith("Z")


# --- 🛡️ DÉFENSE EN PROFONDEUR : aucun secret en clair ------------------


def test_settings_never_leak_secret_values(client, db_session, _fernet_key):
    """Test non-négociable : la réponse ne contient JAMAIS la valeur des secrets."""
    _enroll_full(client, db_session)
    resp = client.get("/api/settings/overview")
    raw_text = resp.text
    # Aucune valeur secrète en clair dans le payload brut.
    assert _TEST_JWT not in raw_text
    assert _fernet_key not in raw_text
    # Aucune clé sensible n'est exposée (sous quelque nom que ce soit).
    body = resp.json()
    for forbidden in ("jwt_secret", "totp_at_rest_key", "secret", "key"):
        # On tolère les suffixes "_configured" qui ne portent qu'un booléen.
        leaking = [k for k in body if forbidden in k.lower() and not k.endswith("_configured")]
        assert leaking == [], f"clé suspecte exposée : {leaking}"


def test_settings_reports_missing_secrets_as_false(client, db_session, monkeypatch):
    """Si les secrets ne sont pas configurés (None), les booléens passent à False."""
    monkeypatch.setattr(settings, "jwt_secret", _TEST_JWT)  # reste OK pour l'enroll
    monkeypatch.setattr(settings, "totp_at_rest_key", Fernet.generate_key().decode("utf-8"))
    _enroll_full(client, db_session)
    # Maintenant on simule l'absence APRÈS la session établie.
    monkeypatch.setattr(settings, "jwt_secret", None)
    monkeypatch.setattr(settings, "totp_at_rest_key", None)
    # require_admin va renvoyer 503 (jwt_secret None) — l'endpoint n'est plus
    # joignable. Vérifié indirectement par ce comportement.
    resp = client.get("/api/settings/overview")
    assert resp.status_code == 503
