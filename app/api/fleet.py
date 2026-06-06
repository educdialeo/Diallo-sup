"""Endpoint d'agregation pour la page Dashboard fleet view (etape N1)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth_admin import require_admin
from app.api.deps import DbSession
from app.models import User
from app.schemas.fleet import FleetResponse
from app.services.fleet import build_fleet

router = APIRouter(prefix="/api", tags=["fleet"])


@router.get("/fleet", response_model=FleetResponse)
def get_fleet(
    db: DbSession,
    _admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """Renvoie l'etat agrege de la flotte (1 entree par etablissement)."""
    return build_fleet(db)
