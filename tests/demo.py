"""Démonstration pas à pas : lance chaque commande de test, affiche le résultat et l'explique en une ligne.

Prérequis : installation neuve, donc v1 PUBLISHED et pas de v2.
Usage     : python tests/demo.py              pause (Entrée) avant chaque étape
            python tests/demo.py --etape 6    reprendre à l'étape 6
            python tests/demo.py --sans-pause enchaîner sans s'arrêter
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.system("")  # active les couleurs dans la console Windows
sys.stdout.reconfigure(line_buffering=True)  # nos lignes s'affichent avant celles des commandes lancées

ROOT = Path(__file__).resolve().parents[1]
GW = "https://localhost:8243/structures"
HOST = "https://localhost:9443"
PAUSE = "--sans-pause" not in sys.argv
DEPART = int(sys.argv[sys.argv.index("--etape") + 1]) if "--etape" in sys.argv else 1

VERT, ROUGE, BLEU, GRIS, GRAS, FIN = "\033[92m", "\033[91m", "\033[96m", "\033[90m", "\033[1m", "\033[0m"


# ---------------------------------------------------------------- affichage
def titre(num, texte):
    if PAUSE:
        input(f"\n{GRIS}[Entrée : étape {num}]{FIN} ")
    print(f"\n{BLEU}{GRAS}{num}. {texte}{FIN}")


def commande(texte):
    print(f"{GRIS}$ {texte}{FIN}")


def resultat(r, attendu, explication):
    """Affiche statut, code et message, puis l'explication si le résultat est celui attendu."""
    if r is None:
        print(f"  {ROUGE}aucune réponse de la passerelle{FIN}")
        return
    couleur = VERT if r.status_code < 400 else ROUGE
    try:
        corps = r.json()
    except ValueError:
        corps = None
    if not isinstance(corps, dict):
        texte = r.text[:200]
    elif "id" in corps:
        texte = f"structure {corps['id']} : {corps['nom']} ({corps['type']}, {corps['region']})"
    elif "items" in corps:
        texte = f"{len(corps['items'])} structures sur {corps['total']} : " + ", ".join(s["nom"] for s in corps["items"][:3])
    elif "code" in corps:
        texte = f"code {corps['code']} : {corps.get('message') or corps.get('type') or ''}"
    else:
        texte = json.dumps(corps, ensure_ascii=False)[:200]
    print(f"  {couleur}{GRAS}HTTP {r.status_code}{FIN}  {texte}")
    if r.status_code == attendu:
        print(f"  {VERT}-> {explication}{FIN}")
    else:
        print(f"  {ROUGE}-> résultat inattendu (attendu : {attendu}){FIN}")


def info(texte, explication):
    print(f"  {texte}")
    print(f"  {VERT}-> {explication}{FIN}")


# ---------------------------------------------------------------- appels
def etat():
    return json.loads((ROOT / "wso2" / ".state.json").read_text())


def jeton(app):
    r = requests.post(f"{HOST}/oauth2/token", auth=(app["consumerKey"], app["consumerSecret"]),
                      data={"grant_type": "client_credentials"}, verify=False, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def appel(chemin, tok, version="1.0.0", timeout=30):
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    try:
        return requests.get(f"{GW}/{version}{chemin}", headers=headers, verify=False, timeout=timeout)
    except requests.exceptions.RequestException:
        return None


def curl(chemin, tok="$TOKEN", version="1.0.0"):
    h = f'-H "Authorization: Bearer {tok}" ' if tok else ""
    commande(f'curl -k {h}"{GW}/{version}{chemin}"')


def jusqua(fn, condition, essais=24, pause=5):
    """Les changements d'état mettent quelques secondes à atteindre la passerelle."""
    r = None
    for _ in range(essais):
        r = fn()
        if r is not None and condition(r):
            return r
        time.sleep(pause)
    return r


def ctl(cmd):
    commande(f"python wso2/wso2ctl.py {cmd}")
    subprocess.run([sys.executable, str(ROOT / "wso2" / "wso2ctl.py"), cmd], cwd=ROOT, check=True)


def compose(*args):
    commande("docker compose " + " ".join(args))
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True, capture_output=True)


def sante_backend():
    """/health interrogé depuis le conteneur api : indépendant du port 8000 de la machine."""
    commande("docker exec g3-api ... GET http://localhost:8000/health")
    code = ("import urllib.request;"
            "print(urllib.request.urlopen('http://localhost:8000/health', timeout=5).read().decode())")
    r = subprocess.run(["docker", "exec", "g3-api", "python", "-c", code], capture_output=True, text=True)
    return r.stdout.strip() or "injoignable"


def avec_chrono(fn):
    """Affiche le temps écoulé pendant une attente longue (arrêt technique)."""
    fini = threading.Event()

    def chrono():
        debut = time.time()
        while not fini.wait(1):
            print(f"\r  {GRIS}attente de la réponse : {int(time.time() - debut)} s{FIN}   ", end="", flush=True)

    t = threading.Thread(target=chrono, daemon=True)
    t.start()
    try:
        return fn()
    finally:
        fini.set()
        t.join()
        print()


# ---------------------------------------------------------------- étapes
def etape_1(t):
    titre(1, "Appel avec une application abonnée")
    curl("/structures?size=3")
    resultat(appel("/structures?size=3", t["ok"]), 200,
             "jeton valide et souscription active : WSO2 transmet au backend, qui répond.")


def etape_2(t):
    titre(2, "Appel sans jeton")
    curl("/structures", tok=None)
    resultat(appel("/structures", None), 401, "pas de jeton : WSO2 refuse sans contacter le backend.")


def etape_3(t):
    titre(3, "Appel avec un jeton invalide")
    curl("/structures", tok="faux-jeton")
    resultat(appel("/structures", "faux-jeton"), 401, "jeton inconnu de WSO2 : appel refusé.")


def etape_4(t):
    titre(4, "Appel par une application non abonnée")
    curl("/structures", tok="$TOKEN_APP_NON_ABONNEE")
    resultat(appel("/structures", t["nosub"]), 403, "jeton valide mais aucune souscription à l'API : accès interdit.")


def etape_5(t):
    titre(5, "Souscription bloquée, puis débloquée")
    ctl("block-sub")
    curl("/structures")
    resultat(jusqua(lambda: appel("/structures", t["ok"]), lambda r: r.status_code == 401), 401,
             "souscription bloquée : cette application seule est refusée, l'API reste publiée.")
    ctl("unblock-sub")
    curl("/structures?size=3")
    resultat(jusqua(lambda: appel("/structures?size=3", t["ok"]), lambda r: r.status_code == 200), 200,
             "souscription débloquée : accès rétabli.")


def etape_6(t):
    titre(6, "Retrait temporaire de publication (Block), puis republication")
    ctl("block")
    curl("/structures")
    resultat(jusqua(lambda: appel("/structures", t["ok"]), lambda r: r.status_code == 503), 503,
             "API BLOCKED : WSO2 refuse sans appeler le backend.")
    info(f"backend : {sante_backend()}", "le backend tourne toujours : c'est une décision, pas une panne.")
    ctl("republish")
    curl("/structures?size=3")
    resultat(jusqua(lambda: appel("/structures?size=3", t["ok"]), lambda r: r.status_code == 200), 200,
             "API republiée : accès rétabli sans autre configuration.")


def etape_7(t):
    titre(7, "Arrêt technique : backend arrêté, puis redémarré")
    compose("stop", "api")
    curl("/structures")
    resultat(avec_chrono(lambda: appel("/structures", t["ok"], timeout=150)), 500,
             "WSO2 n'arrive pas à joindre le backend (101503 : connexion refusée, 101508 : délai de connexion "
             "dépassé) : erreur différente du blocage (503 / 700700).")
    ctl("status")
    print(f"  {VERT}-> l'API est toujours PUBLISHED : c'est une panne, pas un retrait de publication.{FIN}")
    compose("start", "api")
    curl("/structures?size=3")
    resultat(avec_chrono(lambda: jusqua(lambda: appel("/structures?size=3", t["ok"]),
                                        lambda r: r.status_code == 200)), 200,
             "backend redémarré : accès rétabli (WSO2 avait suspendu l'endpoint environ 30 s).")


def etape_8(t):
    titre(8, "Nouvelle version 2.0.0")
    ctl("new-version")
    t["v2"] = jeton(etat()["app"])
    curl("/structures/1", version="2.0.0")
    r = jusqua(lambda: appel("/structures/1", t["v2"], version="2.0.0"), lambda r: r.status_code == 200)
    resultat(r, 200, "la v2 est publiée et répond.")
    if r is not None and r.status_code == 200:
        s = r.json()
        info(f"district = {s.get('district')}, capacite_lits = {s.get('capacite_lits')}, services = {s.get('services')}",
             "la v2 ajoute ces champs à ceux de la v1.")
    curl("/structures/1")
    resultat(appel("/structures/1", t["v2"]), 200, "la v1, maintenant DEPRECATED, répond encore aux abonnés existants.")


def etape_9(t):
    titre(9, "Dépassement du quota (10 appels par minute)")
    tok = t.get("v2") or t["ok"]
    curl("/structures?size=1", version="2.0.0")
    codes, r = [], None
    for _ in range(40):
        r = appel("/structures?size=1", tok, version="2.0.0")
        codes.append(str(r.status_code) if r is not None else "-")
        if r is not None and r.status_code == 429:
            break
    print(f"  {GRIS}codes reçus : {' '.join(codes)}{FIN}")
    resultat(r, 429, f"quota du plan Plan10ParMinute dépassé au {len(codes)}e appel : WSO2 refuse.")


ETAPES = [etape_1, etape_2, etape_3, etape_4, etape_5, etape_6, etape_7, etape_8, etape_9]

if __name__ == "__main__":
    s = etat()
    jetons = {"ok": jeton(s["app"]), "nosub": jeton(s["app_no_sub"])}
    for num, fn in enumerate(ETAPES, start=1):
        if num >= DEPART:
            fn(jetons)
    print(f"\n{VERT}{GRAS}Fin de la démonstration.{FIN}")
