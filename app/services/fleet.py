"""Service d'agregation pour la page Dashboard fleet view (etape N1).

`compute_health` est une fonction pure (isolee + testable). Les seuils sont des
hypotheses ajustables groupees en tete de module.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Etablissement, Heartbeat, Incident, RawPush, SessionRecord

# Seuils de sante live (hypotheses ajustables).
HEALTH_ONLINE_MAX_MIN = 5
HEALTH_SILENT_MIN_MIN = 15

# Fenetres d'agregation.
INCIDENTS_WINDOW_DAYS = 7
SESSIONS_RECENT_WINDOW_DAYS = 7
TREND_WINDOW_DAYS = 14

# Fenetre de la page detail (plus large que la tuile).
DETAIL_INCIDENTS_WINDOW_DAYS = 30
DETAIL_USAGE_WINDOW_DAYS = 30


HealthState = Literal["online", "degraded", "silent"]


def compute_health(
    now: datetime,
    last_hb_received_at: datetime | None,
    last_hb_status: str | None,
) -> HealthState:
    """Calcul pur de la sante live a partir du dernier heartbeat.

    Regles :
    - aucun heartbeat                                  -> silent
    - heartbeat plus vieux que HEALTH_SILENT_MIN_MIN   -> silent
    - heartbeat.status non "ok"                        -> degraded
    - heartbeat plus vieux que HEALTH_ONLINE_MAX_MIN   -> degraded
    - sinon                                            -> online
    """
    if last_hb_received_at is None:
        return "silent"
    # SQLite renvoie souvent un datetime naif : on suppose UTC pour comparer.
    received = (
        last_hb_received_at
        if last_hb_received_at.tzinfo is not None
        else last_hb_received_at.replace(tzinfo=UTC)
    )
    minutes_ago = (now - received).total_seconds() / 60
    if minutes_ago > HEALTH_SILENT_MIN_MIN:
        return "silent"
    if last_hb_status and last_hb_status.lower() != "ok":
        return "degraded"
    if minutes_ago > HEALTH_ONLINE_MAX_MIN:
        return "degraded"
    return "online"


# --- Helpers d'acces BDD ----------------------------------------------------


def _last_heartbeat(db: Session, etab_id: int) -> Heartbeat | None:
    return db.scalar(
        select(Heartbeat)
        .where(Heartbeat.etablissement_id == etab_id)
        .order_by(Heartbeat.received_at.desc(), Heartbeat.id.desc())
        .limit(1)
    )


def _last_live_session(db: Session, etab_id: int) -> SessionRecord | None:
    return db.scalar(
        select(SessionRecord)
        .where(
            SessionRecord.etablissement_id == etab_id,
            SessionRecord.kind == "live",
        )
        .order_by(SessionRecord.received_at.desc(), SessionRecord.id.desc())
        .limit(1)
    )


def _historique_rows(db: Session, etab_id: int) -> list[SessionRecord]:
    return list(
        db.scalars(
            select(SessionRecord).where(
                SessionRecord.etablissement_id == etab_id,
                SessionRecord.kind == "historique",
            )
        ).all()
    )


def _count_incidents_since(db: Session, etab_id: int, since: datetime) -> int:
    rows = db.scalars(
        select(Incident).where(
            Incident.etablissement_id == etab_id,
            Incident.received_at >= since,
        )
    ).all()
    return sum(
        (r.nb_refus_blacklist or 0)
        + (r.nb_refus_llamaguard or 0)
        + (r.nb_refus_systemprompt or 0)
        for r in rows
    )


def _parse_periode(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# --- Agregation usage -------------------------------------------------------


def _aggregate_usage(historique: list[SessionRecord], today: date) -> dict[str, Any]:
    """Renvoie sessions_total, sessions_7j, nb_eleves, duree_moyenne_min, trend_14d."""
    sessions_total = sum(r.nb_sessions or 0 for r in historique)
    nb_eleves_total = sum(r.nb_eleves or 0 for r in historique)

    weighted_num = sum((r.duree_moyenne_min or 0) * (r.nb_sessions or 0) for r in historique)
    weighted_den = sum(r.nb_sessions or 0 for r in historique)
    duree_moyenne_min = weighted_num / weighted_den if weighted_den > 0 else None

    since_7j = today - timedelta(days=SESSIONS_RECENT_WINDOW_DAYS - 1)
    sessions_7j = 0
    by_day: dict[date, int] = defaultdict(int)
    for r in historique:
        if r.granularite != "jour":
            continue
        d = _parse_periode(r.periode)
        if d is None:
            continue
        n = r.nb_sessions or 0
        by_day[d] += n
        if d >= since_7j:
            sessions_7j += n

    trend_14d = [
        by_day.get(today - timedelta(days=TREND_WINDOW_DAYS - 1 - i), 0)
        for i in range(TREND_WINDOW_DAYS)
    ]

    return {
        "sessions_total": sessions_total,
        "sessions_7j": sessions_7j,
        "nb_eleves": nb_eleves_total,
        "duree_moyenne_min": duree_moyenne_min,
        "trend_14d": trend_14d,
    }


# --- Build item / fleet -----------------------------------------------------


def build_fleet_item(db: Session, etab: Etablissement, now: datetime) -> dict[str, Any]:
    last_hb = _last_heartbeat(db, etab.id)
    last_hb_at = last_hb.received_at if last_hb is not None else None
    last_hb_status = last_hb.status if last_hb is not None else None
    health = compute_health(now, last_hb_at, last_hb_status)

    live = _last_live_session(db, etab.id)
    historique = _historique_rows(db, etab.id)
    usage = _aggregate_usage(historique, now.date())

    incidents_recent = _count_incidents_since(
        db, etab.id, now - timedelta(days=INCIDENTS_WINDOW_DAYS)
    )

    # Dormant : santé live OK mais ~0 session sur 14 j (strict pour la v1).
    is_dormant = health == "online" and sum(usage["trend_14d"]) == 0

    return {
        "id": etab.id,
        "name": etab.name,
        "status": etab.status,
        "health": health,
        "last_heartbeat_at": last_hb_at,
        "nb_eleves_connected": live.nb_eleves_connected if live else None,
        "nb_classes_active": live.nb_classes_active if live else None,
        **usage,
        "incidents_recent": incidents_recent,
        "is_dormant": is_dormant,
    }


def build_fleet(db: Session, now: datetime | None = None) -> dict[str, Any]:
    moment = now or datetime.now(UTC)
    etabs = list(db.scalars(select(Etablissement).order_by(Etablissement.id)).all())
    items = [build_fleet_item(db, e, moment) for e in etabs]
    return {"items": items, "generated_at": moment}


# ===========================================================================
# DETAIL — GET /api/fleet/{id}
# ===========================================================================


def _last_raw_push(
    db: Session, etab_id: int, type_: str
) -> tuple[dict, datetime] | None:
    """Renvoie (payload_dict, received_at) du dernier raw_push de ce type, ou None."""
    row = db.scalar(
        select(RawPush)
        .where(RawPush.etablissement_id == etab_id, RawPush.type == type_)
        .order_by(RawPush.received_at.desc(), RawPush.id.desc())
        .limit(1)
    )
    if row is None:
        return None
    payload = row.payload if isinstance(row.payload, dict) else {}
    return payload, row.received_at


def _machine_health(db: Session, etab_id: int) -> dict[str, Any]:
    res = _last_raw_push(db, etab_id, "sante_systeme")
    if res is None:
        return {"last_seen_at": None}
    p, last_seen_at = res
    return {
        "last_seen_at": last_seen_at,
        "status_global": p.get("status_global"),
        "uptime_seconds": p.get("uptime_seconds"),
        "last_boot": p.get("last_boot"),
        "cpu_percent": p.get("cpu_percent"),
        "ram_used_mb": p.get("ram_used_mb"),
        "ram_total_mb": p.get("ram_total_mb"),
        "disk_used_gb": p.get("disk_used_gb"),
        "disk_total_gb": p.get("disk_total_gb"),
        "temperature_celsius": p.get("temperature_celsius"),
        "mac_serial": p.get("mac_serial"),
    }


def _ollama_snapshot(db: Session, etab_id: int) -> dict[str, Any]:
    res = _last_raw_push(db, etab_id, "ollama_status")
    if res is None:
        return {"last_seen_at": None, "models_loaded": []}
    p, last_seen_at = res
    return {
        "last_seen_at": last_seen_at,
        "models_loaded": p.get("models_loaded") or [],
        "ping_latency_ms": p.get("ping_latency_ms"),
        "ram_used_mb": p.get("ram_used_mb"),
        "last_inference_at": p.get("last_inference_at"),
    }


def _dialeo_snapshot(db: Session, etab_id: int) -> dict[str, Any]:
    res = _last_raw_push(db, etab_id, "dialeo_status")
    if res is None:
        return {"last_seen_at": None, "modes_active": []}
    p, last_seen_at = res
    return {
        "last_seen_at": last_seen_at,
        "version": p.get("version"),
        "uvicorn_status": p.get("uvicorn_status"),
        "last_deploy_at": p.get("last_deploy_at"),
        "modes_active": p.get("modes_active") or [],
    }


def _daemon_snapshot(db: Session, etab_id: int) -> dict[str, Any]:
    res = _last_raw_push(db, etab_id, "daemon_uvicorn_health")
    if res is None:
        return {"last_seen_at": None}
    p, last_seen_at = res
    return {
        "last_seen_at": last_seen_at,
        "uvicorn_status": p.get("uvicorn_status"),
        "response_time_ms": p.get("response_time_ms"),
        "http_status": p.get("http_status"),
        "consecutive_failures": p.get("consecutive_failures"),
        "daemon_uptime_seconds": p.get("daemon_uptime_seconds"),
        "last_success_iso": p.get("last_success_iso"),
    }


def _incidents_list(db: Session, etab_id: int, since: datetime) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(Incident)
            .where(
                Incident.etablissement_id == etab_id,
                Incident.received_at >= since,
            )
            .order_by(Incident.received_at.desc(), Incident.id.desc())
        ).all()
    )
    return [
        {
            "received_at": r.received_at,
            "window_start": r.window_start,
            "window_end": r.window_end,
            "nb_refus_blacklist": r.nb_refus_blacklist,
            "nb_refus_llamaguard": r.nb_refus_llamaguard,
            "nb_refus_systemprompt": r.nb_refus_systemprompt,
        }
        for r in rows
    ]


def _usage_history(
    db: Session, etab_id: int, today: date, days: int = DETAIL_USAGE_WINDOW_DAYS
) -> list[dict[str, Any]]:
    """Renvoie `days` jours, du plus ancien au plus recent, avec zeros remplis.

    duree_moyenne_min ponderee par nb_sessions intra-jour (si plusieurs lignes).
    """
    historique = list(
        db.scalars(
            select(SessionRecord).where(
                SessionRecord.etablissement_id == etab_id,
                SessionRecord.kind == "historique",
            )
        ).all()
    )
    # Agrege par jour.
    sums: dict[date, dict[str, float]] = {}
    for r in historique:
        if r.granularite != "jour":
            continue
        d = _parse_periode(r.periode)
        if d is None:
            continue
        bucket = sums.setdefault(
            d, {"nb_sessions": 0, "nb_eleves": 0, "weighted_num": 0.0, "weighted_den": 0}
        )
        n = r.nb_sessions or 0
        bucket["nb_sessions"] += n
        bucket["nb_eleves"] += r.nb_eleves or 0
        bucket["weighted_num"] += (r.duree_moyenne_min or 0) * n
        bucket["weighted_den"] += n

    out: list[dict[str, Any]] = []
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        b = sums.get(d)
        if b is None:
            out.append({"date": d, "nb_sessions": 0, "nb_eleves": 0, "duree_moyenne_min": None})
        else:
            duree = b["weighted_num"] / b["weighted_den"] if b["weighted_den"] > 0 else None
            out.append(
                {
                    "date": d,
                    "nb_sessions": int(b["nb_sessions"]),
                    "nb_eleves": int(b["nb_eleves"]),
                    "duree_moyenne_min": duree,
                }
            )
    return out


def build_establishment_detail(
    db: Session, etab: Etablissement, now: datetime
) -> dict[str, Any]:
    last_hb = _last_heartbeat(db, etab.id)
    last_hb_at = last_hb.received_at if last_hb is not None else None
    last_hb_status = last_hb.status if last_hb is not None else None
    health = compute_health(now, last_hb_at, last_hb_status)

    live = _last_live_session(db, etab.id)

    return {
        "id": etab.id,
        "name": etab.name,
        "status": etab.status,
        "created_at": etab.created_at,
        "health": health,
        "last_heartbeat_at": last_hb_at,
        "nb_eleves_connected": live.nb_eleves_connected if live else None,
        "nb_classes_active": live.nb_classes_active if live else None,
        "machine": _machine_health(db, etab.id),
        "ollama": _ollama_snapshot(db, etab.id),
        "dialeo": _dialeo_snapshot(db, etab.id),
        "daemon": _daemon_snapshot(db, etab.id),
        "incidents_recent": _incidents_list(
            db, etab.id, now - timedelta(days=DETAIL_INCIDENTS_WINDOW_DAYS)
        ),
        "usage_history": _usage_history(db, etab.id, now.date()),
        "generated_at": now,
    }


def get_establishment_or_none(db: Session, etab_id: int) -> Etablissement | None:
    return db.get(Etablissement, etab_id)
