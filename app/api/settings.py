"""Endpoint d'aperçu Réglages (lecture seule, chantier N1 étape 4)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth_admin import require_admin
from app.api.deps import DbSession  # noqa: F401  (cohérence d'ordre des dépendances)
from app.models import User
from app.schemas.settings import SettingsOverview
from app.services.settings import build_settings_overview

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings/overview", response_model=SettingsOverview)
def get_settings_overview(
    _admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """Renvoie la configuration runtime de la console (sans secrets)."""
    return build_settings_overview()
