"""Modeles ORM de la console de supervision."""

from app.models.etablissement import Etablissement
from app.models.heartbeat import Heartbeat

__all__ = ["Etablissement", "Heartbeat"]
