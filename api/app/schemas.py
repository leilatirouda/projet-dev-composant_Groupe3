"""Modèles de réponse (contrat exposé, repris dans openapi/v1.yaml et v2.yaml)."""
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class TypeStructure(str, Enum):
    CHU = "CHU"
    CHR = "CHR"
    CMA = "CMA"
    CM = "CM"
    CSPS = "CSPS"
    CLINIQUE = "CLINIQUE"
    DISPENSAIRE = "DISPENSAIRE"
    MATERNITE = "MATERNITE"


class Statut(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVE = "PRIVE"
    CONFESSIONNEL = "CONFESSIONNEL"
    COMMUNAUTAIRE = "COMMUNAUTAIRE"


class StructureV1(BaseModel):
    id: int
    code: str = Field(examples=["CSPS-0001"])
    nom: str
    type: TypeStructure
    statut: Statut
    region: str
    province: str
    commune: str
    telephone: str | None = None


class StructureV2(StructureV1):
    district: str
    adresse: str | None = None
    email: str | None = None
    capacite_lits: int
    services: list[str]
    latitude: float | None = None
    longitude: float | None = None
    date_ouverture: date | None = None


class PageV1(BaseModel):
    page: int
    size: int
    total: int
    totalPages: int
    items: list[StructureV1]


class PageV2(BaseModel):
    page: int
    size: int
    total: int
    totalPages: int
    items: list[StructureV2]


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class Error(BaseModel):
    code: str = Field(examples=["STRUCTURE_NOT_FOUND"])
    message: str
    details: list[ErrorDetail] = []
    path: str
    timestamp: str
