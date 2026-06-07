"""Schemas I/O pour l'auth admin."""

from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas._utc import UtcDatetime


class LoginIn(BaseModel):
    """Corps de login. Volontairement laxiste sur le format pour ne pas leaker
    par 422 (toute auth invalide finit en 401 generique cote endpoint)."""

    email: str
    password: str


class UserOut(BaseModel):
    """Profil renvoye par GET /api/auth/me."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    last_login_at: UtcDatetime | None = None
