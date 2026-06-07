"""Service d'agregation pour la page Inventaire / licences (chantier N1 etape 4)."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Etablissement
from app.services.fleet import _last_raw_push  # reutilise le helper generique


def _establishment_inventory(db: Session, etab: Etablissement) -> dict[str, Any]:
    """Construit la ligne d'inventaire d'un etablissement (None partout si jamais reçu)."""
    base = {
        "id": etab.id,
        "name": etab.name,
        "status": etab.status,
        "last_seen_at": None,
        "mac_mini_model": None,
        "macos_version": None,
        "capacite_declaree_sieges": None,
        "formule_commerciale": None,
        "last_changed_at": None,
    }
    res = _last_raw_push(db, etab.id, "inventaire")
    if res is None:
        return base
    payload, last_seen_at = res
    base.update(
        {
            "last_seen_at": last_seen_at,
            "mac_mini_model": payload.get("mac_mini_model"),
            "macos_version": payload.get("macos_version"),
            "capacite_declaree_sieges": payload.get("capacite_declaree_sieges"),
            "formule_commerciale": payload.get("formule_commerciale"),
            "last_changed_at": payload.get("last_changed_at"),
        }
    )
    return base


def _compute_totals(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregats : nb etabs / nb renseignes / total sieges / repartition par formule."""
    nb_etabs = len(items)
    nb_renseignes = sum(1 for it in items if it["last_seen_at"] is not None)
    total_sieges = sum(it["capacite_declaree_sieges"] or 0 for it in items)

    par_formule: dict[str, int] = defaultdict(int)
    for it in items:
        if it["formule_commerciale"]:
            par_formule[it["formule_commerciale"]] += 1

    return {
        "nb_etablissements": nb_etabs,
        "nb_etablissements_renseignes": nb_renseignes,
        "total_sieges": total_sieges,
        "par_formule": dict(par_formule),
    }


def build_inventory_overview(
    db: Session, now: datetime | None = None
) -> dict[str, Any]:
    moment = now or datetime.now(UTC)
    etabs = list(db.scalars(select(Etablissement).order_by(Etablissement.id)).all())
    items = [_establishment_inventory(db, e) for e in etabs]
    return {
        "items": items,
        "totals": _compute_totals(items),
        "generated_at": moment,
    }
