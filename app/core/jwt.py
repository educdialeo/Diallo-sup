"""Emission et verification des JWT de session (HS256).

Le claim `purpose` separe les futures etapes de l'auth :
- `session`   : session complete (utilisee par require_admin)
- `pre_auth`  : etat post-mdp avant TOTP (phase B) — non emis ici

Cette separation rend l'introduction de la MFA en phase B sans gros refactor :
le login emettra `pre_auth`, le verify TOTP echangera contre `session`.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

_ALG = "HS256"


def encode_session_token(user_id: int, ttl: timedelta, secret: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "purpose": "session",
        "ver": 1,
    }
    return jwt.encode(payload, secret, algorithm=_ALG)


def encode_preauth_token(user_id: int, ttl: timedelta, secret: str) -> str:
    """JWT pre_auth — emis apres le mdp, n'ouvre PAS les routes admin."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "purpose": "pre_auth",
        "ver": 1,
    }
    return jwt.encode(payload, secret, algorithm=_ALG)


def decode_token(token: str, secret: str) -> dict[str, Any]:
    """Renvoie les claims si la signature/exp sont valides ; leve sinon."""
    return jwt.decode(token, secret, algorithms=[_ALG])
