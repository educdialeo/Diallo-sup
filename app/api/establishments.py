"""Endpoints etablissements : creation (admin) et relecture des heartbeats."""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentEtablissement, DbSession
from app.core.security import generate_api_key, hash_api_key
from app.models import Etablissement, Heartbeat
from app.schemas.establishment import EstablishmentCreate, EstablishmentCreated
from app.schemas.heartbeat import HeartbeatOut

router = APIRouter(prefix="/api", tags=["establishments"])


@router.post(
    "/establishments",
    status_code=status.HTTP_201_CREATED,
    response_model=EstablishmentCreated,
)
def create_establishment(data: EstablishmentCreate, db: DbSession) -> EstablishmentCreated:
    """Cree un etablissement et renvoie son API key en clair (UNE SEULE FOIS).

    ⚠️ ENDPOINT ADMIN — non protege en local pour la phase 3.1.
    DOIT etre derriere Cloudflare Access en prod (cf. ARCHITECTURE.md §7.1).
    A securiser AVANT toute exposition externe.
    """
    if db.scalar(select(Etablissement).where(Etablissement.name == data.name)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un établissement porte déjà ce nom.",
        )

    api_key = generate_api_key()
    etablissement = Etablissement(
        name=data.name,
        api_key_hash=hash_api_key(api_key),
        status="active",
    )
    db.add(etablissement)
    db.commit()
    db.refresh(etablissement)

    # L'API key en clair n'existe qu'ici : elle n'est ni stockee ni reloggable.
    return EstablishmentCreated(
        id=etablissement.id,
        name=etablissement.name,
        api_key=api_key,
        created_at=etablissement.created_at,
    )


@router.get(
    "/establishments/{etablissement_id}/heartbeats",
    response_model=list[HeartbeatOut],
)
def list_heartbeats(
    etablissement_id: int,
    etablissement: CurrentEtablissement,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=1000),
) -> list[Heartbeat]:
    """Renvoie les N derniers heartbeats de l'etablissement authentifie.

    Un etablissement ne peut relire QUE ses propres heartbeats.
    """
    if etablissement.id != etablissement_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit aux heartbeats d'un autre établissement.",
        )

    return list(
        db.scalars(
            select(Heartbeat)
            .where(Heartbeat.etablissement_id == etablissement_id)
            .order_by(Heartbeat.received_at.desc(), Heartbeat.id.desc())
            .limit(limit)
        ).all()
    )
