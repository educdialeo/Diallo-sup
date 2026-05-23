"""Modele ORM de la table 'raw_pushes' : log brut de TOUS les push, sans exception.

Format normalise pour l'audit et le replay. Chaque push (quel que soit son type)
y est consigne integralement (`payload` JSON), en plus de son eventuelle ecriture
dans une table dediee.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RawPush(Base):
    __tablename__ = "raw_pushes"
    __table_args__ = (
        Index("ix_raw_pushes_etab_type_received", "etablissement_id", "type", "received_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    etablissement_id: Mapped[int] = mapped_column(
        ForeignKey("etablissements.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    timestamp_client: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover - confort debug
        return f"<RawPush id={self.id} etab={self.etablissement_id} type={self.type!r}>"
