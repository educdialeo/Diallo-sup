"""Endpoint d'agrégation pour la page Inventaire / licences (chantier N1 étape 4)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth_admin import require_admin
from app.api.deps import DbSession
from app.models import User
from app.schemas.inventory import InventoryOverview
from app.services.inventory import build_inventory_overview

router = APIRouter(prefix="/api", tags=["inventory"])


@router.get("/inventory/overview", response_model=InventoryOverview)
def get_inventory_overview(
    db: DbSession,
    _admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """Renvoie l'inventaire courant de la flotte (1 ligne par établissement)."""
    return build_inventory_overview(db)
