"""Chiffrement at-rest des secrets sensibles (Fernet AES-128 + HMAC).

Utilise pour chiffrer le secret TOTP avant de le poser en BDD. La cle est
generee par `python -m app.scripts.init_secrets` et persistee dans .env.

Si la cle est perdue : les secrets TOTP en base deviennent illisibles ;
les utilisateurs ré-enrôlent (les codes de recuperation restent valides
puisqu'ils sont haches independamment, cf docs/RESILIENCE.md).
"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def is_configured() -> bool:
    return bool(settings.totp_at_rest_key)


def generate_key() -> str:
    """Genere une cle Fernet prete pour .env (44 caracteres base64)."""
    return Fernet.generate_key().decode("utf-8")


def _cipher() -> Fernet:
    # Pas de cache module-level : permet aux tests de monkeypatch la cle.
    if not settings.totp_at_rest_key:
        raise RuntimeError("TOTP_AT_REST_KEY manquant — lancer init_secrets.")
    return Fernet(settings.totp_at_rest_key.encode("utf-8"))


def encrypt_at_rest(plain: str) -> str:
    return _cipher().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_at_rest(cipher_text: str) -> str:
    try:
        return _cipher().decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Déchiffrement TOTP impossible (clé changée ?).") from exc
