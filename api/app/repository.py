"""Requêtes SQL sur structures_sanitaires, partagées par v1 et v2."""
from .db import fetch_all, fetch_one

V1_COLUMNS = "id, code, nom, type, statut, region, province, commune, telephone"
V2_COLUMNS = (
    V1_COLUMNS
    + ", district, adresse, email, capacite_lits, services, "
    "latitude::float AS latitude, longitude::float AS longitude, date_ouverture"
)


def _where(filters: dict, q: str | None) -> tuple[str, dict]:
    """Construit la clause WHERE à partir des filtres non vides."""
    clauses = ["actif = TRUE"]
    params: dict = {}
    for col in ("region", "type", "statut", "district"):
        val = filters.get(col)
        if val:
            clauses.append(f"LOWER({col}) = LOWER(%({col})s)")
            params[col] = val
    if q:
        clauses.append("(nom ILIKE %(q)s OR code ILIKE %(q)s OR commune ILIKE %(q)s)")
        params["q"] = f"%{q}%"
    return " AND ".join(clauses), params


def list_structures(columns: str, page: int, size: int, filters: dict, q: str | None = None):
    where, params = _where(filters, q)
    total = fetch_one(f"SELECT COUNT(*) AS n FROM structures_sanitaires WHERE {where}", params)["n"]
    params |= {"limit": size, "offset": (page - 1) * size}
    rows = fetch_all(
        f"SELECT {columns} FROM structures_sanitaires WHERE {where} "
        "ORDER BY id LIMIT %(limit)s OFFSET %(offset)s",
        params,
    )
    return total, rows


def get_structure(columns: str, structure_id: int):
    return fetch_one(
        f"SELECT {columns} FROM structures_sanitaires WHERE id = %(id)s AND actif = TRUE",
        {"id": structure_id},
    )
