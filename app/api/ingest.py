"""Point d'entree des push des Mac mini clients (POST /api/ingest)."""

from fastapi import APIRouter, status

from app.api.deps import CurrentEtablissement, DbSession
from app.models import Heartbeat
from app.schemas.heartbeat import HeartbeatAccepted, HeartbeatIn

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED, response_model=HeartbeatAccepted)
def ingest(
    data: HeartbeatIn,
    etablissement: CurrentEtablissement,
    db: DbSession,
) -> HeartbeatAccepted:
    """Recoit un heartbeat de l'etablissement authentifie et le persiste.

    Phase 3.1 : seul le type "heartbeat" minimal est traite. Le corps complet est
    conserve en JSON (`payload`) pour absorber le schema N1 exhaustif (phase 3.2).
    """
    heartbeat = Heartbeat(
        etablissement_id=etablissement.id,
        timestamp=data.timestamp,
        status=data.status,
        payload=data.model_dump(mode="json"),
    )
    db.add(heartbeat)
    db.commit()
    db.refresh(heartbeat)

    return HeartbeatAccepted(received_at=heartbeat.received_at)
