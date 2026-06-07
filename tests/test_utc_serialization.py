"""Tests du type Pydantic UtcDatetime (chantier N1 fix fuseau)."""

from datetime import UTC, datetime, timedelta, timezone

from pydantic import BaseModel

from app.schemas._utc import UtcDatetime


class _M(BaseModel):
    t: UtcDatetime | None = None


def test_aware_utc_serialized_with_z():
    m = _M(t=datetime(2026, 6, 7, 9, 31, 4, tzinfo=UTC))
    assert m.model_dump(mode="json")["t"] == "2026-06-07T09:31:04Z"


def test_naive_treated_as_utc_serialized_with_z():
    """SQLite restitue des datetimes naïfs ; on suppose UTC -> wrap + Z."""
    m = _M(t=datetime(2026, 6, 1, 17, 1, 21, 50934))
    assert m.model_dump(mode="json")["t"] == "2026-06-01T17:01:21.050934Z"


def test_aware_non_utc_converted_to_utc_z():
    cest = timezone(timedelta(hours=2))
    m = _M(t=datetime(2026, 6, 7, 11, 31, 4, tzinfo=cest))  # 09:31:04 UTC
    assert m.model_dump(mode="json")["t"] == "2026-06-07T09:31:04Z"


def test_iso_string_with_z_parsed_and_reserialized_with_z():
    m = _M.model_validate({"t": "2026-05-21T16:30:20Z"})
    assert m.model_dump(mode="json")["t"] == "2026-05-21T16:30:20Z"


def test_iso_string_with_plus_offset_parsed_and_reserialized_with_z():
    m = _M.model_validate({"t": "2026-06-07T10:36:52+00:00"})
    assert m.model_dump(mode="json")["t"] == "2026-06-07T10:36:52Z"


def test_iso_string_without_marker_treated_as_utc():
    """Format SQLite naïf (sans suffixe) -> on suppose UTC."""
    m = _M.model_validate({"t": "2026-06-01T17:01:21.050934"})
    assert m.model_dump(mode="json")["t"] == "2026-06-01T17:01:21.050934Z"


def test_none_stays_none():
    m = _M(t=None)
    assert m.model_dump(mode="json")["t"] is None
