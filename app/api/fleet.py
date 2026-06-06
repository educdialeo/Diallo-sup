"""Endpoint d'agregation pour la page Dashboard fleet view + detail (etape N1)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth_admin import require_admin
from app.api.deps import DbSession
from app.models import User
from app.schemas.fleet import EstablishmentDetail, FleetResponse
from app.services.fleet import (
    build_establishment_detail,
    build_fleet,
    get_establishment_or_none,
)

router = APIRouter(prefix="/api", tags=["fleet"])


@router.get("/fleet", response_model=FleetResponse)
def get_fleet(
    db: DbSession,
    _admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """Renvoie l'etat agrege de la flotte (1 entree par etablissement)."""
    return build_fleet(db)


@router.get("/fleet/{etablissement_id}", response_model=EstablishmentDetail)
def get_establishment_detail(
    etablissement_id: int,
    db: DbSession,
    _admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """Detail d'un etablissement pour la page drill-down (chantier N1 etape 2)."""
    etab = get_establishment_or_none(db, etablissement_id)
    if etab is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Établissement introuvable.",
        )
    return build_establishment_detail(db, etab, datetime.now(UTC))
