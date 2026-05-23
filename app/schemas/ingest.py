"""Schemas d'entree de l'ingestion N1 — union discriminee sur le champ `type`.

Les 10 types du cadrage 23 mai (bloc 1.1). La validation est stricte
(`extra="forbid"` partout) : tout champ non declare est refuse. Pour les `reports`,
ce refus materialise l'anonymisation RGPD (cf app/api/errors.py -> HTTP 400).
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.heartbeat import HeartbeatIn


class NiveauScolaire(StrEnum):
    """Niveaux scolaires autorises (CP -> 3e)."""

    CP = "CP"
    CE1 = "CE1"
    CE2 = "CE2"
    CM1 = "CM1"
    CM2 = "CM2"
    SIXIEME = "6e"
    CINQUIEME = "5e"
    QUATRIEME = "4e"
    TROISIEME = "3e"


class _IngestBase(BaseModel):
    """Champs communs + validation stricte (refus des champs inconnus)."""

    model_config = ConfigDict(extra="forbid")
    timestamp: datetime


class SanteSystemeIn(_IngestBase):
    """Sante Mac mini + stats hardware (sections 1 & 2 fusionnees)."""

    type: Literal["sante_systeme"]
    status_global: Literal["up", "degraded", "down"]
    uptime_seconds: int | None = None
    last_boot: datetime | None = None
    mac_serial: str | None = None
    cpu_percent: float | None = None
    ram_used_mb: int | None = None
    ram_total_mb: int | None = None
    disk_used_gb: float | None = None
    disk_total_gb: float | None = None
    temperature_celsius: float | None = None


class OllamaStatusIn(_IngestBase):
    type: Literal["ollama_status"]
    models_loaded: list[str] = Field(default_factory=list)
    ping_latency_ms: float | None = None
    ram_used_mb: int | None = None
    last_inference_at: datetime | None = None


class DialeoStatusIn(_IngestBase):
    type: Literal["dialeo_status"]
    version: str
    uvicorn_status: Literal["up", "down"]
    last_deploy_at: datetime | None = None
    modes_active: list[str] = Field(default_factory=list)


class SessionsLiveIn(_IngestBase):
    type: Literal["sessions_live"]
    nb_classes_active: int
    nb_eleves_connected: int
    modes_in_use: list[str] = Field(default_factory=list)


class SessionsHistoriquesIn(_IngestBase):
    type: Literal["sessions_historiques"]
    granularite: Literal["jour", "semaine", "mois"]
    periode: str
    nb_sessions: int
    nb_eleves: int
    duree_moyenne_min: float
    modes_utilises: list[str] = Field(default_factory=list)


class IncidentsModerationIn(_IngestBase):
    type: Literal["incidents_moderation"]
    window_start: datetime | None = None
    window_end: datetime | None = None
    nb_refus_blacklist: int = 0
    nb_refus_llamaguard: int = 0
    nb_refus_systemprompt: int = 0


class ReportItem(BaseModel):
    """Un report anonymise. extra="forbid" => tout champ identifiant est refuse (400)."""

    model_config = ConfigDict(extra="forbid")

    date_jour: date  # jour pres, jamais l'heure
    question: str
    reponse: str
    mode_pedagogique: str
    niveau_scolaire: list[NiveauScolaire] = Field(min_length=1)
    note_enseignant: str | None = None


class ReportsIn(_IngestBase):
    type: Literal["reports"]
    reports: list[ReportItem] = Field(min_length=1)


class LogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    niveau: Literal["ERROR", "CRITICAL"]
    message: str
    timestamp: datetime
    contexte: dict | str | None = None


class LogsCritiquesIn(_IngestBase):
    type: Literal["logs_critiques"]
    logs: list[LogItem] = Field(min_length=1)


class InventaireIn(_IngestBase):
    type: Literal["inventaire"]
    mac_mini_model: str
    macos_version: str
    capacite_declaree_sieges: int
    formule_commerciale: str
    last_changed_at: datetime | None = None


# Union discriminee : FastAPI/Pydantic dispatchent sur la valeur de `type`.
IngestPayload = Annotated[
    (
        HeartbeatIn
        | SanteSystemeIn
        | OllamaStatusIn
        | DialeoStatusIn
        | SessionsLiveIn
        | SessionsHistoriquesIn
        | IncidentsModerationIn
        | ReportsIn
        | LogsCritiquesIn
        | InventaireIn
    ),
    Field(discriminator="type"),
]


class IngestAccepted(BaseModel):
    """Accuse de reception uniforme (202)."""

    type: str
    received_at: datetime
