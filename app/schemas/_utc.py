"""Type Pydantic centralise pour les datetimes des reponses API.

Garantit que toute datetime renvoyee par un endpoint sort en UTC explicite
(suffixe `Z`), quel que soit son etat d'entree :

- naïve depuis SQLite (limitation : SQLite strip la tz, restitue naïf),
- aware depuis du Python (`datetime.now(UTC)`),
- parsee d'une string ISO avec ou sans suffixe.

Hypothese fondamentale assumee : un datetime naïve cote serveur est UTC.
Verifications concretes faites le 2026-06-07 :
- Datetimes crees par notre code : `datetime.now(UTC)` -> aware UTC (et
  stockes en SQLite qui strip la tz -> naïve UTC en BDD). Wrap = no-op
  semantique.
- Datetimes issus du payload M4 dans `raw_pushes` (last_boot,
  last_success_iso) : marqueurs de fuseau explicites observes en prod
  (`Z` ou `+00:00`). Pydantic parse en aware. `_ensure_utc` idempotent.

Si un emetteur futur (M4 ou autre) envoyait un datetime naïve LOCAL,
ce module introduirait un decalage. A reverifier si la situation change.
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, PlainSerializer


def _ensure_utc(v: datetime) -> datetime:
    """Renvoie un datetime aware UTC (suppose UTC si naïve)."""
    if v.tzinfo is None:
        return v.replace(tzinfo=UTC)
    return v.astimezone(UTC)


def _format_utc_z(v: datetime) -> str:
    """Serialise en ISO 8601 UTC avec suffixe Z (jamais +00:00)."""
    aware = v if v.tzinfo is not None else v.replace(tzinfo=UTC)
    return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[
    datetime,
    AfterValidator(_ensure_utc),
    PlainSerializer(_format_utc_z, return_type=str),
]
