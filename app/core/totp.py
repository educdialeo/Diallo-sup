"""Wrappers TOTP (pyotp) — secrets, URI otpauth, verification."""

import pyotp

ISSUER = "DialSup"


def generate_secret() -> str:
    """Secret TOTP base32 (160 bits)."""
    return pyotp.random_base32()


def otpauth_uri(secret: str, account_email: str) -> str:
    """URI otpauth:// acceptee par tout authenticator (Google, Microsoft, Authy)."""
    return pyotp.TOTP(secret).provisioning_uri(name=account_email, issuer_name=ISSUER)


def verify_code(secret: str, code: str, valid_window: int = 1) -> bool:
    """Verifie un code TOTP a 6 chiffres, tolerance +/- valid_window pas (30 s)."""
    if not code or not code.isdigit():
        return False
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=valid_window)
    except Exception:
        return False
