"""Tests du backend (sans WSO2). Nécessite la base chargée avec db/init.sql + db/seed.sql.

Lancer :  cd api && pytest -v
"""
import os

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------- santé
def test_health_up():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "UP", "database": "UP"}


# ---------------------------------------------------------------- v1
def test_liste_paginee():
    r = client.get("/v1/structures", params={"page": 1, "size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1 and body["size"] == 10
    assert len(body["items"]) == 10
    assert body["total"] >= 70
    assert body["totalPages"] == -(-body["total"] // 10)


def test_pages_sans_chevauchement():
    p1 = {s["id"] for s in client.get("/v1/structures?page=1&size=5").json()["items"]}
    p2 = {s["id"] for s in client.get("/v1/structures?page=2&size=5").json()["items"]}
    assert p1.isdisjoint(p2)


def test_page_au_dela_de_la_fin():
    r = client.get("/v1/structures", params={"page": 999, "size": 10})
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_v1_ne_contient_pas_les_champs_v2():
    item = client.get("/v1/structures?size=1").json()["items"][0]
    assert "capacite_lits" not in item and "services" not in item and "district" not in item


def test_filtre_type_et_region():
    r = client.get("/v1/structures", params={"type": "CHU", "size": 50})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items and all(s["type"] == "CHU" for s in items)
    r = client.get("/v1/structures", params={"region": "centre", "size": 100})
    assert all(s["region"] == "Centre" for s in r.json()["items"])


def test_detail():
    r = client.get("/v1/structures/1")
    assert r.status_code == 200
    assert r.json()["id"] == 1 and r.json()["code"] == "CSPS-0001"


def test_detail_inexistant_404():
    r = client.get("/v1/structures/9999")
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "STRUCTURE_NOT_FOUND"
    assert set(body) == {"code", "message", "details", "path", "timestamp"}


def test_recherche():
    r = client.get("/v1/structures/search", params={"q": "ouaga"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items and all("ouaga" in (s["nom"] + s["commune"]).lower() for s in items)


@pytest.mark.parametrize("url", [
    "/v1/structures?page=0",
    "/v1/structures?page=-1",
    "/v1/structures?size=abc",
    "/v1/structures?size=500",
    "/v1/structures?type=HOPITAL",
    "/v1/structures/search",          # q manquant
    "/v1/structures/search?q=a",      # q trop court
    "/v1/structures/abc",
    "/v1/structures/0",
])
def test_parametres_invalides_400(url):
    r = client.get(url)
    assert r.status_code == 400, url
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"] and "issue" in body["details"][0]


def test_route_inconnue_404():
    r = client.get("/v1/inconnu")
    assert r.status_code == 404
    assert r.json()["code"] == "RESOURCE_NOT_FOUND"


def test_structure_inactive_invisible():
    """Une structure actif = FALSE n'est ni listée ni consultable."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM structures_sanitaires WHERE actif = FALSE LIMIT 1")
        row = cur.fetchone()
    if row is None:
        pytest.skip("aucune structure inactive dans le jeu de données")
    assert client.get(f"/v1/structures/{row['id']}").status_code == 404


# ---------------------------------------------------------------- v2
def test_v2_champs_supplementaires():
    r = client.get("/v2/structures/1")
    assert r.status_code == 200
    s = r.json()
    for champ in ("district", "capacite_lits", "services", "latitude", "longitude"):
        assert champ in s
    assert isinstance(s["services"], list)


def test_v2_filtre_district():
    r = client.get("/v2/structures", params={"district": "District de Bogodogo", "size": 100})
    assert r.status_code == 200
    assert all(s["district"] == "District de Bogodogo" for s in r.json()["items"])


def test_v1_v2_memes_identifiants():
    """Compatibilité : v2 renvoie les mêmes structures que v1, avec plus de champs."""
    a = client.get("/v1/structures?page=2&size=5").json()["items"]
    b = client.get("/v2/structures?page=2&size=5").json()["items"]
    assert [x["id"] for x in a] == [x["id"] for x in b]
    for x, y in zip(a, b):
        assert all(y[k] == v for k, v in x.items())


# ---------------------------------------------------------------- panne base
def test_base_indisponible_503(monkeypatch):
    monkeypatch.setattr(db, "DATABASE_URL", "postgresql://x:x@127.0.0.1:1/none")
    r = client.get("/v1/structures")
    assert r.status_code == 503
    assert r.json()["code"] == "DATABASE_UNAVAILABLE"
    h = client.get("/health")
    assert h.status_code == 503 and h.json()["database"] == "DOWN"
