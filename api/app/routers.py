"""Routes v1 et v2 de l'API Structures sanitaires.

WSO2 expose :
  https://<passerelle>:8243/structures/1.0.0/...  ->  http://api:8000/v1/...
  https://<passerelle>:8243/structures/2.0.0/...  ->  http://api:8000/v2/...
"""
import math
from typing import Annotated

from fastapi import APIRouter, Path, Query

from . import repository as repo
from .errors import ApiError
from .schemas import Error, PageV1, PageV2, Statut, StructureV1, StructureV2, TypeStructure

ERRORS = {
    400: {"model": Error, "description": "Paramètre invalide (VALIDATION_ERROR)"},
    503: {"model": Error, "description": "Base de données indisponible (DATABASE_UNAVAILABLE)"},
}
NOT_FOUND = {404: {"model": Error, "description": "Structure inexistante (STRUCTURE_NOT_FOUND)"}}

Page = Annotated[int, Query(ge=1, description="Numéro de page (commence à 1)")]
Size = Annotated[int, Query(ge=1, le=100, description="Éléments par page (1 à 100)")]
Region = Annotated[str | None, Query(max_length=60, description="Filtre exact sur la région")]
Type_ = Annotated[TypeStructure | None, Query(description="Filtre sur le type")]
Statut_ = Annotated[Statut | None, Query(description="Filtre sur le statut")]
Q = Annotated[str, Query(min_length=2, max_length=100, description="Texte cherché dans le nom, le code ou la commune")]
Id = Annotated[int, Path(ge=1, description="Identifiant de la structure")]


def _page(page, size, total, rows):
    return {"page": page, "size": size, "total": total,
            "totalPages": math.ceil(total / size) if total else 0, "items": rows}


def _get_or_404(columns, structure_id):
    row = repo.get_structure(columns, structure_id)
    if row is None:
        raise ApiError(404, "STRUCTURE_NOT_FOUND",
                       f"Aucune structure active avec l'identifiant {structure_id}")
    return row


def _f(**kw):
    return {k: (v.value if hasattr(v, "value") else v) for k, v in kw.items()}


# ----------------------------------------------------------------- v1
v1 = APIRouter(prefix="/v1", tags=["v1"], responses=ERRORS)


@v1.get("/structures", response_model=PageV1, summary="Lister les structures (paginé)")
def list_v1(page: Page = 1, size: Size = 10, region: Region = None,
            type: Type_ = None, statut: Statut_ = None):
    total, rows = repo.list_structures(repo.V1_COLUMNS, page, size,
                                       _f(region=region, type=type, statut=statut))
    return _page(page, size, total, rows)


@v1.get("/structures/search", response_model=PageV1, summary="Rechercher des structures")
def search_v1(q: Q, page: Page = 1, size: Size = 10, region: Region = None, type: Type_ = None):
    total, rows = repo.list_structures(repo.V1_COLUMNS, page, size,
                                       _f(region=region, type=type), q)
    return _page(page, size, total, rows)


@v1.get("/structures/{id}", response_model=StructureV1, responses=NOT_FOUND,
        summary="Détail d'une structure")
def get_v1(id: Id):
    return _get_or_404(repo.V1_COLUMNS, id)


# ----------------------------------------------------------------- v2
# Évolution compatible : mêmes routes, champs en plus, filtre district en plus.
v2 = APIRouter(prefix="/v2", tags=["v2"], responses=ERRORS)
District = Annotated[str | None, Query(max_length=80, description="Filtre exact sur le district (v2)")]


@v2.get("/structures", response_model=PageV2, summary="Lister les structures (paginé)")
def list_v2(page: Page = 1, size: Size = 10, region: Region = None, type: Type_ = None,
            statut: Statut_ = None, district: District = None):
    total, rows = repo.list_structures(repo.V2_COLUMNS, page, size,
                                       _f(region=region, type=type, statut=statut, district=district))
    return _page(page, size, total, rows)


@v2.get("/structures/search", response_model=PageV2, summary="Rechercher des structures")
def search_v2(q: Q, page: Page = 1, size: Size = 10, region: Region = None,
              type: Type_ = None, district: District = None):
    total, rows = repo.list_structures(repo.V2_COLUMNS, page, size,
                                       _f(region=region, type=type, district=district), q)
    return _page(page, size, total, rows)


@v2.get("/structures/{id}", response_model=StructureV2, responses=NOT_FOUND,
        summary="Détail d'une structure")
def get_v2(id: Id):
    return _get_or_404(repo.V2_COLUMNS, id)
