"""Endpoint d'agrégation pour la vue Modération (chantier N1 étape 3)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth_admin import require_admin
from app.api.deps import DbSession
from app.models import User
from app.schemas.incidents import IncidentsOverview
from app.services.incidents import build_incidents_overview

router = APIRouter(prefix="/api", tags=["incidents"])


@router.get("/incidents/overview", response_model=IncidentsOverview)
def get_incidents_overview(
    db: DbSession,
    _admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """Aperçu modération : KPI 7j/30j, tendance 30j par catégorie, top étabs, récents."""
    return build_incidents_overview(db)
