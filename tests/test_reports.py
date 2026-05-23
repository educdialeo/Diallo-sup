"""Tests d'ingestion des reports : validite + anonymisation stricte (400)."""

import pytest

from app.models import Report

TS = "2026-05-23T14:00:00Z"


@pytest.fixture()
def headers(make_establishment):
    etab = make_establishment("École Reports")
    return {"Authorization": f"Bearer {etab['api_key']}"}


def _reports_payload(item_extra: dict | None = None) -> dict:
    item = {
        "date_jour": "2026-05-22",
        "question": "Pourquoi le ciel est bleu ?",
        "reponse": "Diffusion de la lumière.",
        "mode_pedagogique": "dialogue",
        "niveau_scolaire": ["CM1"],
    }
    if item_extra:
        item.update(item_extra)
    return {"type": "reports", "timestamp": TS, "reports": [item]}


def test_reports_valid_is_202_and_stored(client, headers, db_session):
    resp = client.post("/api/ingest", headers=headers, json=_reports_payload())
    assert resp.status_code == 202
    rows = db_session.query(Report).all()
    assert len(rows) == 1
    assert rows[0].niveau_scolaire == ["CM1"]


def test_reports_forbidden_identifying_field_is_400(client, headers):
    resp = client.post("/api/ingest", headers=headers, json=_reports_payload({"prenom": "Léa"}))
    assert resp.status_code == 400
    detail = resp.json()["detail"].lower()
    assert "interdit" in detail and "prenom" in detail


def test_reports_unknown_field_is_400(client, headers):
    resp = client.post("/api/ingest", headers=headers, json=_reports_payload({"foobar": "x"}))
    assert resp.status_code == 400


def test_reports_invalid_niveau_is_422(client, headers):
    resp = client.post(
        "/api/ingest", headers=headers, json=_reports_payload({"niveau_scolaire": ["CM7"]})
    )
    assert resp.status_code == 422


def test_reports_multi_niveau_is_accepted(client, headers, db_session):
    resp = client.post(
        "/api/ingest",
        headers=headers,
        json=_reports_payload({"niveau_scolaire": ["CM1", "CM2", "6e"]}),
    )
    assert resp.status_code == 202
    assert db_session.query(Report).one().niveau_scolaire == ["CM1", "CM2", "6e"]
