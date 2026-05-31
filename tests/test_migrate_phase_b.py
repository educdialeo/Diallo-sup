"""Test du script de migration Phase B (ALTER idempotent)."""

from sqlalchemy import create_engine, text

from app.scripts.migrate_phase_b import migrate


def _create_phase_a_users_table(eng) -> None:
    """Recree la table users telle qu'elle existait en phase A (sans les 2 nouvelles colonnes)."""
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR NOT NULL UNIQUE,
                    password_hash VARCHAR NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    totp_secret VARCHAR,
                    totp_enrolled BOOLEAN NOT NULL,
                    recovery_codes TEXT,
                    created_at DATETIME NOT NULL,
                    last_login_at DATETIME
                )
                """
            )
        )


def _columns(eng) -> set[str]:
    with eng.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        return {r[1] for r in rows}


def test_migrate_adds_missing_columns(tmp_path):
    eng = create_engine(
        f"sqlite:///{tmp_path / 'old.db'}", connect_args={"check_same_thread": False}
    )
    _create_phase_a_users_table(eng)
    assert "failed_login_count" not in _columns(eng)
    assert "locked_until" not in _columns(eng)

    added = migrate(eng)
    assert set(added) == {"failed_login_count", "locked_until"}
    assert "failed_login_count" in _columns(eng)
    assert "locked_until" in _columns(eng)


def test_migrate_is_idempotent(tmp_path):
    eng = create_engine(
        f"sqlite:///{tmp_path / 'old.db'}", connect_args={"check_same_thread": False}
    )
    _create_phase_a_users_table(eng)
    migrate(eng)
    added_again = migrate(eng)
    assert added_again == []
