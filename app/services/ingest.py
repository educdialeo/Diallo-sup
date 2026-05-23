"""Dispatch et persistance des push d'ingestion (stockage hybride).

Tout push est consigne dans `raw_pushes` (log brut universel). Les types
frequemment requetes sont en plus ecrits dans une table dediee. Les autres
(`sante_systeme`, `ollama_status`, `dialeo_status`, `logs_critiques`,
`inventaire`) restent uniquement dans `raw_pushes`.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Etablissement, Heartbeat, Incident, RawPush, Report, SessionRecord
from app.schemas.heartbeat import HeartbeatIn
from app.schemas.ingest import (
    IncidentsModerationIn,
    ReportsIn,
    SessionsHistoriquesIn,
    SessionsLiveIn,
)


def store_push(db: Session, etablissement: Etablissement, payload) -> datetime:
    """Persiste un push : log brut systematique + table dediee selon le type."""
    received_at = datetime.now(UTC)
    etab_id = etablissement.id

    db.add(
        RawPush(
            etablissement_id=etab_id,
            type=payload.type,
            timestamp_client=payload.timestamp,
            payload=payload.model_dump(mode="json"),
            received_at=received_at,
        )
    )

    match payload:
        case HeartbeatIn():
            db.add(
                Heartbeat(
                    etablissement_id=etab_id,
                    timestamp=payload.timestamp,
                    status=payload.status,
                    payload=payload.model_dump(mode="json"),
                    received_at=received_at,
                )
            )
        case SessionsLiveIn():
            db.add(
                SessionRecord(
                    etablissement_id=etab_id,
                    kind="live",
                    timestamp_client=payload.timestamp,
                    received_at=received_at,
                    nb_classes_active=payload.nb_classes_active,
                    nb_eleves_connected=payload.nb_eleves_connected,
                    modes=payload.modes_in_use,
                )
            )
        case SessionsHistoriquesIn():
            db.add(
                SessionRecord(
                    etablissement_id=etab_id,
                    kind="historique",
                    timestamp_client=payload.timestamp,
                    received_at=received_at,
                    granularite=payload.granularite,
                    periode=payload.periode,
                    nb_sessions=payload.nb_sessions,
                    nb_eleves=payload.nb_eleves,
                    duree_moyenne_min=payload.duree_moyenne_min,
                    modes=payload.modes_utilises,
                )
            )
        case IncidentsModerationIn():
            db.add(
                Incident(
                    etablissement_id=etab_id,
                    timestamp_client=payload.timestamp,
                    received_at=received_at,
                    window_start=payload.window_start,
                    window_end=payload.window_end,
                    nb_refus_blacklist=payload.nb_refus_blacklist,
                    nb_refus_llamaguard=payload.nb_refus_llamaguard,
                    nb_refus_systemprompt=payload.nb_refus_systemprompt,
                )
            )
        case ReportsIn():
            for item in payload.reports:
                db.add(
                    Report(
                        etablissement_id=etab_id,
                        received_at=received_at,
                        date_jour=item.date_jour,
                        question=item.question,
                        reponse=item.reponse,
                        mode_pedagogique=item.mode_pedagogique,
                        niveau_scolaire=[n.value for n in item.niveau_scolaire],
                        note_enseignant=item.note_enseignant,
                    )
                )
        case _:
            # sante_systeme, ollama_status, dialeo_status, logs_critiques, inventaire :
            # log brut uniquement (promotion en table dediee plus tard si besoin).
            pass

    db.commit()
    return received_at
