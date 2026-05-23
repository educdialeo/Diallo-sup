"""Point d'entree des push des Mac mini clients (stub — non implemente)."""

from fastapi import APIRouter, status

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/ingest", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def ingest() -> dict[str, str]:
    """Future reception des donnees de supervision poussees par les Mac mini clients.

    Materialise le point d'entree REST ; l'implementation (auth par API key,
    validation, persistance SQLite) viendra avec le chantier N1.
    """
    return {"detail": "Not Implemented", "endpoint": "/api/ingest"}
