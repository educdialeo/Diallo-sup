"""Throttling / lockout par compte (persistant en BDD).

⚠️ Decision Phase B : le compteur n'est RESET que sur etablissement d'une
SESSION COMPLETE (verify-totp OK ou confirm OK), JAMAIS sur le succes du mot
de passe seul. Sans ca, un attaquant qui connait le mdp pourrait brute-forcer
TOTP a l'infini en re-faisant /login + /verify-totp en boucle. Cf test dedie.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User


def _normalize_utc(dt: datetime | None) -> datetime | None:
    """Garantit un datetime aware en UTC (SQLite renvoie souvent naive)."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def is_locked(user: User, now: datetime | None = None) -> bool:
    locked_until = _normalize_utc(user.locked_until)
    if locked_until is None:
        return False
    moment = now or datetime.now(UTC)
    return locked_until > moment


def register_failure(user: User, db: Session) -> None:
    """Incremente le compteur d'echec. Verrouille si seuil atteint.

    Si une fenetre de lock precedente est expiree, on repart de zero avant
    de compter (sinon on prolongerait indefiniment l'etat verrouille).
    """
    locked_until = _normalize_utc(user.locked_until)
    if locked_until is not None and not is_locked(user):
        user.failed_login_count = 0
        user.locked_until = None

    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= settings.login_max_attempts:
        user.locked_until = datetime.now(UTC) + timedelta(
            minutes=settings.login_lockout_minutes
        )
    db.commit()


def register_session_established(user: User, db: Session) -> None:
    """RESET du compteur — UNIQUEMENT sur verify-totp OK ou confirm OK.

    NE PAS appeler sur succes du mot de passe seul (cf docstring du module).
    """
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
