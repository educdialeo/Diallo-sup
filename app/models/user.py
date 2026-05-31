"""Modele ORM de la table 'users' (admins de la console).

Phase A : email + mot de passe + session. Les champs TOTP et recovery_codes
sont declares ici mais resteront a leur valeur par defaut tant que la phase B
n'est pas livree.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # === Reserve phase B (MFA TOTP) ===
    totp_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    totp_enrolled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recovery_codes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON liste

    # === Lockout (chantier 4 phase B) ===
    # ⚠️ Le compteur n'est RESET que sur etablissement d'une session complete
    # (verify-totp OK ou confirm OK), JAMAIS sur succes du mdp seul.
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # === Audit ===
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - confort debug
        return f"<User id={self.id} email={self.email!r} active={self.is_active}>"
