"""Generation et hachage des API keys des etablissements.

Chaque Mac mini client s'authentifie aupres de la console avec une API key
de 256 bits. La console ne stocke jamais la cle en clair : seul son hash
SHA-256 est conserve (colonne `etablissements.api_key_hash`).
"""

import hashlib
import secrets

# 32 octets = 256 bits d'entropie, encodes en base64 URL-safe (~43 caracteres).
_API_KEY_NBYTES = 32


def generate_api_key() -> str:
    """Genere une API key cryptographiquement sure (256 bits)."""
    return secrets.token_urlsafe(_API_KEY_NBYTES)


def hash_api_key(api_key: str) -> str:
    """Renvoie le hash SHA-256 hexadecimal d'une API key."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
