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
from app.models import Etablissement, Heartbeat, Incident, RawPush, SessionRecord

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


def _add_incident(
    db, etab_id: int,
    hours_ago: int = 20,
    blacklist: int = 7, llamaguard: int = 0, systemprompt: int = 0,
) -> None:
    ts = _now() - timedelta(hours=hours_ago)
    db.add(Incident(
        etablissement_id=etab_id,
        timestamp_client=ts, received_at=ts,
        nb_refus_blacklist=blacklist,
        nb_refus_llamaguard=llamaguard,
        nb_refus_systemprompt=systemprompt,
    ))


# --- Snapshots de telemetrie pour la page detail (chantier N1 etape 2) ----

def _add_sante_systeme(
    db, etab_id: int,
    minutes_ago: int = 1,
    status_global: str = "up",
    cpu_percent: float = 12.5,
    ram_used_mb: int = 8000,
    ram_total_mb: int = 24576,
    disk_used_gb: float = 120.0,
    disk_total_gb: float = 460.0,
) -> None:
    ts = _now() - timedelta(minutes=minutes_ago)
    db.add(RawPush(
        etablissement_id=etab_id,
        type="sante_systeme",
        timestamp_client=ts, received_at=ts,
        payload={
            "type": "sante_systeme",
            "timestamp": ts.isoformat(),
            "status_global": status_global,
            "uptime_seconds": 952247,
            "last_boot": (ts - timedelta(seconds=952247)).isoformat(),
            "mac_serial": "C02XYZSEED",
            "cpu_percent": cpu_percent,
            "ram_used_mb": ram_used_mb,
            "ram_total_mb": ram_total_mb,
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "temperature_celsius": None,
        },
    ))


def _add_dialeo_status(
    db, etab_id: int,
    minutes_ago: int = 1,
    uvicorn_status: str = "up",
    version: str = "v0.10.1-supervision-logging-fix",
) -> None:
    ts = _now() - timedelta(minutes=minutes_ago)
    db.add(RawPush(
        etablissement_id=etab_id,
        type="dialeo_status",
        timestamp_client=ts, received_at=ts,
        payload={
            "type": "dialeo_status",
            "timestamp": ts.isoformat(),
            "version": version,
            "uvicorn_status": uvicorn_status,
            "last_deploy_at": None,
            "modes_active": [
                "aide_redaction", "exploration_libre",
                "recherche_encadree", "tuteur_socratique",
            ],
        },
    ))


def _add_daemon_uvicorn_health(
    db, etab_id: int,
    minutes_ago: int = 1,
    uvicorn_status: str = "ok",
    consecutive_failures: int = 0,
    response_time_ms: int = 6,
) -> None:
    ts = _now() - timedelta(minutes=minutes_ago)
    db.add(RawPush(
        etablissement_id=etab_id,
        type="daemon_uvicorn_health",
        timestamp_client=ts, received_at=ts,
        payload={
            "type": "daemon_uvicorn_health",
            "timestamp": ts.isoformat(),
            "uvicorn_status": uvicorn_status,
            "response_time_ms": response_time_ms if uvicorn_status == "ok" else None,
            "http_status": 200 if uvicorn_status == "ok" else None,
            "consecutive_failures": consecutive_failures,
            "daemon_uptime_seconds": 695690,
            "last_success_iso": ts.isoformat() if uvicorn_status == "ok" else None,
        },
    ))


_FIXTURES = [
    # (nom, hb_min, hb_status, eleves, classes, historique_dense, incidents,
    #  machine_min_ago | None, dialeo_uvicorn_status | None, daemon_status | None,
    #  daemon_consecutive_failures)
    # online — snapshots frais, zéro incident (cas "tout propre")
    ("École Saint-Pierre",  1, "ok",   42, 3, True,  0,   1, "up",  "ok",     0),
    # degraded (8 min HB) + 2 incidents pour étoffer la vue Modération (étape 3)
    ("Collège Voltaire",    8, "ok",   12, 1, True,  2,   1, "up",  "ok",     0),
    # silent (30 min HB) + 1 incident ancien (~25 j) — silent peut avoir un historique
    ("École Tilleuls",     30, "ok",   None, None, False, 1,  None, None, None,   0),
    # online + dormant + 1 incident isolé (llamaguard uniquement)
    ("Lycée Démo",          1, "ok",   None, None, False, 1,  2,   "up",  "ok",   0),
    # online + 3 INCIDENTS ventilés + daemon en alerte (cas "top du classement")
    ("Collège Renoir",      2, "ok",   25, 2, True,  3,   1, "up",  "ko",     3),
]


def seed(db) -> None:
    for (
        name, hb_min, hb_status, eleves, classes, hist_dense, incidents_count,
        machine_min, dialeo_status, daemon_status, daemon_failures,
    ) in _FIXTURES:
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

        # Snapshots de telemetrie pour la page detail.
        if machine_min is not None:
            _add_sante_systeme(db, etab.id, minutes_ago=machine_min)
        if dialeo_status is not None:
            _add_dialeo_status(db, etab.id, uvicorn_status=dialeo_status)
        if daemon_status is not None:
            _add_daemon_uvicorn_health(
                db, etab.id,
                uvicorn_status=daemon_status,
                consecutive_failures=daemon_failures,
            )

        # Incidents — réparti par nb_incidents souhaité. Ventilations
        # différenciées pour démontrer la vue Modération (chantier N1 étape 3) :
        # KPI par catégorie + tendance + top établissements.
        if incidents_count == 1:
            # Cas isolé : 1 refus llamaguard récent OU 1 refus ancien blacklist
            # selon l'étab (silent vs dormant) -> on prend le nom comme heuristique.
            if name.startswith("École Tilleuls"):
                _add_incident(db, etab.id, hours_ago=25 * 24, blacklist=2)  # ~25 j
            else:
                _add_incident(db, etab.id, hours_ago=12, llamaguard=4)
        elif incidents_count == 2:
            _add_incident(db, etab.id, hours_ago=6,  blacklist=1, systemprompt=2)
            _add_incident(db, etab.id, hours_ago=48, llamaguard=3)
        elif incidents_count >= 3:
            _add_incident(db, etab.id, hours_ago=4,  blacklist=3, llamaguard=1)
            _add_incident(db, etab.id, hours_ago=28, blacklist=0, llamaguard=2, systemprompt=1)
            _add_incident(db, etab.id, hours_ago=72, blacklist=5)

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
