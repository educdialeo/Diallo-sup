"""Modele ORM de la table 'reports' (reports anonymises, RGPD by design).

Aucune donnee identifiante n'est stockee : la table ne declare QUE les champs
autorises (cf docs/ARCHITECTURE.md §8). La validation a l'entree (schema Pydantic
`extra="forbid"`) refuse tout champ identifiant avec un 400 explicite.
"""

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_etab_date", "etablissement_id", "date_jour"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    etablissement_id: Mapped[int] = mapped_column(
        ForeignKey("etablissements.id"), nullable=False, index=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )

    date_jour: Mapped[date] = mapped_column(Date, nullable=False)  # jour pres, jamais l'heure
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reponse: Mapped[str] = mapped_column(Text, nullable=False)
    mode_pedagogique: Mapped[str] = mapped_column(String, nullable=False)
    niveau_scolaire: Mapped[list] = mapped_column(JSON, nullable=False)  # 1+ niveaux CP->3e
    note_enseignant: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - confort debug
        return f"<Report id={self.id} etab={self.etablissement_id} date={self.date_jour}>"
