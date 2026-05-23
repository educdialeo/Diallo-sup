"""Modele ORM de la table 'incidents' (compteurs de moderation anonymises)."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_etab_received", "etablissement_id", "received_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    etablissement_id: Mapped[int] = mapped_column(
        ForeignKey("etablissements.id"), nullable=False, index=True
    )
    timestamp_client: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )

    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    nb_refus_blacklist: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_refus_llamaguard: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_refus_systemprompt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover - confort debug
        return f"<Incident id={self.id} etab={self.etablissement_id}>"
