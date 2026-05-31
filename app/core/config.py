"""Configuration applicative, chargee depuis l'environnement / le fichier .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reglages de la console, surchargeables par variables d'environnement."""

    app_name: str = "Diallo-sup console"
    database_url: str = "sqlite:///./data/diallo_sup.db"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"

    # === Auth admin (chantier 4 phase A) ===
    # Secret JWT optionnel : s'il manque, /api/auth/* renvoie 503 mais le reste
    # (ingestion, health) continue de tourner -> deploiement non-bloquant.
    # Genere via `python -m app.scripts.init_secrets`.
    jwt_secret: str | None = None
    # Duree de vie de la session (heures).
    session_ttl_hours: int = 12
    # Cookie Secure : False en local HTTP ; passer True quand HTTPS (Cloudflare).
    session_cookie_secure: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
