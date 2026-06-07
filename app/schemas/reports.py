"""Schemas de sortie pour la page Rapports (chantier N1 etape 4).

⚠️ Aucun champ ne porte de contenu utilisateur (`question`, `reponse`,
`note_enseignant`). Seuls des compteurs et metadonnees anonymisees sortent.
La defense en profondeur est faite au service (`_recent_reports` selectionne
explicitement les colonnes sures, jamais les colonnes contenu).
"""

from datetime import date

from pydantic import BaseModel

from app.schemas._utc import UtcDatetime


class ReportsTotals(BaseModel):
    total: int
    by_niveau: dict[str, int]       # {"CM1": 12, "6e": 7, ...}
    by_mode: dict[str, int]         # {"dialogue": 15, "quiz": 4, ...}


class TopReportingEstablishment(BaseModel):
    id: int
    name: str
    nb_reports: int


class RecentReportSummary(BaseModel):
    """Resume anonymise d'un report — JAMAIS de contenu utilisateur."""

    received_at: UtcDatetime
    date_jour: date
    etablissement_id: int
    etablissement_name: str
    niveau_scolaire: list[str]
    mode_pedagogique: str
    # PAS de question, PAS de reponse, PAS de note_enseignant (defense en profondeur).


class ReportsOverview(BaseModel):
    totals_7d: ReportsTotals
    totals_30d: ReportsTotals
    top_establishments: list[TopReportingEstablishment]   # max 10, fenetre 30j
    recent: list[RecentReportSummary]                     # max 50, sans contenu
    generated_at: UtcDatetime
