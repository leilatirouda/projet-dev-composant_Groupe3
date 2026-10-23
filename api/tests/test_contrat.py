"""Vérifie que le backend respecte les contrats openapi/v1.yaml et openapi/v2.yaml."""
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
OPENAPI = Path(__file__).resolve().parents[2] / "openapi"
TYPES = {"integer": int, "string": str, "number": (int, float), "array": list, "boolean": bool}


def _spec(version):
    return yaml.safe_load((OPENAPI / f"{version}.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_structure_conforme(version):
    spec = _spec(version)
    schema = spec["components"]["schemas"]["Structure"]
    enums = spec["components"]["schemas"]
    item = client.get(f"/{version}/structures/1").json()

    assert set(item) == set(schema["properties"]), "champs différents du contrat"
    for champ in schema["required"]:
        assert item[champ] is not None, champ
    for champ, prop in schema["properties"].items():
        val = item[champ]
        if val is None:
            assert prop.get("nullable"), f"{champ} est null mais non nullable"
        elif "$ref" in prop:
            assert val in enums[prop["$ref"].split("/")[-1]]["enum"]
        else:
            assert isinstance(val, TYPES[prop["type"]]), champ


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_page_conforme(version):
    spec = _spec(version)
    body = client.get(f"/{version}/structures?size=3").json()
    assert set(body) == set(spec["components"]["schemas"]["PageStructures"]["properties"])


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_routes_du_contrat_existent(version):
    for path in _spec(version)["paths"]:
        url = f"/{version}" + path.replace("{id}", "1")
        if path.endswith("search"):
            url += "?q=csps"
        assert client.get(url).status_code == 200, url
