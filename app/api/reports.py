"""Endpoint d'agrégation pour la page Rapports (chantier N1 étape 4).

⚠️ Aucun contenu utilisateur ne sort jamais de cet endpoint (cf service).
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth_admin import require_admin
from app.api.deps import DbSession
from app.models import User
from app.schemas.reports import ReportsOverview
from app.services.reports import build_reports_overview

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports/overview", response_model=ReportsOverview)
def get_reports_overview(
    db: DbSession,
    _admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """Aperçu anonymisé des reports : KPI 7j/30j, ventilation niveau/mode, top, récents."""
    return build_reports_overview(db)
