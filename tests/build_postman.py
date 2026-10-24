"""Génère tests/postman_collection.json (format Postman v2.1).

La collection est générée pour rester lisible et cohérente avec tests/resultats-attendus.md.
Usage : python tests/build_postman.py
"""
import json
from pathlib import Path

GW1 = "{{gateway}}/structures/1.0.0"
GW2 = "{{gateway}}/structures/2.0.0"


def js(*lines):
    return [l for l in lines]


def req(name, url, tests, auth="token", method="GET", body=None, prerequest=None, headers=None):
    hdr = list(headers or [])
    if auth == "token":
        hdr.append({"key": "Authorization", "value": "Bearer {{token}}"})
    elif auth == "nosub":
        hdr.append({"key": "Authorization", "value": "Bearer {{tokenNoSub}}"})
    elif auth == "invalid":
        hdr.append({"key": "Authorization", "value": "Bearer jeton-invalide-0000"})
    item = {
        "name": name,
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": tests}}],
        "request": {"method": method, "header": hdr, "url": url},
    }
    if prerequest:
        item["event"].append({"listen": "prerequest", "script": {"type": "text/javascript", "exec": prerequest}})
    if body:
        item["request"]["body"] = body
    return item


def status(code, label=None):
    return f'pm.test("HTTP {code}{(" - " + label) if label else ""}", () => pm.response.to.have.status({code}));'


def contains(code):
    return f'pm.test("Code {code} dans la réponse", () => pm.expect(pm.response.text()).to.include("{code}"));'


def token_req(name, key, secret, var):
    return {
        "name": name,
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": [
            status(200),
            f'pm.environment.set("{var}", pm.response.json().access_token);',
        ]}}],
        "request": {
            "method": "POST",
            "auth": {"type": "basic", "basic": [
                {"key": "username", "value": "{{" + key + "}}"},
                {"key": "password", "value": "{{" + secret + "}}"}]},
            "header": [],
            "body": {"mode": "urlencoded", "urlencoded": [{"key": "grant_type", "value": "client_credentials"}]},
            "url": "{{host}}/oauth2/token",
        },
    }


collection = {
    "info": {
        "name": "Groupe 3 SI - API Structures via WSO2",
        "description": "Scénarios T1 à T12 (voir tests/resultats-attendus.md). "
                       "Environnement : tests/postman_environment.local.json généré par wso2/wso2ctl.py setup.",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "item": [
        {"name": "0 - Jetons", "item": [
            token_req("Jeton application abonnée", "consumerKey", "consumerSecret", "token"),
            token_req("Jeton application NON abonnée", "consumerKeyNoSub", "consumerSecretNoSub", "tokenNoSub"),
        ]},
        {"name": "1 - Fonctionnel (T1-T4)", "item": [
            req("T1 - Liste paginée (bout en bout)", GW1 + "/structures?page=1&size=10", js(
                status(200),
                'const b = pm.response.json();',
                'pm.test("10 éléments", () => pm.expect(b.items).to.have.lengthOf(10));',
                'pm.test("Pagination cohérente", () => pm.expect(b.totalPages).to.eql(Math.ceil(b.total / b.size)));',
                'pm.test("Pas de champ v2 en v1", () => pm.expect(b.items[0]).to.not.have.property("capacite_lits"));',
            )),
            req("T1b - Filtre type=CHU", GW1 + "/structures?type=CHU", js(
                status(200),
                'pm.test("Uniquement des CHU", () => pm.response.json().items.forEach(s => pm.expect(s.type).to.eql("CHU")));',
            )),
            req("T1c - Recherche q=ouaga", GW1 + "/structures/search?q=ouaga", js(
                status(200),
                'pm.test("Résultats contenant ouaga", () => pm.response.json().items.forEach(s =>'
                ' pm.expect((s.nom + s.commune).toLowerCase()).to.include("ouaga")));',
            )),
            req("T2 - Détail id=5", GW1 + "/structures/5", js(
                status(200),
                'pm.test("Bonne structure", () => pm.expect(pm.response.json().id).to.eql(5));',
            )),
            req("T3 - Structure inexistante", GW1 + "/structures/9999", js(
                status(404), contains("STRUCTURE_NOT_FOUND"),
                'pm.test("Format d\'erreur du contrat", () => pm.expect(pm.response.json()).to.have.all.keys('
                '"code","message","details","path","timestamp"));',
            )),
            req("T4a - page=-1", GW1 + "/structures?page=-1", js(status(400), contains("VALIDATION_ERROR"))),
            req("T4b - size=abc", GW1 + "/structures?size=abc", js(status(400), contains("VALIDATION_ERROR"))),
            req("T4c - type inconnu", GW1 + "/structures?type=HOPITAL", js(status(400), contains("VALIDATION_ERROR"))),
        ]},
        {"name": "2 - Sécurité (T5-T7)", "item": [
            req("T5 - Jeton absent", GW1 + "/structures", js(status(401), contains("900902")), auth=None),
            req("T6 - Jeton invalide", GW1 + "/structures", js(status(401), contains("900901")), auth="invalid"),
            req("T7 - Application non abonnée", GW1 + "/structures", js(status(403), contains("900908")), auth="nosub"),
        ]},
        {"name": "3 - Quota (T8) - lancer seul", "item": [
            req("T8 - Dépassement du plan 10/min", GW1 + "/structures?size=1", js(
                'const n = (pm.collectionVariables.get("t8_count") || 0) + 1;',
                'pm.collectionVariables.set("t8_count", n);',
                'if (pm.response.code === 200 && n < 25) {',
                '  postman.setNextRequest("T8 - Dépassement du plan 10/min");',
                '} else {',
                '  pm.collectionVariables.set("t8_count", 0);',
                '  console.log("Appels avant rejet : " + n);',
                f'  {status(429, "quota dépassé")}',
                f'  {contains("900804")}',
                '}',
            )),
        ]},
        {"name": "4 - Cycle de vie (après chaque commande wso2ctl)", "item": [
            req("T9 - API bloquée  [après: wso2ctl block]", GW1 + "/structures", js(
                status(503, "API BLOCKED"), contains("700700"))),
            req("T10 - Arrêt technique  [après: docker compose stop api]", GW1 + "/structures", js(
                'pm.test("Erreur 5xx de la passerelle", () => pm.expect(pm.response.code).to.be.within(500, 599));',
                contains("101503"))),
            req("T7b - Souscription bloquée  [après: wso2ctl block-sub]", GW1 + "/structures", js(
                status(401), contains("900907"))),
            req("T11a - v2 avec nouveaux champs  [après: wso2ctl new-version]", GW2 + "/structures/1", js(
                status(200),
                'const s = pm.response.json();',
                'pm.test("Champs v2 présents", () => pm.expect(s).to.include.keys("district","capacite_lits","services"));',
            )),
            req("T11b - v2 filtre district", GW2 + "/structures?district=District de Bogodogo", js(
                status(200),
                'pm.test("Filtre district", () => pm.response.json().items.forEach(s =>'
                ' pm.expect(s.district).to.eql("District de Bogodogo")));',
            )),
            req("T11c - v1 dépréciée répond toujours", GW1 + "/structures/1", js(status(200))),
            req("T12 - Republication  [après: wso2ctl republish]", GW1 + "/structures", js(status(200))),
        ]},
        {"name": "5 - Backend direct (supervision)", "item": [
            req("Santé du backend", "{{backend}}/health", js(
                status(200), 'pm.test("Base UP", () => pm.expect(pm.response.json().database).to.eql("UP"));'),
                auth=None),
        ]},
    ],
    "variable": [{"key": "t8_count", "value": 0}],
}

out = Path(__file__).with_name("postman_collection.json")
out.write_text(json.dumps(collection, indent=2, ensure_ascii=False), encoding="utf-8")

env = {"name": "Groupe3 WSO2 (modèle)", "values": [
    {"key": k, "value": v, "enabled": True} for k, v in {
        "gateway": "https://localhost:8243", "host": "https://localhost:9443", "backend": "http://localhost:8000",
        "consumerKey": "", "consumerSecret": "", "consumerKeyNoSub": "", "consumerSecretNoSub": "",
        "token": "", "tokenNoSub": ""}.items()]}
Path(__file__).with_name("postman_environment.example.json").write_text(json.dumps(env, indent=2))
print("Collection et environnement modèle écrits.")
