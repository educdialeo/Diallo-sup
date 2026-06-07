"""Schemas de sortie pour le Dashboard fleet view + page detail (chantier N1)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.schemas._utc import UtcDatetime

# ============================================================================
# Liste — GET /api/fleet
# ============================================================================


class FleetItem(BaseModel):
    """Une tuile etablissement de la grille."""

    # Identite
    id: int
    name: str
    status: str  # etablissements.status (cycle de vie ; PAS la sante live)

    # Sante live (calculee serveur)
    health: Literal["online", "degraded", "silent"]
    last_heartbeat_at: UtcDatetime | None

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
    generated_at: UtcDatetime


# ============================================================================
# Detail — GET /api/fleet/{id}
# ============================================================================
#
# Chaque snapshot expose last_seen_at -> le frontend marque "perime" si trop
# vieux (jugement de fraicheur cote UI, pas de seuil dur cote backend). Tous
# les champs metier sont optionnels : la prod peut ne jamais avoir recu certains
# types (ex. ollama_status, 0 ligne en prod observee 2026-06-06).


class MachineHealth(BaseModel):
    """Dernier `sante_systeme` re&ccedil;u (None si jamais re&ccedil;u)."""

    last_seen_at: UtcDatetime | None = None
    status_global: str | None = None
    uptime_seconds: int | None = None
    last_boot: UtcDatetime | None = None
    cpu_percent: float | None = None
    ram_used_mb: int | None = None
    ram_total_mb: int | None = None
    disk_used_gb: float | None = None
    disk_total_gb: float | None = None
    temperature_celsius: float | None = None
    mac_serial: str | None = None


class OllamaSnapshot(BaseModel):
    """Dernier `ollama_status` recu (0 ligne en prod au 2026-06-06)."""

    last_seen_at: UtcDatetime | None = None
    models_loaded: list[str] = []
    ping_latency_ms: float | None = None
    ram_used_mb: int | None = None
    last_inference_at: UtcDatetime | None = None


class DialeoSnapshot(BaseModel):
    """Dernier `dialeo_status` re&ccedil;u."""

    last_seen_at: UtcDatetime | None = None
    version: str | None = None
    uvicorn_status: str | None = None
    last_deploy_at: UtcDatetime | None = None
    modes_active: list[str] = []


class DaemonSnapshot(BaseModel):
    """Dernier `daemon_uvicorn_health` (signal du daemon de surveillance M4)."""

    last_seen_at: UtcDatetime | None = None
    uvicorn_status: str | None = None  # "ok" | "ko" | "unknown"
    response_time_ms: int | None = None
    http_status: int | None = None
    consecutive_failures: int | None = None
    daemon_uptime_seconds: int | None = None
    last_success_iso: str | None = None


class IncidentDetail(BaseModel):
    """Une ligne d'incident moderation (compteurs uniquement, JAMAIS de contenu)."""

    received_at: UtcDatetime
    window_start: UtcDatetime | None = None
    window_end: UtcDatetime | None = None
    nb_refus_blacklist: int
    nb_refus_llamaguard: int
    nb_refus_systemprompt: int


class UsageDay(BaseModel):
    """Agregat d'un jour d'usage (issu de `sessions kind='historique' granularite='jour'`)."""

    date: date
    nb_sessions: int
    nb_eleves: int
    duree_moyenne_min: float | None  # ponderee par nb_sessions intra-jour


class EstablishmentDetail(BaseModel):
    # Identite
    id: int
    name: str
    status: str
    created_at: UtcDatetime

    # Sante live (meme calcul que la tuile -- cf dette ROADMAP : ne reflete
    # PAS encore la degradation au niveau service).
    health: Literal["online", "degraded", "silent"]
    last_heartbeat_at: UtcDatetime | None

    # Live
    nb_eleves_connected: int | None
    nb_classes_active: int | None

    # Snapshots de telemetrie (chaque panneau juge sa propre fraicheur cote UI)
    machine: MachineHealth
    ollama: OllamaSnapshot
    dialeo: DialeoSnapshot
    daemon: DaemonSnapshot

    # Incidents detailles (30 j ; LISTE de compteurs)
    incidents_recent: list[IncidentDetail]

    # Historique d'usage (30 j, 1 entree/jour, zeros remplis)
    usage_history: list[UsageDay]

    # Meta
    generated_at: UtcDatetime
