"""Dependances FastAPI partagees (authentification API key)."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import hash_api_key
from app.models import Etablissement

# auto_error=False : on gere nous-memes l'absence de header pour renvoyer 401
# (HTTPBearer renverrait 403 par defaut).
_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="API key 256 bits de l'établissement (header Authorization: Bearer <clé>).",
)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Clé API manquante ou invalide.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_etablissement(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Etablissement:
    """Authentifie la requete via l'API key et renvoie l'etablissement actif.

    Hashe la cle recue et la compare au `api_key_hash` stocke. Renvoie 401 si
    aucun etablissement actif ne correspond.
    """
    if credentials is None or not credentials.credentials:
        raise _UNAUTHORIZED

    key_hash = hash_api_key(credentials.credentials)
    etablissement = db.scalar(
        select(Etablissement).where(Etablissement.api_key_hash == key_hash)
    )
    if etablissement is None or etablissement.status != "active":
        raise _UNAUTHORIZED

    return etablissement


CurrentEtablissement = Annotated[Etablissement, Depends(get_current_etablissement)]
DbSession = Annotated[Session, Depends(get_db)]
