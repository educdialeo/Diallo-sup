"""Schemas de sortie pour la page Inventaire / licences (chantier N1 etape 4)."""

from pydantic import BaseModel

from app.schemas._utc import UtcDatetime


class EstablishmentInventory(BaseModel):
    """Inventaire courant d'un etablissement, depuis le dernier raw_push 'inventaire'."""

    # Identite
    id: int
    name: str
    status: str

    # Snapshot du dernier inventaire reçu
    last_seen_at: UtcDatetime | None = None
    mac_mini_model: str | None = None
    macos_version: str | None = None
    capacite_declaree_sieges: int | None = None
    formule_commerciale: str | None = None
    last_changed_at: UtcDatetime | None = None  # declare cote M4


class InventoryTotals(BaseModel):
    nb_etablissements: int                       # total flotte
    nb_etablissements_renseignes: int            # ont reçu au moins 1 inventaire
    total_sieges: int                            # somme des capacites_declarees
    par_formule: dict[str, int]                  # {"Essentiel": 3, "Confort": 2, ...}


class InventoryOverview(BaseModel):
    items: list[EstablishmentInventory]
    totals: InventoryTotals
    generated_at: UtcDatetime
