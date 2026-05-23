"""Schemas d'entree/sortie pour les heartbeats."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class HeartbeatIn(BaseModel):
    """Corps d'un push de heartbeat (phase 3.1 : type minimal).

    Le payload N1 exhaustif (10 donnees) sera introduit en phase 3.2 ; la table
    `heartbeats` conserve deja le corps complet en JSON pour l'absorber.
    """

    type: Literal["heartbeat"] = "heartbeat"
    timestamp: datetime
    status: str


class HeartbeatAccepted(BaseModel):
    """Accuse de reception d'un heartbeat."""

    received_at: datetime


class HeartbeatOut(BaseModel):
    """Heartbeat tel que relu via l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    status: str
    received_at: datetime
