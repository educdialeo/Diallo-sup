"""Point d'entree de l'application — Console de supervision Dialeo (Diallo-sup)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import health, ingest
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la base (creation des tables) au demarrage de l'application."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Fabrique l'application FastAPI et monte les routers."""
    app = FastAPI(
        title="Console de supervision Dialeo",
        version=__version__,
        summary="Backend de supervision multi-etablissements (repo technique : Diallo-sup).",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(ingest.router)
    return app


app = create_app()
