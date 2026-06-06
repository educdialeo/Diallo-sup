"""Seed dev-only — peuple une base SQLite jetable pour démontrer le Dashboard fleet view.

⚠️ REFUSE D'ÉCRIRE EN PROD. Avant de lancer, pointez DATABASE_URL vers un fichier
hors-prod, par exemple :

    DATABASE_URL="sqlite:////tmp/diallo_fleet_seed.db" \\
        .venv/bin/python -m app.scripts.seed_fleet

Couvre les états santé online / degraded / silent, le badge dormant, et un
incident récent — 5 établissements. Recette de démo complète (3 terminaux,
uvicorn de démo + Vite avec VITE_API_TARGET) : voir `docs/JOURNAL.md` entrée
fleet-dashboard.
"""

import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal, init_db
from app.core.security import generate_api_key, hash_api_key
from app.models import Etablissement, Heartbeat, Incident, SessionRecord

_PROD_DB_PATH = Path("/Users/serveur/Projects/Diallo-sup/data/diallo_sup.db")
_DEFAULT_URL = "sqlite:///./data/diallo_sup.db"


def _is_prod_db(database_url: str) -> bool:
    """Renvoie True si l'URL pointe vers la base prod (refus immediat)."""
    if database_url == _DEFAULT_URL:
        return True
    if not database_url.startswith("sqlite:///"):
        return False
    path_str = database_url[len("sqlite:///") :]
    try:
        resolved = Path(path_str).resolve()
    except (OSError, ValueError):
        return False
    return resolved == _PROD_DB_PATH.resolve()


def _now() -> datetime:
    return datetime.now(UTC)


def _add_heartbeats(db, etab_id: int, minutes_ago: int, status: str = "ok", count: int = 3) -> None:
    """Ajoute quelques heartbeats, le plus recent etant `minutes_ago` minutes en arriere."""
    now = _now()
    for i in range(count):
        ts = now - timedelta(minutes=minutes_ago + i * 5)
        db.add(Heartbeat(
            etablissement_id=etab_id,
            timestamp=ts, status=status, payload={}, received_at=ts,
        ))


def _add_live_session(db, etab_id: int, eleves: int, classes: int) -> None:
    now = _now()
    db.add(SessionRecord(
        etablissement_id=etab_id, kind="live",
        timestamp_client=now, received_at=now,
        nb_eleves_connected=eleves, nb_classes_active=classes,
    ))


def _add_historique(
    db, etab_id: int, days_back: int, nb_sessions: int, nb_eleves: int, duree: float
) -> None:
    d = date.today() - timedelta(days=days_back)
    ts = _now() - timedelta(days=days_back)
    db.add(SessionRecord(
        etablissement_id=etab_id, kind="historique",
        timestamp_client=ts, received_at=ts,
        granularite="jour", periode=d.isoformat(),
        nb_sessions=nb_sessions, nb_eleves=nb_eleves, duree_moyenne_min=duree,
    ))


def _add_incident(db, etab_id: int, refus_blacklist: int = 7) -> None:
    ts = _now() - timedelta(hours=20)
    db.add(Incident(
        etablissement_id=etab_id,
        timestamp_client=ts, received_at=ts,
        nb_refus_blacklist=refus_blacklist,
        nb_refus_llamaguard=0, nb_refus_systemprompt=0,
    ))


_FIXTURES = [
    # (nom, hb_min, hb_status, eleves_connectes, classes, historique_dense, incident)
    ("École Saint-Pierre",  1, "ok",   42, 3, True,  False),   # online
    ("Collège Voltaire",    8, "ok",   12, 1, True,  False),   # degraded (8 min)
    ("École Tilleuls",     30, "ok",   None, None, False, False),  # silent
    ("Lycée Démo",          1, "ok",   None, None, False, False),  # online + dormant
    ("Collège Renoir",      2, "ok",   25, 2, True,  True),    # online + incident
]


def seed(db) -> None:
    for name, hb_min, hb_status, eleves, classes, hist_dense, has_incident in _FIXTURES:
        if db.scalar(select(Etablissement).where(Etablissement.name == name)):
            print(f"  ↳ {name} déjà présent, skip")
            continue
        etab = Etablissement(
            name=name,
            api_key_hash=hash_api_key(generate_api_key()),
            status="active",
        )
        db.add(etab)
        db.flush()  # pour avoir etab.id

        _add_heartbeats(db, etab.id, hb_min, status=hb_status)
        if eleves is not None and classes is not None:
            _add_live_session(db, etab.id, eleves, classes)
        if hist_dense:
            for d_back in range(14):
                _add_historique(
                    db, etab.id,
                    days_back=d_back,
                    nb_sessions=10 + d_back % 5,
                    nb_eleves=80 + d_back * 3,
                    duree=28 + d_back % 4,
                )
        if has_incident:
            _add_incident(db, etab.id)
        print(f"  ✓ {name} créé")
    db.commit()


def main() -> int:
    if _is_prod_db(settings.database_url):
        print(
            "❌ DATABASE_URL pointe vers la base PROD. Refus catégorique.",
            file=sys.stderr,
        )
        print("   Définissez DATABASE_URL hors-prod avant de relancer, ex :", file=sys.stderr)
        print(
            '   DATABASE_URL="sqlite:////tmp/diallo_fleet_seed.db" '
            "python -m app.scripts.seed_fleet",
            file=sys.stderr,
        )
        return 2
    print(f"→ Cible : {settings.database_url}")
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    print("✅ Seed terminé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
