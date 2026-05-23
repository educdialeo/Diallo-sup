"""Schemas d'entree/sortie pour les heartbeats."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class HeartbeatIn(BaseModel):
    """Corps d'un push de heartbeat (type minimal, membre de l'union d'ingestion).

    Conserve depuis la phase 3.1 pour la compatibilite ascendante. Le payload N1
    exhaustif (10 types) vit dans `app/schemas/ingest.py`.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["heartbeat"] = "heartbeat"
    timestamp: datetime
    status: str


class HeartbeatOut(BaseModel):
    """Heartbeat tel que relu via l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    status: str
    received_at: datetime
