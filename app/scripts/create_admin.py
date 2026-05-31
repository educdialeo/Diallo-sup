"""Bootstrap interactif d'un compte admin.

Usage : `python -m app.scripts.create_admin`
Demande email + mot de passe (getpass, jamais en argv). Cree le secret JWT
si absent puis insere l'admin en base. Refuse les doublons d'email et les
mots de passe < MIN_PASSWORD_LENGTH.
"""

import getpass
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, init_db
from app.core.passwords import MIN_PASSWORD_LENGTH, hash_password
from app.models import User
from app.scripts.init_secrets import ensure_jwt_secret


def create_admin(email: str, password: str, db: Session) -> User:
    """Logique pure (testable). Leve ValueError sur entree invalide / doublon."""
    email = email.strip().lower()
    if not email:
        raise ValueError("Email vide.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Mot de passe trop court ({len(password)} caractères, "
            f"min {MIN_PASSWORD_LENGTH})."
        )
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise ValueError(f"Un admin avec l'email {email!r} existe déjà.")
    user = User(
        email=email,
        password_hash=hash_password(password),
        is_active=True,
        totp_enrolled=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def main() -> int:
    if ensure_jwt_secret():
        print("JWT_SECRET généré.")
    # Cree les tables si necessaire (au cas ou le service n'a jamais demarre).
    init_db()

    email = input("Email admin : ").strip().lower()
    pw1 = getpass.getpass(f"Mot de passe (min {MIN_PASSWORD_LENGTH}) : ")
    pw2 = getpass.getpass("Confirmer : ")
    if pw1 != pw2:
        print("❌ Les mots de passe ne correspondent pas.", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        user = create_admin(email, pw1, db)
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(f"✅ Admin créé : id={user.id} email={user.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
