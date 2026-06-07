"""Schemas d'entree/sortie pour les etablissements."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._utc import UtcDatetime


class EstablishmentCreate(BaseModel):
    """Corps de creation d'un etablissement."""

    name: str = Field(min_length=1, max_length=200, examples=["École Saint-Pierre"])


class EstablishmentCreated(BaseModel):
    """Reponse de creation : contient l'API key en clair, renvoyee UNE SEULE FOIS."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    api_key: str
    created_at: UtcDatetime
