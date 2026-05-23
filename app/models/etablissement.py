"""Modele ORM de la table 'etablissements' (inventaire / licences)."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Etablissement(Base):
    """Un etablissement supervise (1 Mac mini client Dialeo par etablissement).

    L'API key 256 bits propre a chaque Mac mini n'est jamais stockee en clair :
    seul son hash SHA-256 (`api_key_hash`) est conserve par la console.
    """

    __tablename__ = "etablissements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    api_key_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - confort debug
        return f"<Etablissement id={self.id} name={self.name!r} status={self.status!r}>"
