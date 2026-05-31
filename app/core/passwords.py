"""Hachage et verification des mots de passe (passlib + bcrypt).

bcrypt limite a 72 octets : on tronque explicitement a l'encodage pour un
comportement deterministe, ce qui autorise des passphrases longues sans
plantage et garantit que hash() et verify() voient la meme chose.
"""

from passlib.context import CryptContext

# Longueur minimale d'un mot de passe admin (cf script create_admin).
MIN_PASSWORD_LENGTH = 12

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _truncate_for_bcrypt(plain: str) -> bytes:
    """Renvoie au plus 72 octets UTF-8 (limite stricte de bcrypt)."""
    return plain.encode("utf-8")[:72]


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(_truncate_for_bcrypt(plain))


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_ctx.verify(_truncate_for_bcrypt(plain), hashed)
    except Exception:
        return False
