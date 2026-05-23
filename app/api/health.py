"""Endpoint de sante de la console."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["monitoring"])


@router.get("/health")
def health() -> dict[str, str]:
    """Sonde de liveness : repond OK tant que le process FastAPI sert les requetes."""
    return {"status": "ok", "service": settings.app_name}
