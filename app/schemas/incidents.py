"""Schemas de sortie pour la vue Modération (chantier N1 étape 3).

Vue d'agrégation flotte. Aucun contenu utilisateur : compteurs uniquement
(blacklist / llamaguard / systemprompt). Cf docs/ARCHITECTURE.md §8.
"""

from pydantic import BaseModel

from app.schemas._utc import UtcDatetime


class IncidentTotals(BaseModel):
    blacklist: int
    llamaguard: int
    systemprompt: int
    total: int


class TrendByCategory(BaseModel):
    """3 séries de N ints, du plus ancien au plus récent (1 par jour, zéros remplis)."""

    blacklist: list[int]
    llamaguard: list[int]
    systemprompt: list[int]


class EstablishmentIncidentsSummary(BaseModel):
    id: int
    name: str
    nb_refus_blacklist: int
    nb_refus_llamaguard: int
    nb_refus_systemprompt: int
    total: int


class RecentIncidentItem(BaseModel):
    received_at: UtcDatetime
    window_start: UtcDatetime | None = None
    window_end: UtcDatetime | None = None
    etablissement_id: int
    etablissement_name: str
    nb_refus_blacklist: int
    nb_refus_llamaguard: int
    nb_refus_systemprompt: int


class IncidentsOverview(BaseModel):
    totals_7d: IncidentTotals
    totals_30d: IncidentTotals
    trend_30d: TrendByCategory
    top_establishments: list[EstablishmentIncidentsSummary]  # max 10
    recent_incidents: list[RecentIncidentItem]  # max 50
    generated_at: UtcDatetime
