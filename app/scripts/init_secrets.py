"""Genere et persiste les secrets de l'app (JWT_SECRET, TOTP_AT_REST_KEY) dans .env.

Idempotent : toute cle existante est PRESERVEE (jamais regeneree). Les autres
lignes du .env (commentaires, autres variables) sont conservees.
"""

import secrets
import sys
from pathlib import Path

from cryptography.fernet import Fernet

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


def ensure_secrets(env_path: Path = ENV_PATH) -> dict[str, bool]:
    """Cree les secrets manquants. Renvoie {nom: True_si_genere_now}."""
    env = _read_env(env_path)
    generated: dict[str, bool] = {"JWT_SECRET": False, "TOTP_AT_REST_KEY": False}

    if not env.get("JWT_SECRET"):
        env["JWT_SECRET"] = secrets.token_urlsafe(32)  # 256 bits
        generated["JWT_SECRET"] = True

    if not env.get("TOTP_AT_REST_KEY"):
        env["TOTP_AT_REST_KEY"] = Fernet.generate_key().decode("utf-8")
        generated["TOTP_AT_REST_KEY"] = True

    if any(generated.values()):
        _write_env(env_path, env)
        try:
            env_path.chmod(0o600)
        except OSError:
            pass
    return generated


def ensure_jwt_secret(env_path: Path = ENV_PATH) -> bool:
    """Alias historique (chantier 4 phase A). Garanti `JWT_SECRET` ET les autres."""
    return ensure_secrets(env_path)["JWT_SECRET"]


def main() -> int:
    result = ensure_secrets()
    for name, was_generated in result.items():
        status = "généré" if was_generated else "déjà présent (préservé)"
        print(f"{name} : {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
