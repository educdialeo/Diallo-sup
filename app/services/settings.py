"""Service pour la page Reglages (chantier N1 etape 4).

Expose la configuration runtime en LECTURE SEULE. Les secrets ne sont jamais
sortis — seul un booleen "configured" est renvoye.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app import __version__
from app.core.config import settings


def build_settings_overview(now: datetime | None = None) -> dict[str, Any]:
    moment = now or datetime.now(UTC)
    return {
        # Service
        "app_name": settings.app_name,
        "version": __version__,
        "host": settings.host,
        "port": settings.port,
        "log_level": settings.log_level,
        # Auth / Session
        "session_ttl_hours": settings.session_ttl_hours,
        "preauth_ttl_minutes": settings.preauth_ttl_minutes,
        "session_cookie_secure": settings.session_cookie_secure,
        # Lockout
        "login_max_attempts": settings.login_max_attempts,
        "login_lockout_minutes": settings.login_lockout_minutes,
        # Secrets — booleens uniquement, JAMAIS les valeurs
        "jwt_secret_configured": bool(settings.jwt_secret),
        "totp_at_rest_key_configured": bool(settings.totp_at_rest_key),
        "generated_at": moment,
    }
