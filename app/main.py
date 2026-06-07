"""Point d'entree de l'application — Console de supervision Dialeo (Diallo-sup)."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import auth_admin, establishments, fleet, health, incidents, ingest
from app.api.errors import register_exception_handlers
from app.core.config import settings
from app.core.db import init_db

# Build statique du SPA (genere par `npm run build` dans frontend/).
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la base (creation des tables) au demarrage de l'application."""
    init_db()
    yield


def _mount_spa(app: FastAPI) -> None:
    """Sert le build statique du SPA si present (prod).

    Inerte si le build n'existe pas (dev avec Vite, CI, tests) : dans ce cas
    seules les routes API/health sont exposees. Les routers etant montes avant,
    `/health` et `/api/*` gardent la priorite sur le fallback SPA.
    """
    if not FRONTEND_DIST.is_dir():
        return

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        # Sert le fichier demande s'il existe (favicon, etc.), sinon index.html
        # pour laisser le routeur cote client gerer les deep-links.
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


def create_app() -> FastAPI:
    """Fabrique l'application FastAPI et monte les routers."""
    app = FastAPI(
        title="Console de supervision Dialeo",
        version=__version__,
        summary="Backend de supervision multi-etablissements (repo technique : Diallo-sup).",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    if not settings.jwt_secret:
        sys.stderr.write(
            "[diallosup.auth] WARN: JWT_SECRET non configuré dans .env — "
            "/api/auth/* renverra 503 jusqu'à exécution de "
            "`python -m app.scripts.init_secrets` (ou create_admin).\n"
        )
    app.include_router(health.router)
    app.include_router(establishments.router)
    app.include_router(ingest.router)
    app.include_router(auth_admin.router)
    app.include_router(fleet.router)
    app.include_router(incidents.router)
    _mount_spa(app)
    return app


app = create_app()
