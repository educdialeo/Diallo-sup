"""Modele ORM de la table 'heartbeats' (donnees poussees par les Mac mini).

Phase 3.1 : seul le type "heartbeat" minimal est recu. Le payload complet est
conserve en JSON pour accueillir le schema N1 exhaustif (10 donnees) en phase 3.2
sans migration de structure.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Heartbeat(Base):
    """Un point de telemetrie recu d'un etablissement."""

    __tablename__ = "heartbeats"
    __table_args__ = (
        # Sert le tri/lecture par etablissement et la future purge a 90 jours.
        Index("ix_heartbeats_etab_received", "etablissement_id", "received_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    etablissement_id: Mapped[int] = mapped_column(
        ForeignKey("etablissements.id"), nullable=False, index=True
    )
    # Horodatage rapporte par le client.
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    # Corps complet recu (evolution N1 sans changement de schema).
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Heure serveur a la reception.
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover - confort debug
        return (
            f"<Heartbeat id={self.id} etablissement_id={self.etablissement_id} "
            f"status={self.status!r} received_at={self.received_at!r}>"
        )
