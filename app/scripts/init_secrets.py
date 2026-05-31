"""Genere et persiste les secrets de l'app (JWT_SECRET) dans le .env.

Idempotent : si la cle existe deja, elle est PRESERVEE (jamais regeneree). Les
autres lignes du .env (commentaires, autres variables) sont conservees.
"""

import secrets
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = _REPO_ROOT / ".env"


def _read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _write_env(path: Path, mapping: dict[str, str]) -> None:
    """Reecrit le .env en preservant commentaires/ordre des lignes existantes."""
    lines: list[str] = []
    seen: set[str] = set()
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                lines.append(raw)
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in mapping:
                lines.append(f'{key}="{mapping[key]}"')
                seen.add(key)
            else:
                lines.append(raw)
    for k, v in mapping.items():
        if k not in seen:
            lines.append(f'{k}="{v}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_jwt_secret(env_path: Path = ENV_PATH) -> bool:
    """Cree JWT_SECRET si absent. Renvoie True si genere, False si deja present."""
    env = _read_env(env_path)
    if env.get("JWT_SECRET"):
        return False
    env["JWT_SECRET"] = secrets.token_urlsafe(32)  # 256 bits
    _write_env(env_path, env)
    try:
        env_path.chmod(0o600)
    except OSError:
        pass
    return True


def main() -> int:
    if ensure_jwt_secret():
        print(f"JWT_SECRET généré dans {ENV_PATH}")
    else:
        print(f"JWT_SECRET déjà présent dans {ENV_PATH} (préservé)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
