"""Initialisation SQLAlchemy : engine, session, base declarative.

La couche ORM pose la fondation d'un schema appele a grossir (sessions,
incidents, reports, logs, hardware, inventaire, audit A1-A5). Pour ce
chantier de fondation, les tables sont creees via `create_all` ; Alembic
prendra le relais quand le schema se stabilisera (cf docs/ARCHITECTURE.md).
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base declarative commune a tous les modeles ORM."""


def _ensure_sqlite_dir(database_url: str) -> None:
    """Cree le dossier parent du fichier SQLite si necessaire."""
    prefix = "sqlite:///"
    if database_url.startswith(prefix):
        db_path = Path(database_url[len(prefix) :])
        if db_path.parent and not db_path.parent.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

# check_same_thread=False : requis par SQLite sous le modele de threads de FastAPI.
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Cree les tables manquantes au demarrage de l'application."""
    # Import pour enregistrer les modeles sur Base.metadata avant create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependance FastAPI : fournit une session DB par requete."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
