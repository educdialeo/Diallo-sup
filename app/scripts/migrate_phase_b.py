"""Migration Phase B : ALTER TABLE users ADD COLUMN failed_login_count, locked_until.

Idempotent : on lit `PRAGMA table_info(users)` et on n'ajoute que les colonnes
manquantes. SQLite supporte `ALTER TABLE ADD COLUMN` (avec defaut constant)
depuis longtemps — sans besoin d'Alembic pour cette phase.

À lancer AVANT le redémarrage launchd lors du déploiement de la Phase B
(cf docs/RESILIENCE.md).
"""

import sys

from sqlalchemy import Engine, text

from app.core.db import engine

_TARGETS: dict[str, str] = {
    "failed_login_count": "INTEGER NOT NULL DEFAULT 0",
    "locked_until": "DATETIME",
}


def _existing_columns(conn) -> set[str]:
    rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
    return {r[1] for r in rows}


def migrate(eng: Engine = engine) -> list[str]:
    """Renvoie la liste des colonnes effectivement ajoutees."""
    added: list[str] = []
    with eng.begin() as conn:
        existing = _existing_columns(conn)
        for col, ddl in _TARGETS.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {ddl}"))
                added.append(col)
    return added


def main() -> int:
    added = migrate()
    if added:
        print(f"Colonnes ajoutées : {', '.join(added)}")
    else:
        print("Schéma déjà à jour (no-op).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
