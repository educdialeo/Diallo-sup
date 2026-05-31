"""Tests du service lockout (compteur, verrouillage, reset)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import settings
from app.scripts.create_admin import create_admin
from app.services.auth_lockout import (
    is_locked,
    register_failure,
    register_session_established,
)


@pytest.fixture()
def user(db_session):
    return create_admin("lock@example.com", "passphrase-longue-ok", db_session)


def test_fresh_user_is_not_locked(user):
    assert is_locked(user) is False
    assert user.failed_login_count == 0
    assert user.locked_until is None


def test_register_failure_increments(user, db_session):
    register_failure(user, db_session)
    assert user.failed_login_count == 1
    assert is_locked(user) is False


def test_reaching_max_attempts_locks(user, db_session, monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 3)
    for _ in range(3):
        register_failure(user, db_session)
    assert user.failed_login_count == 3
    assert is_locked(user) is True
    # SQLite renvoie un datetime naive apres commit ; is_locked() normalise en UTC.
    assert user.locked_until is not None


def test_session_established_resets_counter(user, db_session, monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 3)
    for _ in range(3):
        register_failure(user, db_session)
    assert is_locked(user) is True
    register_session_established(user, db_session)
    assert user.failed_login_count == 0
    assert user.locked_until is None
    assert is_locked(user) is False


def test_register_failure_resets_when_lock_expired(user, db_session, monkeypatch):
    """Apres expiration du lock, le compteur repart de zero."""
    monkeypatch.setattr(settings, "login_max_attempts", 3)
    for _ in range(3):
        register_failure(user, db_session)
    # On force locked_until dans le passe (simule l'expiration de la fenetre).
    user.locked_until = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()
    assert is_locked(user) is False
    register_failure(user, db_session)
    assert user.failed_login_count == 1
    assert is_locked(user) is False
