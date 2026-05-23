"""Modele ORM de la table 'sessions' (live + historiques agregees).

Une seule table porte les deux natures via la colonne `kind` ('live' | 'historique'),
les colonnes specifiques etant nullables selon le cas. Classe nommee `SessionRecord`
pour eviter la collision avec `sqlalchemy.orm.Session`.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SessionRecord(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_etab_kind_received", "etablissement_id", "kind", "received_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    etablissement_id: Mapped[int] = mapped_column(
        ForeignKey("etablissements.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)  # 'live' | 'historique'
    timestamp_client: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )

    # Sessions live.
    nb_classes_active: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nb_eleves_connected: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Sessions historiques agregees.
    granularite: Mapped[str | None] = mapped_column(String, nullable=True)  # jour|semaine|mois
    periode: Mapped[str | None] = mapped_column(String, nullable=True)
    nb_sessions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nb_eleves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duree_moyenne_min: Mapped[float | None] = mapped_column(Float, nullable=True)

    # modes_in_use (live) ou modes_utilises (historique).
    modes: Mapped[list | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - confort debug
        return f"<SessionRecord id={self.id} etab={self.etablissement_id} kind={self.kind!r}>"
