"""Service d'agregation pour la vue Modération (chantier N1 étape 3).

Lecture seule sur la table `incidents`. Aucune logique de seuil (la vue est
factuelle : compteurs bruts). Toutes les fenêtres temporelles sont calculees
relatives au `now` injecte (testable).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Etablissement, Incident

# Fenêtres et limites.
KPI_SHORT_WINDOW_DAYS = 7
KPI_LONG_WINDOW_DAYS = 30
TREND_WINDOW_DAYS = 30
TOP_LIMIT = 10
RECENT_LIMIT = 50


def _totals_since(db: Session, since: datetime) -> dict[str, int]:
    rows = db.scalars(
        select(Incident).where(Incident.received_at >= since)
    ).all()
    bl = sum(r.nb_refus_blacklist or 0 for r in rows)
    lg = sum(r.nb_refus_llamaguard or 0 for r in rows)
    sp = sum(r.nb_refus_systemprompt or 0 for r in rows)
    return {"blacklist": bl, "llamaguard": lg, "systemprompt": sp, "total": bl + lg + sp}


def _trend_by_category(
    db: Session, today: date, days: int = TREND_WINDOW_DAYS
) -> dict[str, list[int]]:
    """Renvoie 3 séries de `days` ints, du plus ancien au plus récent.

    Agrège par jour (date(received_at)). Zéros remplis pour les jours sans incident.
    """
    since_dt = datetime.combine(
        today - timedelta(days=days - 1), datetime.min.time(), tzinfo=UTC
    )
    rows = db.scalars(
        select(Incident).where(Incident.received_at >= since_dt)
    ).all()

    by_day_bl: dict[date, int] = defaultdict(int)
    by_day_lg: dict[date, int] = defaultdict(int)
    by_day_sp: dict[date, int] = defaultdict(int)
    for r in rows:
        # SQLite renvoie souvent un datetime naïf : on suppose UTC, on prend la date UTC.
        ts = r.received_at
        d = ts.date() if hasattr(ts, "date") else ts
        by_day_bl[d] += r.nb_refus_blacklist or 0
        by_day_lg[d] += r.nb_refus_llamaguard or 0
        by_day_sp[d] += r.nb_refus_systemprompt or 0

    def _series(buckets: dict[date, int]) -> list[int]:
        return [buckets.get(today - timedelta(days=days - 1 - i), 0) for i in range(days)]

    return {
        "blacklist": _series(by_day_bl),
        "llamaguard": _series(by_day_lg),
        "systemprompt": _series(by_day_sp),
    }


def _top_establishments(
    db: Session, since: datetime, limit: int = TOP_LIMIT
) -> list[dict[str, Any]]:
    """Top établissements par total d'incidents sur la fenêtre, desc."""
    # Récupère tous les incidents + leur étab, agrège en Python (volume bornable).
    rows = db.scalars(
        select(Incident).where(Incident.received_at >= since)
    ).all()
    by_etab: dict[int, dict[str, int]] = defaultdict(
        lambda: {"blacklist": 0, "llamaguard": 0, "systemprompt": 0}
    )
    for r in rows:
        b = by_etab[r.etablissement_id]
        b["blacklist"] += r.nb_refus_blacklist or 0
        b["llamaguard"] += r.nb_refus_llamaguard or 0
        b["systemprompt"] += r.nb_refus_systemprompt or 0

    if not by_etab:
        return []

    # Jointure noms en un seul select.
    etab_ids = list(by_etab.keys())
    etabs = {
        e.id: e.name
        for e in db.scalars(
            select(Etablissement).where(Etablissement.id.in_(etab_ids))
        ).all()
    }

    out: list[dict[str, Any]] = []
    for etab_id, counts in by_etab.items():
        total = counts["blacklist"] + counts["llamaguard"] + counts["systemprompt"]
        out.append(
            {
                "id": etab_id,
                "name": etabs.get(etab_id, f"#{etab_id}"),
                "nb_refus_blacklist": counts["blacklist"],
                "nb_refus_llamaguard": counts["llamaguard"],
                "nb_refus_systemprompt": counts["systemprompt"],
                "total": total,
            }
        )
    out.sort(key=lambda x: (-x["total"], x["name"]))
    return out[:limit]


def _recent_incidents(db: Session, limit: int = RECENT_LIMIT) -> list[dict[str, Any]]:
    """Liste des `limit` incidents les plus récents, tous établissements confondus."""
    rows = list(
        db.scalars(
            select(Incident)
            .order_by(Incident.received_at.desc(), Incident.id.desc())
            .limit(limit)
        ).all()
    )
    if not rows:
        return []
    etab_ids = list({r.etablissement_id for r in rows})
    etabs = {
        e.id: e.name
        for e in db.scalars(
            select(Etablissement).where(Etablissement.id.in_(etab_ids))
        ).all()
    }
    return [
        {
            "received_at": r.received_at,
            "window_start": r.window_start,
            "window_end": r.window_end,
            "etablissement_id": r.etablissement_id,
            "etablissement_name": etabs.get(r.etablissement_id, f"#{r.etablissement_id}"),
            "nb_refus_blacklist": r.nb_refus_blacklist,
            "nb_refus_llamaguard": r.nb_refus_llamaguard,
            "nb_refus_systemprompt": r.nb_refus_systemprompt,
        }
        for r in rows
    ]


def build_incidents_overview(
    db: Session, now: datetime | None = None
) -> dict[str, Any]:
    moment = now or datetime.now(UTC)
    since_7d = moment - timedelta(days=KPI_SHORT_WINDOW_DAYS)
    since_30d = moment - timedelta(days=KPI_LONG_WINDOW_DAYS)

    return {
        "totals_7d": _totals_since(db, since_7d),
        "totals_30d": _totals_since(db, since_30d),
        "trend_30d": _trend_by_category(db, moment.date()),
        "top_establishments": _top_establishments(db, since_30d),
        "recent_incidents": _recent_incidents(db),
        "generated_at": moment,
    }
