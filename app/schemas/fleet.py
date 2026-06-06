"""Schemas de sortie pour le Dashboard fleet view (etape N1)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FleetItem(BaseModel):
    """Une tuile etablissement de la grille."""

    # Identite
    id: int
    name: str
    status: str  # etablissements.status (cycle de vie ; PAS la sante live)

    # Sante live (calculee serveur)
    health: Literal["online", "degraded", "silent"]
    last_heartbeat_at: datetime | None

    # Sessions live (dernier snapshot kind='live')
    nb_eleves_connected: int | None
    nb_classes_active: int | None

    # Usage agrege (historique jour/semaine/mois)
    sessions_total: int
    sessions_7j: int
    nb_eleves: int
    duree_moyenne_min: float | None
    trend_14d: list[int]  # 14 valeurs, du plus ancien au plus recent

    # Alertes
    incidents_recent: int  # somme des 3 nb_refus_* sur 7 j
    is_dormant: bool  # online mais 0 session sur 14 j


class FleetResponse(BaseModel):
    items: list[FleetItem]
    generated_at: datetime
