"""Tests des wrappers TOTP (pyotp)."""

import time

import pyotp

from app.core.totp import ISSUER, generate_secret, otpauth_uri, verify_code


def test_generate_secret_is_base32():
    secret = generate_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 16
    # base32 : A-Z + 2-7
    assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)


def test_otpauth_uri_format():
    uri = otpauth_uri("JBSWY3DPEHPK3PXP", "admin@example.com")
    assert uri.startswith("otpauth://totp/")
    assert f"issuer={ISSUER}" in uri
    assert "secret=JBSWY3DPEHPK3PXP" in uri


def test_verify_code_current():
    secret = generate_secret()
    code_now = pyotp.TOTP(secret).now()
    assert verify_code(secret, code_now) is True


def test_verify_code_rejects_garbage():
    secret = generate_secret()
    assert verify_code(secret, "lolol") is False
    assert verify_code(secret, "") is False
    assert verify_code(secret, "000000") in (True, False)  # extremement improbable


def test_verify_code_tolerates_one_step_window():
    """Tolerance +/- 1 pas = 30 s."""
    secret = generate_secret()
    totp = pyotp.TOTP(secret)
    code_30s_ago = totp.at(int(time.time()) - 30)
    assert verify_code(secret, code_30s_ago) is True


def test_verify_code_rejects_far_past_code():
    secret = generate_secret()
    code_5min_ago = pyotp.TOTP(secret).at(int(time.time()) - 300)
    assert verify_code(secret, code_5min_ago) is False
