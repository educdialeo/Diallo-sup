"""Tests du bootstrap admin (create_admin) + init_secrets."""

import pytest

from app.core.passwords import verify_password
from app.scripts.create_admin import create_admin
from app.scripts.init_secrets import ensure_jwt_secret

# --- create_admin ----------------------------------------------------------

def test_create_admin_creates_user(db_session):
    user = create_admin("admin@example.com", "passphrase-longue-ok", db_session)
    assert user.id is not None
    assert user.email == "admin@example.com"
    assert user.is_active is True
    assert user.totp_enrolled is False
    assert verify_password("passphrase-longue-ok", user.password_hash)


def test_create_admin_normalizes_email_lowercase(db_session):
    user = create_admin("MIXED@Case.COM", "passphrase-longue-ok", db_session)
    assert user.email == "mixed@case.com"


def test_create_admin_refuses_duplicate_email(db_session):
    create_admin("dup@example.com", "passphrase-longue-ok", db_session)
    with pytest.raises(ValueError, match="existe déjà"):
        create_admin("DUP@example.com", "autre-passphrase-ok", db_session)


def test_create_admin_refuses_short_password(db_session):
    with pytest.raises(ValueError, match="trop court"):
        create_admin("short@example.com", "shortpw", db_session)


def test_create_admin_refuses_empty_email(db_session):
    with pytest.raises(ValueError, match="vide"):
        create_admin("   ", "passphrase-longue-ok", db_session)


def test_create_admin_accepts_long_passphrase(db_session):
    """Passphrase tres longue : la troncature bcrypt est transparente (hash+verify OK)."""
    long_pp = "correct horse battery staple " * 5  # ~150 caracteres
    user = create_admin("longpp@example.com", long_pp, db_session)
    assert verify_password(long_pp, user.password_hash)


# --- init_secrets ----------------------------------------------------------

def test_init_secrets_generates_when_absent(tmp_path):
    env = tmp_path / ".env"
    assert ensure_jwt_secret(env) is True
    content = env.read_text()
    assert "JWT_SECRET=" in content
    assert len(content) > 20  # quelque chose de non trivial


def test_init_secrets_preserves_existing_value(tmp_path):
    env = tmp_path / ".env"
    env.write_text('JWT_SECRET="ma-valeur-existante"\nAUTRE="x"\n')
    assert ensure_jwt_secret(env) is False
    new_content = env.read_text()
    assert "ma-valeur-existante" in new_content
    assert "AUTRE" in new_content  # autres cles preservees aussi
