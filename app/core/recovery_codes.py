"""Codes de récupération à usage unique.

Generation server-side, haute entropie (~32 bits/code). Stockes haches SHA-256
(pas bcrypt — les codes sont aleatoires, pas besoin du facteur de cout). Consommation
= retrait du hash de la liste. Format XXXX-XXXX (8 hex en majuscules + 1 tiret).
"""

import hashlib
import json
import secrets
from collections.abc import Iterable

CODE_COUNT = 10


def _hash(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def generate_codes(n: int = CODE_COUNT) -> list[str]:
    return [
        f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
        for _ in range(n)
    ]


def hash_codes(codes: Iterable[str]) -> list[str]:
    return [_hash(c) for c in codes]


def serialize(hashes: Iterable[str]) -> str:
    return json.dumps(list(hashes))


def deserialize(data: str | None) -> list[str]:
    if not data:
        return []
    try:
        v = json.loads(data)
        return list(v) if isinstance(v, list) else []
    except json.JSONDecodeError:
        return []


def consume(code: str, stored_json: str | None) -> tuple[bool, str | None]:
    """Si `code` matche un hash stocke, le retire et renvoie (True, new_json)."""
    hashes = deserialize(stored_json)
    target = _hash(code)
    if target in hashes:
        hashes.remove(target)
        return True, serialize(hashes)
    return False, stored_json
