"""Tests purs de la fonction de calcul de sante live (chantier N1, fleet)."""

from datetime import UTC, datetime, timedelta

from app.services.fleet import compute_health

_NOW = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)


def test_no_heartbeat_is_silent():
    assert compute_health(_NOW, None, None) == "silent"


def test_recent_ok_is_online():
    assert compute_health(_NOW, _NOW - timedelta(minutes=1), "ok") == "online"


def test_recent_non_ok_status_is_degraded():
    assert compute_health(_NOW, _NOW - timedelta(minutes=1), "warning") == "degraded"
    assert compute_health(_NOW, _NOW - timedelta(minutes=1), "error") == "degraded"


def test_eight_minutes_old_ok_is_degraded():
    assert compute_health(_NOW, _NOW - timedelta(minutes=8), "ok") == "degraded"


def test_thirty_minutes_old_is_silent():
    assert compute_health(_NOW, _NOW - timedelta(minutes=30), "ok") == "silent"


def test_at_threshold_boundaries():
    # Exactement 5 min -> online (>5 devient degraded)
    assert compute_health(_NOW, _NOW - timedelta(minutes=5), "ok") == "online"
    # Exactement 15 min -> degraded (>15 devient silent)
    assert compute_health(_NOW, _NOW - timedelta(minutes=15), "ok") == "degraded"


def test_naive_datetime_treated_as_utc():
    naive = (_NOW - timedelta(minutes=1)).replace(tzinfo=None)
    assert compute_health(_NOW, naive, "ok") == "online"


def test_silent_dominates_over_status():
    """Vieux heartbeat status="ok" reste silent, status="error" aussi (silent prime)."""
    assert compute_health(_NOW, _NOW - timedelta(minutes=20), "error") == "silent"
