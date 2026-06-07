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
from app.models import Etablissement, Heartbeat, Incident, RawPush, Report, SessionRecord

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


def _add_inventaire(
    db, etab_id: int,
    *, mac_model: str, macos: str, sieges: int, formule: str,
    days_since_changed: int = 30,
) -> None:
    """Ajoute un raw_push 'inventaire' realiste pour demontrer la page Inventaire."""
    now = _now()
    db.add(RawPush(
        etablissement_id=etab_id,
        type="inventaire",
        timestamp_client=now, received_at=now,
        payload={
            "type": "inventaire",
            "timestamp": now.isoformat(),
            "mac_mini_model": mac_model,
            "macos_version": macos,
            "capacite_declaree_sieges": sieges,
            "formule_commerciale": formule,
            "last_changed_at": (now - timedelta(days=days_since_changed)).isoformat(),
        },
    ))


def _add_report(
    db, etab_id: int,
    *, days_ago: int, niveaux: list[str], mode: str,
    question: str = "Q exemple seed (non affichee)",
    reponse: str = "R exemple seed (non affichee)",
    note: str | None = None,
) -> None:
    """Ajoute un report (table dediee). Le contenu n'est jamais affiche dans l'UI
    (defense en profondeur cote service reports), mais doit etre present en BDD."""
    received = _now() - timedelta(days=days_ago)
    db.add(Report(
        etablissement_id=etab_id,
        received_at=received,
        date_jour=received.date(),
        question=question, reponse=reponse,
        mode_pedagogique=mode,
        niveau_scolaire=niveaux,
        note_enseignant=note,
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


# --- Inventaire (chantier N1 etape 4) ---------------------------------------
#
# OPTION A (defaut) — `formule_commerciale` = vraies formules commerciales
# Dialeo (Essentiel / Confort / Maitrise). L'agregat UI s'appelle alors
# naturellement « par formule commerciale ».
#
# OPTION B — `formule_commerciale` = type d'etablissement (école / collège /
# lycée). Dans ce cas, l'agregat UI doit etre relabel « par type
# d'etablissement » (le NOM du champ Pydantic ne bouge pas, seul son CONTENU
# change). C'est l'option presentee a l'arbitrage au Point 2.
#
# Pour basculer en Option B : remplacer les valeurs ci-dessous par
#   "école primaire" / "collège" / "lycée" et adapter le label UI.
_INVENTAIRES = {
    "École Saint-Pierre": ("Mac mini M4", "15.5", 30, "Essentiel"),
    "Collège Voltaire":   ("Mac mini M4", "15.4", 50, "Confort"),
    "École Tilleuls":     ("Mac mini M2", "14.7", 20, "Essentiel"),
    "Lycée Démo":         ("Mac mini M4", "15.5", 80, "Maîtrise"),
    "Collège Renoir":     ("Mac mini M4", "15.5", 60, "Confort"),
}

# --- Reports (chantier N1 etape 4) ------------------------------------------
#
# Seed minimal pour demontrer la page Rapports : ventilation par niveau et par
# mode pedagogique. Le contenu (question/reponse/note) est factice et N'EST
# PAS affiche cote UI (defense en profondeur dans app/services/reports.py).
_REPORTS = [
    # (nom_etab, days_ago, niveaux, mode)
    ("École Saint-Pierre",  1, ["CM1"],         "dialogue"),
    ("École Saint-Pierre",  2, ["CM2"],         "quiz"),
    ("École Saint-Pierre",  4, ["CM1", "CM2"],  "dialogue"),
    ("Collège Voltaire",    1, ["6e"],          "dialogue"),
    ("Collège Voltaire",    3, ["5e", "4e"],    "explication"),
    ("Collège Renoir",      2, ["3e"],          "dialogue"),
    ("Collège Renoir",      5, ["4e"],          "quiz"),
]


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

        # Inventaire (chantier N1 etape 4).
        inv = _INVENTAIRES.get(name)
        if inv is not None:
            model, macos, sieges, formule = inv
            _add_inventaire(
                db, etab.id,
                mac_model=model, macos=macos, sieges=sieges, formule=formule,
            )

        print(f"  ✓ {name} créé")

    # Reports (chantier N1 etape 4) — apres creation des etabs pour disposer des IDs.
    name_to_id = {
        e.name: e.id
        for e in db.scalars(select(Etablissement)).all()
    }
    for etab_name, days_ago, niveaux, mode in _REPORTS:
        etab_id = name_to_id.get(etab_name)
        if etab_id is None:
            continue
        # Idempotence basique : skip si on a deja autant de reports pour cet etab.
        from sqlalchemy import func as _func
        existing = db.scalar(
            select(_func.count()).select_from(Report).where(Report.etablissement_id == etab_id)
        )
        # On ne re-insere pas en double quand seed est relance.
        if existing and existing >= sum(1 for r in _REPORTS if r[0] == etab_name):
            continue
        _add_report(db, etab_id, days_ago=days_ago, niveaux=niveaux, mode=mode)
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
