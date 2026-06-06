"""Tests du garde-fou anti-prod du script seed_fleet."""

from app.scripts.seed_fleet import _DEFAULT_URL, _PROD_DB_PATH, _is_prod_db


def test_default_url_is_refused():
    assert _is_prod_db(_DEFAULT_URL) is True


def test_absolute_prod_path_is_refused():
    assert _is_prod_db(f"sqlite:///{_PROD_DB_PATH}") is True


def test_tmp_path_is_accepted():
    assert _is_prod_db("sqlite:////tmp/diallo_fleet_seed.db") is False


def test_non_sqlite_url_is_accepted():
    assert _is_prod_db("postgresql://localhost/diallosup") is False


def test_arbitrary_other_path_is_accepted(tmp_path):
    target = tmp_path / "fleet_demo.db"
    assert _is_prod_db(f"sqlite:///{target}") is False
