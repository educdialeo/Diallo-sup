"""Endpoints d'auth admin de la console : flux 2 etapes (mdp + TOTP) + MFA.

Chantier 4 phase B :
- /login emet un JWT pre_auth (5 min) au lieu d'une session complete
- /totp/enroll + /totp/confirm pour le 1er enrolement (codes de recup en clair 1x)
- /verify-totp consomme un code TOTP ou un code de recuperation -> session
- require_admin n'accepte que purpose="session" (inchange)
- lockout par compte sur /login + /verify-totp + /totp/confirm
- compteur RESET uniquement sur session complete (verify-totp OK ou confirm OK)
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_at_rest, encrypt_at_rest
from app.core.crypto import is_configured as crypto_configured
from app.core.db import get_db
from app.core.jwt import decode_token, encode_preauth_token, encode_session_token
from app.core.passwords import hash_password, verify_password
from app.core.recovery_codes import (
    consume as consume_recovery_code,
)
from app.core.recovery_codes import (
    generate_codes,
    hash_codes,
    serialize,
)
from app.core.totp import generate_secret, otpauth_uri, verify_code
from app.models import User
from app.schemas.auth import LoginIn, UserOut
from app.schemas.auth_mfa import (
    LoginStatus,
    RecoveryCodesOut,
    TotpConfirmIn,
    TotpEnrollOut,
    TotpVerifyIn,
    VerifyOk,
)
from app.services.auth_lockout import (
    is_locked,
    register_failure,
    register_session_established,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "diallosup_session"

# Erreurs unifiees -> evitent l'enumeration et donnent des messages stables.
_AUTH_FAIL = HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides.")
_TOTP_FAIL = HTTPException(status.HTTP_401_UNAUTHORIZED, "Code invalide.")
_LOCKED = HTTPException(status.HTTP_423_LOCKED, "Compte temporairement verrouillé.")
_UNAUTHENTICATED = HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise.")
_ALREADY_ENROLLED = HTTPException(status.HTTP_409_CONFLICT, "TOTP déjà enrôlé.")
_NOT_ENROLLED = HTTPException(status.HTTP_409_CONFLICT, "TOTP non enrôlé.")
_NO_PENDING_ENROLL = HTTPException(
    status.HTTP_400_BAD_REQUEST,
    "Aucun enrôlement TOTP en cours. Appelez d'abord /api/auth/totp/enroll.",
)
_NOT_CONFIGURED = HTTPException(
    status.HTTP_503_SERVICE_UNAVAILABLE,
    "Auth non configurée : JWT_SECRET manquant. "
    "Lancer `python -m app.scripts.init_secrets`.",
)
_CRYPTO_NOT_CONFIGURED = HTTPException(
    status.HTTP_503_SERVICE_UNAVAILABLE,
    "Chiffrement at-rest non configuré : TOTP_AT_REST_KEY manquant.",
)

# Hash factice precalcule : egaliser le temps quand l'email est inconnu (anti-enum).
_DUMMY_HASH = hash_password("dummy-anti-enumeration-passphrase-xx")


# --- Cookies -----------------------------------------------------------------

def _set_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=max_age_seconds,
        path="/",
        httponly=True,
        samesite="strict",
        secure=settings.session_cookie_secure,
    )


def _set_preauth_cookie(response: Response, user_id: int) -> None:
    assert settings.jwt_secret  # garanti par check amont
    token = encode_preauth_token(
        user_id,
        timedelta(minutes=settings.preauth_ttl_minutes),
        settings.jwt_secret,
    )
    _set_cookie(response, token, settings.preauth_ttl_minutes * 60)


def _set_session_cookie(response: Response, user_id: int) -> None:
    assert settings.jwt_secret
    token = encode_session_token(
        user_id,
        timedelta(hours=settings.session_ttl_hours),
        settings.jwt_secret,
    )
    _set_cookie(response, token, settings.session_ttl_hours * 3600)


# --- Decodage cookie ---------------------------------------------------------

def _decode_cookie(cookie: str | None) -> tuple[int, str] | None:
    """Renvoie (user_id, purpose) ou None si invalide/expire."""
    if not settings.jwt_secret or not cookie:
        return None
    try:
        claims = decode_token(cookie, settings.jwt_secret)
        return int(claims["sub"]), claims.get("purpose", "")
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None


def _resolve_user(db: Session, user_id: int) -> User | None:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


# --- Dependances -------------------------------------------------------------

def require_admin(
    db: Annotated[Session, Depends(get_db)],
    diallosup_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    """Strict : exige une session complete (purpose=='session'). 401 sinon."""
    if not settings.jwt_secret:
        raise _NOT_CONFIGURED
    parsed = _decode_cookie(diallosup_session)
    if parsed is None or parsed[1] != "session":
        raise _UNAUTHENTICATED
    user = _resolve_user(db, parsed[0])
    if user is None:
        raise _UNAUTHENTICATED
    return user


def require_authenticated(
    db: Annotated[Session, Depends(get_db)],
    diallosup_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> tuple[User, str]:
    """Accepte pre_auth OU session. Renvoie (user, purpose). Utilise par enroll/confirm."""
    if not settings.jwt_secret:
        raise _NOT_CONFIGURED
    parsed = _decode_cookie(diallosup_session)
    if parsed is None or parsed[1] not in ("pre_auth", "session"):
        raise _UNAUTHENTICATED
    user = _resolve_user(db, parsed[0])
    if user is None:
        raise _UNAUTHENTICATED
    return user, parsed[1]


def require_preauth(
    db: Annotated[Session, Depends(get_db)],
    diallosup_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    """Stricte sur pre_auth (utilisee par /verify-totp)."""
    if not settings.jwt_secret:
        raise _NOT_CONFIGURED
    parsed = _decode_cookie(diallosup_session)
    if parsed is None or parsed[1] != "pre_auth":
        raise _UNAUTHENTICATED
    user = _resolve_user(db, parsed[0])
    if user is None:
        raise _UNAUTHENTICATED
    return user


# --- Endpoints ---------------------------------------------------------------

@router.post("/login", response_model=LoginStatus)
def login(
    data: LoginIn,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> LoginStatus:
    """Etape 1/2 : mot de passe. Emet UNIQUEMENT un JWT pre_auth (jamais une session)."""
    if not settings.jwt_secret:
        raise _NOT_CONFIGURED

    email = data.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    # Lock check pour les comptes connus (pas pour email inconnu -> anti-enum).
    if user is not None and is_locked(user):
        raise _LOCKED

    # Verification systematique (egalisation timing meme si user None).
    candidate_hash = user.password_hash if user is not None else _DUMMY_HASH
    password_ok = verify_password(data.password, candidate_hash)

    if user is None or not user.is_active or not password_ok:
        # Compte l'echec UNIQUEMENT si le user existe et est actif.
        if user is not None and user.is_active:
            register_failure(user, db)
        raise _AUTH_FAIL

    # ⚠️ Pwd OK : on NE RESET PAS le compteur (decision phase B).
    user.last_login_at = datetime.now(UTC)
    db.commit()

    _set_preauth_cookie(response, user.id)
    return LoginStatus(status="totp_requis" if user.totp_enrolled else "enrolement_requis")


@router.post("/totp/enroll", response_model=TotpEnrollOut)
def totp_enroll(
    auth: Annotated[tuple[User, str], Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> TotpEnrollOut:
    """Genere un secret TOTP provisoire (encrypte at-rest) et renvoie l'URI."""
    if not crypto_configured():
        raise _CRYPTO_NOT_CONFIGURED
    user, _purpose = auth
    if user.totp_enrolled:
        raise _ALREADY_ENROLLED

    secret = generate_secret()
    user.totp_secret = encrypt_at_rest(secret)
    db.commit()
    return TotpEnrollOut(otpauth_uri=otpauth_uri(secret, user.email))


@router.post("/totp/confirm", response_model=RecoveryCodesOut)
def totp_confirm(
    data: TotpConfirmIn,
    response: Response,
    auth: Annotated[tuple[User, str], Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> RecoveryCodesOut:
    """Confirme l'enrolement : flip enrolled=True, emet recovery codes + session."""
    if not crypto_configured():
        raise _CRYPTO_NOT_CONFIGURED
    user, _purpose = auth

    if user.totp_enrolled:
        raise _ALREADY_ENROLLED
    if not user.totp_secret:
        raise _NO_PENDING_ENROLL
    if is_locked(user):
        raise _LOCKED

    plain_secret = decrypt_at_rest(user.totp_secret)
    if not verify_code(plain_secret, data.code):
        register_failure(user, db)
        raise _TOTP_FAIL

    # Confirm OK -> on ouvre une session COMPLETE.
    codes = generate_codes()
    user.recovery_codes = serialize(hash_codes(codes))
    user.totp_enrolled = True
    register_session_established(user, db)  # commit inclus + reset compteur
    _set_session_cookie(response, user.id)
    return RecoveryCodesOut(recovery_codes=codes)


@router.post("/verify-totp", response_model=VerifyOk)
def verify_totp(
    data: TotpVerifyIn,
    response: Response,
    user: Annotated[User, Depends(require_preauth)],
    db: Annotated[Session, Depends(get_db)],
) -> VerifyOk:
    """Etape 2/2 : verifie un code TOTP ou un code de recuperation. Emet la session."""
    if not crypto_configured():
        raise _CRYPTO_NOT_CONFIGURED
    if not user.totp_enrolled or not user.totp_secret:
        raise _NOT_ENROLLED
    if is_locked(user):
        raise _LOCKED

    # TOTP en premier.
    plain_secret = decrypt_at_rest(user.totp_secret)
    if verify_code(plain_secret, data.code):
        register_session_established(user, db)
        _set_session_cookie(response, user.id)
        return VerifyOk()

    # Sinon : code de recuperation (consomme si match).
    ok, new_codes_json = consume_recovery_code(data.code, user.recovery_codes)
    if ok:
        user.recovery_codes = new_codes_json
        register_session_established(user, db)
        _set_session_cookie(response, user.id)
        return VerifyOk()

    register_failure(user, db)
    raise _TOTP_FAIL


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Efface le cookie de session. ⚠️ JWT stateless : un token volé reste valide
    jusqu'à exp (12 h). Pour invalider toutes les sessions vivantes, rotation
    de JWT_SECRET (cf docs/RESILIENCE.md)."""
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
