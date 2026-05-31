"""Schemas I/O pour le flux MFA TOTP (chantier 4 phase B)."""

from pydantic import BaseModel, Field


class LoginStatus(BaseModel):
    """Reponse de POST /api/auth/login (flux 2 etapes)."""

    status: str  # "totp_requis" | "enrolement_requis"


class TotpEnrollOut(BaseModel):
    otpauth_uri: str


class TotpConfirmIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class TotpVerifyIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class RecoveryCodesOut(BaseModel):
    """10 codes de recuperation en clair — affiches UNE SEULE FOIS."""

    recovery_codes: list[str]


class VerifyOk(BaseModel):
    status: str = "ok"
