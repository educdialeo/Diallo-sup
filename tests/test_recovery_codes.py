"""Tests des codes de recuperation (format, hashes, consommation a usage unique)."""

import json
import re

from app.core.recovery_codes import (
    CODE_COUNT,
    consume,
    deserialize,
    generate_codes,
    hash_codes,
    serialize,
)

_CODE_RE = re.compile(r"^[0-9A-F]{4}-[0-9A-F]{4}$")


def test_generate_returns_n_unique_codes_with_format():
    codes = generate_codes()
    assert len(codes) == CODE_COUNT
    assert len(set(codes)) == CODE_COUNT
    for c in codes:
        assert _CODE_RE.fullmatch(c), c


def test_hash_codes_are_sha256_hex():
    codes = generate_codes(3)
    hashes = hash_codes(codes)
    assert len(hashes) == 3
    for h in hashes:
        assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)


def test_serialize_roundtrip():
    hashes = hash_codes(generate_codes(5))
    serialized = serialize(hashes)
    assert json.loads(serialized) == hashes
    assert deserialize(serialized) == hashes


def test_consume_removes_matching_hash_and_returns_new_json():
    codes = generate_codes()
    stored = serialize(hash_codes(codes))
    ok, new_json = consume(codes[0], stored)
    assert ok is True
    assert len(deserialize(new_json)) == CODE_COUNT - 1


def test_consume_same_code_twice_fails_on_second_attempt():
    codes = generate_codes()
    stored = serialize(hash_codes(codes))
    ok1, after = consume(codes[0], stored)
    assert ok1 is True
    ok2, after2 = consume(codes[0], after)
    assert ok2 is False
    assert after2 == after


def test_consume_unknown_code_fails():
    stored = serialize(hash_codes(generate_codes()))
    ok, after = consume("DEAD-BEEF", stored)
    assert ok is False
    assert after == stored
