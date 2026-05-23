"""Configuration applicative, chargee depuis l'environnement / le fichier .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reglages de la console, surchargeables par variables d'environnement."""

    app_name: str = "Diallo-sup console"
    database_url: str = "sqlite:///./data/diallo_sup.db"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
