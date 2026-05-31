"""Endpoints d'auth admin de la console (cookie + JWT)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.jwt import decode_token, encode_session_token
from app.core.passwords import hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "diallosup_session"

# Erreur unique d'auth -> evite l'enumeration d'emails.
_AUTH_FAIL = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Identifiants invalides.",
)
_NOT_CONFIGURED = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail=(
        "Auth non configurée : JWT_SECRET manquant. "
        "Lancer `python -m app.scripts.init_secrets`."
    ),
)

# Hash factice precalcule : sert a equaliser le temps de reponse quand l'email
# n'existe pas (anti-enumeration par timing).
_DUMMY_HASH = hash_password("dummy-anti-enumeration-passphrase-xx")


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
        httponly=True,
        samesite="strict",
        secure=settings.session_cookie_secure,
    )


def require_admin(
    db: Annotated[Session, Depends(get_db)],
    diallosup_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    """Dependance protegeant les routes admin. Refuse 401 si session absente/invalide."""
    if not settings.jwt_secret:
        raise _NOT_CONFIGURED
    if not diallosup_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise.")
    try:
        claims = decode_token(diallosup_session, settings.jwt_secret)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalide ou expirée.") from None
    if claims.get("purpose") != "session":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalide.")
    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalide.") from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalide.")
    return user


@router.post("/login")
def login(
    data: LoginIn,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    if not settings.jwt_secret:
        raise _NOT_CONFIGURED

    email = data.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    # Verification systematique (meme si user None) pour egaliser le temps.
    candidate_hash = user.password_hash if user is not None else _DUMMY_HASH
    password_ok = verify_password(data.password, candidate_hash)

    if user is None or not user.is_active or not password_ok:
        raise _AUTH_FAIL

    user.last_login_at = datetime.now(UTC)
    db.commit()

    token = encode_session_token(
        user.id, timedelta(hours=settings.session_ttl_hours), settings.jwt_secret
    )
    _set_session_cookie(response, token)
    return {"status": "ok"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    # JWT stateless : on ne peut pas invalider le token cote serveur. On efface
    # juste le cookie ; un token vole reste valide jusqu'a exp (cf RESILIENCE.md).
    # On mute l'objet Response injecte (FastAPI applique les en-tetes au retour) ;
    # on ne le RENVOIE PAS, sinon le status 204 du decorateur est ignore.
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="strict",
        secure=settings.session_cookie_secure,
    )


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(require_admin)]) -> User:
    return user
