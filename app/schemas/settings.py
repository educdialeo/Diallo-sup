"""Schemas de sortie pour la page Reglages (chantier N1 etape 4).

Lecture seule v1. Aucune valeur secrete n'est exposee — pour `JWT_SECRET` et
`TOTP_AT_REST_KEY`, seul un booleen "configured: true/false" est renvoye.
Modification possible uniquement via `.env` + redemarrage launchd cote DialSup.
"""

from pydantic import BaseModel

from app.schemas._utc import UtcDatetime


class SettingsOverview(BaseModel):
    # Service
    app_name: str
    version: str
    host: str
    port: int
    log_level: str

    # Auth / Session
    session_ttl_hours: int
    preauth_ttl_minutes: int
    session_cookie_secure: bool

    # Lockout
    login_max_attempts: int
    login_lockout_minutes: int

    # Secrets — booleens uniquement, JAMAIS les valeurs
    jwt_secret_configured: bool
    totp_at_rest_key_configured: bool

    generated_at: UtcDatetime
