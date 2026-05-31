"""Fixtures partagees : client HTTP de test + base SQLite jetable isolee.

Le client surcharge la dependance `get_db` pour router toutes les requetes HTTP
vers la base jetable du test (et non la base reelle). Le `TestClient` est utilise
sans gestionnaire de contexte : le lifespan (init_db sur la base reelle) n'est pas
declenche.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base, get_db
from app.main import app
from app.models import Etablissement, Heartbeat  # noqa: F401  (enregistre les modeles)


@pytest.fixture()
def engine(tmp_path) -> Generator[Engine, None, None]:
    """Engine SQLite sur fichier jetable, schema cree, partage par le test."""
    eng = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=eng)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    """Session liee a la base jetable du test (acces direct a la BDD)."""
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine) -> Generator[TestClient, None, None]:
    """Client HTTP dont la dependance get_db pointe vers la base jetable."""
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def make_establishment(db_session):
    """Cree un etablissement directement en BDD et renvoie sa representation.

    Bypass HTTP volontairement (chantier 4 phase C) : POST /api/establishments
    est desormais protege par require_admin, et les tests d'ingest/heartbeats
    n'ont pas a configurer l'auth admin juste pour fabriquer un etablissement
    de fixture. Le verrouillage HTTP de l'endpoint est teste explicitement
    dans tests/test_establishments.py.
    """
    from app.core.security import generate_api_key, hash_api_key

    def _make(name: str) -> dict:
        api_key = generate_api_key()
        etab = Etablissement(
            name=name,
            api_key_hash=hash_api_key(api_key),
            status="active",
        )
        db_session.add(etab)
        db_session.commit()
        db_session.refresh(etab)
        return {
            "id": etab.id,
            "name": etab.name,
            "api_key": api_key,
            "created_at": etab.created_at.isoformat(),
        }

    return _make
