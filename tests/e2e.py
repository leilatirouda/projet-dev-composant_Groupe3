"""Test de bout en bout de la chaîne principale : client -> WSO2 -> FastAPI -> PostgreSQL.

Enchaîne tous les scénarios T1 à T12, y compris les changements d'état
(blocage, souscription bloquée, arrêt du backend, nouvelle version),
puis écrit le rapport tests/resultats-obtenus.md.

Prérequis : docker compose up -d --build  puis  python wso2/wso2ctl.py setup
Usage     : python tests/e2e.py            (ajouter --skip-v2 si la v2 existe déjà)
"""
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parents[1]
STATE = json.loads((ROOT / "wso2" / ".state.json").read_text())
GW = "https://localhost:8243/structures"
HOST = "https://localhost:9443"
results = []


def token(app):
    r = requests.post(f"{HOST}/oauth2/token", auth=(app["consumerKey"], app["consumerSecret"]),
                      data={"grant_type": "client_credentials"}, verify=False, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


TOK = token(STATE["app"])
TOK_NOSUB = token(STATE["app_no_sub"])


def call(path, tok=TOK, version="1.0.0"):
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    return requests.get(f"{GW}/{version}{path}", headers=headers, verify=False, timeout=30)


def check(num, label, resp, status, contains=None, extra=None):
    ok = resp.status_code == status if isinstance(status, int) else resp.status_code in status
    if contains:
        ok = ok and contains in resp.text
    if extra:
        ok = ok and extra(resp)
    results.append((num, label, f"{status}" + (f" + {contains}" if contains else ""),
                    f"{resp.status_code} {resp.text[:90].strip()}", ok))
    print(f"{'OK ' if ok else 'KO '} {num:4} {label:45} -> HTTP {resp.status_code}")
    return ok


def retry(fn, cond, attempts=12, wait=5):
    """Les changements d'état WSO2 mettent quelques secondes à atteindre la passerelle."""
    for _ in range(attempts):
        r = fn()
        if cond(r):
            return r
        time.sleep(wait)
    return r


def ctl(cmd):
    subprocess.run([sys.executable, str(ROOT / "wso2" / "wso2ctl.py"), cmd], check=True)


def compose(*args):
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)


# ---------------------------------------------------------------- scénarios
print("\n== Fonctionnel")
check("T1", "Liste paginée", call("/structures?page=1&size=10"), 200,
      extra=lambda r: len(r.json()["items"]) == 10)
check("T2", "Détail id=5", call("/structures/5"), 200, extra=lambda r: r.json()["id"] == 5)
check("T3", "Structure inexistante", call("/structures/9999"), 404, "STRUCTURE_NOT_FOUND")
check("T4", "Paramètre invalide page=-1", call("/structures?page=-1"), 400, "VALIDATION_ERROR")

print("\n== Sécurité")
check("T5", "Jeton absent", call("/structures", tok=None), 401, "900902")
check("T6", "Jeton invalide", call("/structures", tok="faux-jeton"), 401, "900901")
check("T7", "Application non abonnée", call("/structures", tok=TOK_NOSUB), 403, "900908")

print("\n== Souscription bloquée")
ctl("block-sub")
check("T7b", "Souscription bloquée", retry(lambda: call("/structures"), lambda r: r.status_code == 401),
      401, "900907")
ctl("unblock-sub")
retry(lambda: call("/structures"), lambda r: r.status_code == 200)

print("\n== Retrait de publication vs arrêt technique")
ctl("block")
r = retry(lambda: call("/structures"), lambda r: r.status_code == 503)
check("T9", "API bloquée (retrait de publication)", r, 503, "700700")
health = requests.get("http://localhost:8000/health", timeout=10)
check("T9b", "Backend toujours en marche pendant le blocage", health, 200)
ctl("republish")
check("T12", "Republication", retry(lambda: call("/structures"), lambda r: r.status_code == 200), 200)

compose("stop", "api")
r = retry(lambda: call("/structures"), lambda r: r.status_code >= 500)
check("T10", "Arrêt technique (backend coupé)", r, (502, 503, 504), "101503")
compose("start", "api")
time.sleep(8)
check("T10b", "Retour à la normale après redémarrage",
      retry(lambda: call("/structures"), lambda r: r.status_code == 200), 200)

if "--skip-v2" not in sys.argv:
    print("\n== Nouvelle version")
    ctl("new-version")
r = retry(lambda: call("/structures/1", version="2.0.0"), lambda r: r.status_code == 200)
check("T11", "v2 avec champs supplémentaires", r, 200, extra=lambda r: "capacite_lits" in r.json())
check("T11b", "v1 dépréciée répond toujours", call("/structures/1"), 200)

print("\n== Quota (en dernier : il consomme le plan pour une minute)")
r = None
for n in range(1, 26):
    r = call("/structures?size=1", version="2.0.0")
    if r.status_code == 429:
        break
check("T8", f"Dépassement du quota (rejet au {n}e appel)", r, 429, "900800")

# ---------------------------------------------------------------- rapport
ok = sum(1 for *_, s in results if s)
lines = [
    "# Résultats obtenus (générés par tests/e2e.py)", "",
    f"Exécution du {datetime.now():%d/%m/%Y à %H:%M} : **{ok}/{len(results)} scénarios réussis**.", "",
    "| N° | Scénario | Attendu | Obtenu | Résultat |", "| --- | --- | --- | --- | --- |",
]
for num, label, exp, got, s in results:
    got = got.replace("|", "\\|").replace("\n", " ")
    lines.append(f"| {num} | {label} | {exp} | `{got}` | {'OK' if s else 'ÉCHEC'} |")
(ROOT / "tests" / "resultats-obtenus.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n{ok}/{len(results)} réussis. Rapport : tests/resultats-obtenus.md")
sys.exit(0 if ok == len(results) else 1)
