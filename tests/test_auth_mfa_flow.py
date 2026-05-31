"""Tests d'integration du flux MFA TOTP (chantier 4 phase B).

Couvre : login 2 etapes (pre_auth -> verify-totp -> session), enrolement,
codes de recuperation usage unique, lockout sur /login ET /verify-totp,
et surtout : le compteur ne se reset PAS sur succes du mdp seul."""

import pyotp
import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.crypto import decrypt_at_rest
from app.scripts.create_admin import create_admin

EMAIL = "admin@example.com"
PWD = "passphrase-longue-ok"
_TEST_JWT_SECRET = "test-jwt-secret-" + "x" * 24


@pytest.fixture(autouse=True)
def _secrets(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", _TEST_JWT_SECRET)
    monkeypatch.setattr(settings, "totp_at_rest_key", Fernet.generate_key().decode("utf-8"))


@pytest.fixture()
def admin_user(db_session):
    return create_admin(EMAIL, PWD, db_session)


def _login(client, email=EMAIL, password=PWD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _current_totp(user, db_session) -> str:
    """Decrypt le secret TOTP du user depuis la BDD et renvoie le code courant."""
    db_session.refresh(user)
    secret = decrypt_at_rest(user.totp_secret)
    return pyotp.TOTP(secret).now()


def _enroll(client, db_session, user) -> tuple[str, list[str]]:
    """Enrole un user (1er login -> enroll -> confirm). Renvoie (secret_plain, recovery_codes)."""
    r = _login(client)
    assert r.status_code == 200 and r.json()["status"] == "enrolement_requis"
    r2 = client.post("/api/auth/totp/enroll")
    assert r2.status_code == 200
    uri = r2.json()["otpauth_uri"]
    secret_plain = uri.split("secret=")[1].split("&")[0]
    code = pyotp.TOTP(secret_plain).now()
    r3 = client.post("/api/auth/totp/confirm", json={"code": code})
    assert r3.status_code == 200
    codes = r3.json()["recovery_codes"]
    assert len(codes) == 10
    db_session.refresh(user)
    return secret_plain, codes


# --- Etape 1/2 : login pwd ---------------------------------------------------

def test_login_not_enrolled_returns_preauth_with_status(client, admin_user):
    r = _login(client)
    assert r.status_code == 200
    assert r.json() == {"status": "enrolement_requis"}
    sc = r.headers["set-cookie"].lower()
    assert "diallosup_session=" in sc
    assert "max-age=300" in sc  # 5 min = pre_auth
    assert "httponly" in sc and "samesite=strict" in sc


def test_me_with_preauth_cookie_is_401(client, admin_user):
    _login(client)
    assert client.get("/api/auth/me").status_code == 401


# --- Enrolement + confirmation ----------------------------------------------

def test_enroll_returns_otpauth_uri(client, admin_user):
    _login(client)
    r = client.post("/api/auth/totp/enroll")
    assert r.status_code == 200
    uri = r.json()["otpauth_uri"]
    assert uri.startswith("otpauth://totp/")
    assert "issuer=DialSup" in uri


def test_confirm_valid_code_enrolls_and_opens_session(client, db_session, admin_user):
    secret, codes = _enroll(client, db_session, admin_user)
    # Session etablie -> /me 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL
    # User flippe a enrolled, recovery_codes persistes (haches).
    assert admin_user.totp_enrolled is True
    assert admin_user.recovery_codes is not None


def test_confirm_invalid_code_is_401(client, admin_user):
    _login(client)
    client.post("/api/auth/totp/enroll")
    r = client.post("/api/auth/totp/confirm", json={"code": "000000"})
    assert r.status_code == 401


def test_already_enrolled_returns_409_on_enroll(client, db_session, admin_user):
    _enroll(client, db_session, admin_user)
    r = client.post("/api/auth/totp/enroll")
    assert r.status_code == 409


# --- Etape 2/2 : verify-totp -------------------------------------------------

def test_login_enrolled_returns_totp_requis(client, db_session, admin_user):
    _enroll(client, db_session, admin_user)
    client.cookies.clear()
    r = _login(client)
    assert r.status_code == 200 and r.json()["status"] == "totp_requis"


def test_verify_totp_valid_grants_session(client, db_session, admin_user):
    _enroll(client, db_session, admin_user)
    client.cookies.clear()
    _login(client)
    code = _current_totp(admin_user, db_session)
    r = client.post("/api/auth/verify-totp", json={"code": code})
    assert r.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_verify_totp_invalid_is_401(client, db_session, admin_user):
    _enroll(client, db_session, admin_user)
    client.cookies.clear()
    _login(client)
    r = client.post("/api/auth/verify-totp", json={"code": "000000"})
    assert r.status_code == 401


# --- Codes de recuperation ---------------------------------------------------

def test_recovery_code_grants_session_and_is_consumed(client, db_session, admin_user):
    _, codes = _enroll(client, db_session, admin_user)
    one = codes[0]
    client.cookies.clear()
    _login(client)
    r = client.post("/api/auth/verify-totp", json={"code": one})
    assert r.status_code == 200
    # Memoriser le code une 2e fois -> doit echouer
    client.cookies.clear()
    _login(client)
    r2 = client.post("/api/auth/verify-totp", json={"code": one})
    assert r2.status_code == 401


# --- Lockout -----------------------------------------------------------------

def test_lockout_after_n_password_failures(client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 3)
    for _ in range(3):
        r = _login(client, password="mauvais-mdp-12+")
        assert r.status_code == 401
    # Meme avec le bon mdp : 423
    r = _login(client)
    assert r.status_code == 423


def test_lockout_after_n_totp_failures(client, db_session, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 3)
    _enroll(client, db_session, admin_user)
    client.cookies.clear()
    _login(client)
    for _ in range(3):
        r = client.post("/api/auth/verify-totp", json={"code": "000000"})
        assert r.status_code == 401
    # Nouveau login -> 423 (le pwd serait OK mais le compte est lock)
    client.cookies.clear()
    r = _login(client)
    assert r.status_code == 423


def test_password_ok_does_not_reset_failure_counter(client, db_session, admin_user, monkeypatch):
    """⚠️ Test cle phase B : pwd OK repete + TOTP KO -> le compteur monte quand
    meme et finit par locker. Sinon le brute-force TOTP serait rouvert."""
    monkeypatch.setattr(settings, "login_max_attempts", 3)
    _enroll(client, db_session, admin_user)

    for _ in range(3):
        client.cookies.clear()
        r = _login(client)
        # pwd OK -> pre_auth (cookie pose, status totp_requis), MAIS le compteur ne reset PAS
        assert r.status_code == 200 and r.json()["status"] == "totp_requis"
        r2 = client.post("/api/auth/verify-totp", json={"code": "000000"})
        assert r2.status_code == 401  # compteur +1 a chaque fois

    # Apres 3 echecs TOTP : le compte est lock, meme un login pwd-correct -> 423
    client.cookies.clear()
    r3 = _login(client)
    assert r3.status_code == 423


def test_session_establishment_resets_counter(client, db_session, admin_user, monkeypatch):
    """Verify-totp OK reset bien le compteur (contrepartie du test precedent)."""
    monkeypatch.setattr(settings, "login_max_attempts", 5)
    _enroll(client, db_session, admin_user)
    # Quelques echecs TOTP (sans atteindre le seuil)
    client.cookies.clear()
    _login(client)
    for _ in range(3):
        client.post("/api/auth/verify-totp", json={"code": "000000"})
    db_session.refresh(admin_user)
    assert admin_user.failed_login_count == 3

    # Puis verify-totp avec un bon code -> compteur reset
    code = _current_totp(admin_user, db_session)
    r = client.post("/api/auth/verify-totp", json={"code": code})
    assert r.status_code == 200
    db_session.refresh(admin_user)
    assert admin_user.failed_login_count == 0
    assert admin_user.locked_until is None
