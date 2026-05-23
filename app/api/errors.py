"""Handlers d'erreurs : conversion des champs interdits en 400 explicite.

La validation stricte (`extra="forbid"`) leve une erreur Pydantic `extra_forbidden`
pour tout champ non declare. On la transforme en HTTP 400 (et non 422) avec un
message explicite — notamment pour materialiser l'anonymisation RGPD des reports.
"""

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Champs identifiants explicitement bannis des reports (message dedie).
_FORBIDDEN_IDENTIFYING_FIELDS = {
    "prenom",
    "prenom_eleve",
    "nom",
    "nom_eleve",
    "nom_enseignant",
    "enseignant",
    "id_session",
    "session_id",
    "code_session",
    "id_connexion",
    "connexion_id",
    "id_classe",
    "classe_id",
    "nom_etablissement",
    "etablissement",
    "eleve_id",
    "student_id",
    "ip",
    "email",
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        for err in exc.errors():
            if err.get("type") == "extra_forbidden":
                loc = err.get("loc") or ()
                field = str(loc[-1]) if loc else "?"
                if field in _FORBIDDEN_IDENTIFYING_FIELDS:
                    detail = (
                        f"Champ interdit (anonymisation RGPD) : '{field}'. Un report ne doit "
                        "contenir aucune donnée identifiante (prénom, nom, identifiants de "
                        "session / classe / connexion, établissement, e-mail, IP)."
                    )
                else:
                    detail = f"Champ non autorisé dans le payload : '{field}'."
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST, content={"detail": detail}
                )

        return JSONResponse(
            status_code=422,  # Unprocessable Content (constante renommee selon la version)
            content={"detail": jsonable_encoder(exc.errors())},
        )
