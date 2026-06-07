"""Service d'agregation pour la page Rapports (chantier N1 etape 4).

⚠️ Defense en profondeur : `_recent_reports` selectionne EXPLICITEMENT les
colonnes sures de la table `reports`. Les colonnes contenu (`question`,
`reponse`, `note_enseignant`) ne sont JAMAIS chargees -> elles ne peuvent
pas leaker dans la reponse meme par accident.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Etablissement, Report

KPI_SHORT_WINDOW_DAYS = 7
KPI_LONG_WINDOW_DAYS = 30
TOP_LIMIT = 10
RECENT_LIMIT = 50


# --- Helpers --------------------------------------------------------------


def _totals_since(db: Session, since: datetime) -> dict[str, Any]:
    """Total + ventilation par niveau (multi-valeurs) + par mode."""
    # Charge UNIQUEMENT les colonnes necessaires aux agregats (pas le contenu).
    rows = db.execute(
        select(Report.niveau_scolaire, Report.mode_pedagogique).where(
            Report.received_at >= since
        )
    ).all()
    total = len(rows)
    by_niveau: dict[str, int] = defaultdict(int)
    by_mode: dict[str, int] = defaultdict(int)
    for niveau_list, mode in rows:
        # niveau_scolaire est une JSON list -> chaque niveau compte 1x.
        for n in niveau_list or []:
            by_niveau[str(n)] += 1
        if mode:
            by_mode[str(mode)] += 1
    return {
        "total": total,
        "by_niveau": dict(by_niveau),
        "by_mode": dict(by_mode),
    }


def _top_establishments(
    db: Session, since: datetime, limit: int = TOP_LIMIT
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Report.etablissement_id, func.count().label("nb"))
        .where(Report.received_at >= since)
        .group_by(Report.etablissement_id)
    ).all()
    if not rows:
        return []
    etab_ids = [r[0] for r in rows]
    etabs = {
        e.id: e.name
        for e in db.scalars(
            select(Etablissement).where(Etablissement.id.in_(etab_ids))
        ).all()
    }
    out = [
        {
            "id": etab_id,
            "name": etabs.get(etab_id, f"#{etab_id}"),
            "nb_reports": int(nb),
        }
        for etab_id, nb in rows
    ]
    out.sort(key=lambda x: (-x["nb_reports"], x["name"]))
    return out[:limit]


def _recent_reports(db: Session, limit: int = RECENT_LIMIT) -> list[dict[str, Any]]:
    """⚠️ SELECT EXPLICITE : colonnes contenu (question/reponse/note_enseignant)
    JAMAIS chargees. Defense en profondeur — meme un bug d'UI ne peut leaker."""
    rows = db.execute(
        select(
            Report.id,                  # pas exposé mais utile pour ORDER BY tiebreak
            Report.received_at,
            Report.date_jour,
            Report.etablissement_id,
            Report.niveau_scolaire,
            Report.mode_pedagogique,
            # NOTE : question, reponse, note_enseignant volontairement absents.
        )
        .order_by(Report.received_at.desc(), Report.id.desc())
        .limit(limit)
    ).all()
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
            "date_jour": r.date_jour,
            "etablissement_id": r.etablissement_id,
            "etablissement_name": etabs.get(r.etablissement_id, f"#{r.etablissement_id}"),
            "niveau_scolaire": [str(x) for x in (r.niveau_scolaire or [])],
            "mode_pedagogique": r.mode_pedagogique,
        }
        for r in rows
    ]


def build_reports_overview(
    db: Session, now: datetime | None = None
) -> dict[str, Any]:
    moment = now or datetime.now(UTC)
    since_7d = moment - timedelta(days=KPI_SHORT_WINDOW_DAYS)
    since_30d = moment - timedelta(days=KPI_LONG_WINDOW_DAYS)
    return {
        "totals_7d": _totals_since(db, since_7d),
        "totals_30d": _totals_since(db, since_30d),
        "top_establishments": _top_establishments(db, since_30d),
        "recent": _recent_reports(db),
        "generated_at": moment,
    }
