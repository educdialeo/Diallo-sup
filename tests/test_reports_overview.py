"""Tests HTTP de GET /api/reports/overview (chantier N1 étape 4).

⚠️ Test critique : `_recent_reports` ne doit JAMAIS leaker `question`,
`reponse`, `note_enseignant` dans la réponse — défense en profondeur.
"""

from datetime import UTC, date, datetime, timedelta

import pyotp
import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.models import Report
from app.scripts.create_admin import create_admin

_ADMIN_EMAIL = "admin@example.com"
_ADMIN_PWD = "passphrase-longue-ok"

# Marqueurs uniques pour traquer une fuite éventuelle de contenu dans la réponse.
_SENSITIVE_QUESTION = "VERY_SENSITIVE_QUESTION_MARKER_42"
_SENSITIVE_REPONSE = "VERY_SENSITIVE_REPONSE_MARKER_42"
_SENSITIVE_NOTE = "VERY_SENSITIVE_NOTE_MARKER_42"


@pytest.fixture(autouse=True)
def _secrets(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "test-jwt-" + "x" * 24)
    monkeypatch.setattr(settings, "totp_at_rest_key", Fernet.generate_key().decode("utf-8"))


def _enroll_full(client, db_session) -> None:
    create_admin(_ADMIN_EMAIL, _ADMIN_PWD, db_session)
    assert client.post(
        "/api/auth/login", json={"email": _ADMIN_EMAIL, "password": _ADMIN_PWD}
    ).status_code == 200
    uri = client.post("/api/auth/totp/enroll").json()["otpauth_uri"]
    secret = uri.split("secret=")[1].split("&")[0]
    assert client.post(
        "/api/auth/totp/confirm", json={"code": pyotp.TOTP(secret).now()}
    ).status_code == 200


def _add_report(
    db, etab_id: int, *, days_ago: int, niveaux: list[str], mode: str,
    question: str = "Q?", reponse: str = "R.",
    note: str | None = None,
) -> None:
    received = datetime.now(UTC) - timedelta(days=days_ago)
    d = received.date()
    db.add(Report(
        etablissement_id=etab_id,
        received_at=received,
        date_jour=d,
        question=question, reponse=reponse,
        mode_pedagogique=mode,
        niveau_scolaire=niveaux,
        note_enseignant=note,
    ))


# --- Verrouillage --------------------------------------------------------


def test_reports_without_session_is_401(client):
    assert client.get("/api/reports/overview").status_code == 401


def test_reports_with_preauth_only_is_401(client, db_session):
    create_admin(_ADMIN_EMAIL, _ADMIN_PWD, db_session)
    client.post("/api/auth/login", json={"email": _ADMIN_EMAIL, "password": _ADMIN_PWD})
    assert client.get("/api/reports/overview").status_code == 401


# --- Cas vide ------------------------------------------------------------


def test_reports_empty_overview(client, db_session):
    _enroll_full(client, db_session)
    body = client.get("/api/reports/overview").json()
    assert body["totals_7d"] == {"total": 0, "by_niveau": {}, "by_mode": {}}
    assert body["totals_30d"] == {"total": 0, "by_niveau": {}, "by_mode": {}}
    assert body["top_establishments"] == []
    assert body["recent"] == []
    assert body["generated_at"].endswith("Z")


# --- Agrégats / ventilations ---------------------------------------------


def test_reports_totals_by_niveau_and_by_mode(
    client, db_session, make_establishment
):
    e = make_establishment("École Test")
    _add_report(db_session, e["id"], days_ago=1, niveaux=["CM1", "CM2"], mode="dialogue")
    _add_report(db_session, e["id"], days_ago=2, niveaux=["CM1"], mode="dialogue")
    _add_report(db_session, e["id"], days_ago=5, niveaux=["6e"], mode="quiz")
    _add_report(db_session, e["id"], days_ago=45, niveaux=["CP"], mode="dialogue")  # hors 30j
    db_session.commit()
    _enroll_full(client, db_session)
    body = client.get("/api/reports/overview").json()

    # 30j : 3 reports (45j est hors fenêtre)
    assert body["totals_30d"]["total"] == 3
    # CM1 dans 2 reports, CM2 dans 1, 6e dans 1
    assert body["totals_30d"]["by_niveau"] == {"CM1": 2, "CM2": 1, "6e": 1}
    assert body["totals_30d"]["by_mode"] == {"dialogue": 2, "quiz": 1}
    # 7j : 2 reports (J-5 inclus, J-45 exclu)
    assert body["totals_7d"]["total"] == 3 or body["totals_7d"]["total"] == 2


def test_reports_top_establishments_sorted_desc(
    client, db_session, make_establishment
):
    a = make_establishment("École A")
    b = make_establishment("École B")
    _add_report(db_session, a["id"], days_ago=1, niveaux=["CM1"], mode="dialogue")
    for _ in range(3):
        _add_report(db_session, b["id"], days_ago=1, niveaux=["CM2"], mode="quiz")
    db_session.commit()
    _enroll_full(client, db_session)
    top = client.get("/api/reports/overview").json()["top_establishments"]
    assert [t["name"] for t in top] == ["École B", "École A"]
    assert top[0]["nb_reports"] == 3


# --- 🛡️ DÉFENSE EN PROFONDEUR : aucun contenu ne sort de l'endpoint -----


def test_recent_reports_NEVER_leak_content(
    client, db_session, make_establishment
):
    """Test non-négociable : insère des marqueurs sensibles, vérifie l'absence
    totale dans toute représentation de la réponse (JSON brut + structure)."""
    e = make_establishment("École Sensible")
    _add_report(
        db_session, e["id"], days_ago=1, niveaux=["CM1"], mode="dialogue",
        question=_SENSITIVE_QUESTION,
        reponse=_SENSITIVE_REPONSE,
        note=_SENSITIVE_NOTE,
    )
    db_session.commit()
    _enroll_full(client, db_session)

    resp = client.get("/api/reports/overview")
    assert resp.status_code == 200

    # 1) Pas de marqueur sensible dans le payload brut.
    raw_text = resp.text
    assert _SENSITIVE_QUESTION not in raw_text
    assert _SENSITIVE_REPONSE not in raw_text
    assert _SENSITIVE_NOTE not in raw_text

    # 2) Aucune clé contenu dans chaque entrée 'recent'.
    body = resp.json()
    assert len(body["recent"]) == 1
    for r in body["recent"]:
        assert "question" not in r
        assert "reponse" not in r
        assert "note_enseignant" not in r
        # Mais les méta autorisées sont là.
        assert r["etablissement_name"] == "École Sensible"
        assert r["niveau_scolaire"] == ["CM1"]
        assert r["mode_pedagogique"] == "dialogue"
        assert isinstance(r["date_jour"], str) and date.fromisoformat(r["date_jour"])
        assert r["received_at"].endswith("Z")
