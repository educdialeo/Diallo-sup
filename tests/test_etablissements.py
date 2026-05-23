"""Test de persistance d'un etablissement en base."""

from app.models import Etablissement


def test_create_etablissement(db_session):
    etab = Etablissement(name="Ecole des Tilleuls", api_key_hash="a" * 64, status="active")
    db_session.add(etab)
    db_session.commit()
    db_session.refresh(etab)

    assert etab.id is not None
    assert etab.created_at is not None

    fetched = db_session.query(Etablissement).filter_by(name="Ecole des Tilleuls").one()
    assert fetched.id == etab.id
    assert fetched.status == "active"
    assert fetched.api_key_hash == "a" * 64
