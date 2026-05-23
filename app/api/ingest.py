"""Point d'entree des push des Mac mini clients (POST /api/ingest).

Endpoint unique : la validation et le dispatch se font sur le champ `type` du
payload (union discriminee). Tout push est consigne dans `raw_pushes` ; certains
types alimentent en plus une table dediee (cf app/services/ingest.py).
"""

from fastapi import APIRouter, status

from app.api.deps import CurrentEtablissement, DbSession
from app.schemas.ingest import IngestAccepted, IngestPayload
from app.services.ingest import store_push

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED, response_model=IngestAccepted)
def ingest(
    payload: IngestPayload,
    etablissement: CurrentEtablissement,
    db: DbSession,
) -> IngestAccepted:
    """Recoit un push de l'etablissement authentifie, le valide et le persiste."""
    received_at = store_push(db, etablissement, payload)
    return IngestAccepted(type=payload.type, received_at=received_at)
