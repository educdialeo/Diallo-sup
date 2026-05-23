"""Fixtures partagees : client HTTP de test + base SQLite temporaire isolee."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.main import app
from app.models import Etablissement  # noqa: F401  (enregistre le modele sur Base.metadata)


@pytest.fixture()
def client() -> TestClient:
    """Client HTTP de test (lifespan non declenche : aucune base reelle touchee)."""
    return TestClient(app)


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    """Session liee a une base SQLite jetable, recreee pour chaque test."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
