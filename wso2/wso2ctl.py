"""Pilotage de WSO2 API Manager 4.6.0 par ses API REST officielles.

Rend la configuration reproductible : tout ce qui se fait à la main dans le
Publisher, le Developer Portal et l'Admin Portal est fait ici par script.

Usage (depuis la racine du dépôt, WSO2 démarré) :
    python wso2/wso2ctl.py setup          # plan + API v1 + publication + applications + souscription
    python wso2/wso2ctl.py status         # état du cycle de vie des versions
    python wso2/wso2ctl.py token          # nouveau jeton pour l'application abonnée
    python wso2/wso2ctl.py block          # retrait temporaire de publication (BLOCKED)
    python wso2/wso2ctl.py republish      # BLOCKED -> PUBLISHED
    python wso2/wso2ctl.py new-version    # crée, configure et publie la v2, déprécie la v1
    python wso2/wso2ctl.py block-sub      # bloque la souscription de l'application
    python wso2/wso2ctl.py unblock-sub    # la débloque
    python wso2/wso2ctl.py retire-v1      # fin de vie de la v1 (DEPRECATED -> RETIRED)

APIs utilisées : publisher/v4, devportal/v3, admin/v4, client-registration/v0.17
(spécifications : github.com/wso2/carbon-apimgt, components/apimgt/*/src/main/resources).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # certificat auto-signé de WSO2

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "wso2" / ".state.json"
POSTMAN_ENV = ROOT / "tests" / "postman_environment.local.json"

HOST = os.getenv("WSO2_HOST", "https://localhost:9443")
GATEWAY = os.getenv("WSO2_GATEWAY", "https://localhost:8243")
ADMIN_USER = os.getenv("WSO2_USER", "admin")
ADMIN_PASS = os.getenv("WSO2_PASSWORD", "admin")
BACKEND = os.getenv("BACKEND_URL", "http://api:8000")   # vu depuis le conteneur WSO2

PUB = f"{HOST}/api/am/publisher/v4"
DEV = f"{HOST}/api/am/devportal/v3"
ADM = f"{HOST}/api/am/admin/v4"

API_NAME = "StructuresSanitaires"
CONTEXT = "/structures"
PLAN = "Plan10ParMinute"
APP = "AppPortailSante"
APP_NO_SUB = "AppNonAbonnee"
SCOPES = " ".join([
    "apim:api_view", "apim:api_create", "apim:api_manage", "apim:api_publish", "apim:api_deploy",
    "apim:api_version_create", "apim:subscribe", "apim:app_manage", "apim:sub_manage",
    "apim:subscription_view", "apim:subscription_block", "apim:subscription_manage",
    "apim:admin", "apim:tier_view", "apim:tier_manage", "apim:admin_tier_view", "apim:admin_tier_manage",
])


# ------------------------------------------------------------------ outils
def log(msg):
    print(f"  -> {msg}", flush=True)


def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def check(resp, *ok):
    if resp.status_code not in (ok or (200, 201)):
        print(f"\nERREUR {resp.request.method} {resp.url}\n  HTTP {resp.status_code} : {resp.text[:800]}")
        sys.exit(1)
    return resp.json() if resp.content and "json" in resp.headers.get("content-type", "") else {}


def wait_for_wso2(timeout=420):
    print(f"Attente de WSO2 sur {HOST} ...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{HOST}/services/Version", verify=False, timeout=5)
            if r.status_code < 500:
                # le serveur répond ; on vérifie que la REST API est prête aussi
                r = requests.get(f"{PUB}/apis", verify=False, timeout=5)
                if r.status_code in (200, 401):
                    log("WSO2 est prêt")
                    return
        except requests.RequestException:
            pass
        time.sleep(10)
    sys.exit("WSO2 ne répond pas. Vérifier : docker compose logs wso2am")


def admin_session():
    """Enregistre un client REST (DCR) puis obtient un jeton administrateur."""
    r = requests.post(
        f"{HOST}/client-registration/v0.17/register",
        auth=(ADMIN_USER, ADMIN_PASS), verify=False, timeout=30,
        json={"callbackUrl": "https://localhost", "clientName": "groupe3_wso2ctl", "owner": ADMIN_USER,
              "grantType": "client_credentials password refresh_token", "saasApp": True},
    )
    reg = check(r)
    r = requests.post(
        f"{HOST}/oauth2/token", auth=(reg["clientId"], reg["clientSecret"]), verify=False, timeout=30,
        data={"grant_type": "password", "username": ADMIN_USER, "password": ADMIN_PASS, "scope": SCOPES},
    )
    tok = check(r)["access_token"]
    s = requests.Session()
    s.verify = False
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


def find_api(s, version):
    r = s.get(f"{PUB}/apis", params={"query": f"name:{API_NAME} version:{version}"})
    for api in check(r).get("list", []):
        if api["name"] == API_NAME and api["version"] == version:
            return api
    return None


def lifecycle(s, api_id, action, checklist=None):
    params = {"apiId": api_id, "action": action}
    if checklist:
        params["lifecycleChecklist"] = checklist
    check(s.post(f"{PUB}/apis/change-lifecycle", params=params))
    state = check(s.get(f"{PUB}/apis/{api_id}"))["lifeCycleStatus"]
    log(f"{action} -> état {state}")
    return state


def deploy_revision(s, api_id, label):
    rev = check(s.post(f"{PUB}/apis/{api_id}/revisions", json={"description": label}))
    check(s.post(f"{PUB}/apis/{api_id}/deploy-revision", params={"revisionId": rev["id"]},
                 json=[{"name": "Default", "vhost": "localhost", "displayOnDevportal": True}]))
    log(f"révision {rev.get('displayName', rev['id'])} déployée sur la passerelle Default")


def endpoint(version_path):
    url = f"{BACKEND}/{version_path}"
    return {"endpoint_type": "http", "production_endpoints": {"url": url}, "sandbox_endpoints": {"url": url}}


def get_app(s, name):
    r = s.get(f"{DEV}/applications", params={"query": name})
    for app in check(r).get("list", []):
        if app["name"] == name:
            return app
    return None


def ensure_app(s, name, description):
    app = get_app(s, name)
    if app:
        log(f"application {name} déjà présente")
    else:
        app = check(s.post(f"{DEV}/applications", json={
            "name": name, "throttlingPolicy": "Unlimited", "description": description, "tokenType": "JWT"}))
        log(f"application {name} créée")
    app_id = app["applicationId"]
    r = s.post(f"{DEV}/applications/{app_id}/generate-keys", json={
        "keyType": "PRODUCTION", "keyManager": "Resident Key Manager",
        "grantTypesToBeSupported": ["client_credentials"], "callbackUrl": "", "validityTime": 3600})
    if r.status_code == 409:           # clés déjà générées : on les relit
        keys = [k for k in check(s.get(f"{DEV}/applications/{app_id}/keys")).get("list", [])
                if k["keyType"] == "PRODUCTION"][0]
    else:
        keys = check(r)
    return {"id": app_id, "consumerKey": keys["consumerKey"], "consumerSecret": keys["consumerSecret"]}


def app_token(app):
    r = requests.post(f"{HOST}/oauth2/token", auth=(app["consumerKey"], app["consumerSecret"]),
                      data={"grant_type": "client_credentials"}, verify=False, timeout=30)
    return check(r)["access_token"]


def subscribe(s, app_id, api_id):
    existing = check(s.get(f"{DEV}/subscriptions", params={"applicationId": app_id})).get("list", [])
    for sub in existing:
        if sub["apiId"] == api_id:
            log("souscription déjà présente")
            return sub["subscriptionId"]
    for _ in range(12):   # le Developer Portal indexe l'API quelques secondes après la publication
        r = s.post(f"{DEV}/subscriptions",
                   json={"applicationId": app_id, "apiId": api_id, "throttlingPolicy": PLAN})
        if r.status_code in (200, 201):
            log(f"souscription créée avec le plan {PLAN}")
            return r.json()["subscriptionId"]
        time.sleep(5)
    check(r)


def write_postman_env(state):
    values = {
        "gateway": GATEWAY, "host": HOST, "backend": "http://localhost:8000",
        "consumerKey": state["app"]["consumerKey"], "consumerSecret": state["app"]["consumerSecret"],
        "consumerKeyNoSub": state["app_no_sub"]["consumerKey"],
        "consumerSecretNoSub": state["app_no_sub"]["consumerSecret"],
        "token": "", "tokenNoSub": "",
    }
    POSTMAN_ENV.parent.mkdir(exist_ok=True)
    POSTMAN_ENV.write_text(json.dumps({
        "name": "Groupe3 WSO2 (local)",
        "values": [{"key": k, "value": v, "enabled": True} for k, v in values.items()],
    }, indent=2))
    log(f"environnement Postman écrit : {POSTMAN_ENV.relative_to(ROOT)}")


# ------------------------------------------------------------------ commandes
def cmd_setup(s, state):
    print("1. Plan d'accès (Business Plan) avec quota")
    pols = check(s.get(f"{ADM}/throttling/policies/subscription")).get("list", [])
    if any(p["policyName"] == PLAN for p in pols):
        log(f"plan {PLAN} déjà présent")
    else:
        check(s.post(f"{ADM}/throttling/policies/subscription", json={
            "policyName": PLAN, "displayName": "Plan 10 requêtes/minute",
            "description": "Plan étudiant : 10 requêtes par minute, requêtes rejetées au-delà (HTTP 429)",
            "defaultLimit": {"type": "REQUESTCOUNTLIMIT",
                             "requestCount": {"timeUnit": "min", "unitTime": 1, "requestCount": 10}},
            "rateLimitCount": 0, "rateLimitTimeUnit": "sec",
            "stopOnQuotaReach": True, "billingPlan": "FREE", "customAttributes": []}))
        log(f"plan {PLAN} créé (10 requêtes/min)")

    print("2. Création de l'API v1 depuis openapi/v1.yaml")
    api = find_api(s, "1.0.0")
    if api:
        log("API 1.0.0 déjà présente")
        api_id = api["id"]
    else:
        props = {"name": API_NAME, "version": "1.0.0", "context": CONTEXT,
                 "description": "Consultation des structures sanitaires (Groupe 3 SI)",
                 "policies": [PLAN, "Unlimited"], "endpointConfig": endpoint("v1"),
                 "transport": ["http", "https"], "tags": ["sante", "groupe3"]}
        with open(ROOT / "openapi" / "v1.yaml", "rb") as f:
            r = s.post(f"{PUB}/apis/import-openapi",
                       files={"file": ("v1.yaml", f, "application/x-yaml")},
                       data={"additionalProperties": json.dumps(props)})
        api_id = check(r)["id"]
        log(f"API créée (état CREATED), id={api_id}")
        print("3. Déploiement sur la passerelle et publication")
        deploy_revision(s, api_id, "v1 initiale")
        lifecycle(s, api_id, "Publish")
    state["v1"] = api_id

    print("4. Applications consommatrices et souscription")
    state["app"] = ensure_app(s, APP, "Application abonnée (tests T1 à T12)")
    state["app_no_sub"] = ensure_app(s, APP_NO_SUB, "Application SANS souscription (test 403)")
    state["sub_v1"] = subscribe(s, state["app"]["id"], api_id)
    save_state(state)
    write_postman_env(state)

    print("5. Vérification de bout en bout via la passerelle")
    tok = app_token(state["app"])
    for _ in range(12):
        r = requests.get(f"{GATEWAY}{CONTEXT}/1.0.0/structures", params={"size": 2},
                         headers={"Authorization": f"Bearer {tok}"}, verify=False, timeout=30)
        if r.status_code == 200:
            break
        time.sleep(5)
    log(f"GET {CONTEXT}/1.0.0/structures -> HTTP {r.status_code}")
    print(r.text[:300])


def cmd_status(s, state):
    for v in ("1.0.0", "2.0.0"):
        api = find_api(s, v)
        print(f"  {API_NAME} {v} : {api['lifeCycleStatus'] if api else 'absente'}")


def cmd_new_version(s, state):
    v1 = state["v1"]
    v2 = find_api(s, "2.0.0")
    if v2:
        sys.exit("La version 2.0.0 existe déjà.")
    print("1. Copie de la v1 en 2.0.0")
    api = check(s.post(f"{PUB}/apis/copy-api", params={"apiId": v1, "newVersion": "2.0.0",
                                                         "defaultVersion": "false"}))
    v2_id = api["id"]
    print("2. Contrat v2 et routage vers /v2 du backend")
    with open(ROOT / "openapi" / "v2.yaml", encoding="utf-8") as f:
        check(s.put(f"{PUB}/apis/{v2_id}/swagger", files={"apiDefinition": (None, f.read())}))
    full = check(s.get(f"{PUB}/apis/{v2_id}"))
    full["endpointConfig"] = endpoint("v2")
    full["description"] = "v2 : district, capacité en lits, services, coordonnées"
    check(s.put(f"{PUB}/apis/{v2_id}", json=full))
    log("endpoint v2 configuré")
    print("3. Déploiement, publication de la v2 et dépréciation automatique de la v1")
    deploy_revision(s, v2_id, "v2 initiale")
    lifecycle(s, v2_id, "Publish", "Deprecate old versions after publishing the API:true")
    state["v2"] = v2_id
    state["sub_v2"] = subscribe(s, state["app"]["id"], v2_id)
    save_state(state)
    cmd_status(s, state)


def cmd_token(s, state):
    print(app_token(state["app"]))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("commande", choices=["setup", "status", "token", "block", "republish", "new-version",
                                        "block-sub", "unblock-sub", "retire-v1"])
    cmd = p.parse_args().commande
    state = load_state()
    if cmd != "setup" and "v1" not in state:
        sys.exit("Lancer d'abord : python wso2/wso2ctl.py setup")
    if cmd == "setup":
        wait_for_wso2()
    s = admin_session()
    if cmd == "setup":
        cmd_setup(s, state)
    elif cmd == "status":
        cmd_status(s, state)
    elif cmd == "token":
        cmd_token(s, state)
    elif cmd == "block":
        lifecycle(s, state["v1"], "Block")
        print("  L'API reste visible ; la passerelle répond 503 / code 700700. Le backend tourne toujours.")
    elif cmd == "republish":
        lifecycle(s, state["v1"], "Re-Publish")
    elif cmd == "new-version":
        cmd_new_version(s, state)
    elif cmd == "block-sub":
        check(s.post(f"{PUB}/subscriptions/block-subscription",
                     params={"subscriptionId": state["sub_v1"], "blockState": "BLOCKED"}))
        log("souscription bloquée : la passerelle répond 401 / code 900907")
    elif cmd == "unblock-sub":
        check(s.post(f"{PUB}/subscriptions/unblock-subscription", params={"subscriptionId": state["sub_v1"]}))
        log("souscription débloquée")
    elif cmd == "retire-v1":
        lifecycle(s, state["v1"], "Retire")


if __name__ == "__main__":
    main()
