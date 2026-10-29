# Gestion du cycle de vie d'une API avec WSO2 API Manager

**Groupe 3 SI - Thème 24 - Projet composants et services web 2026**

Une API REST de consultation de structures sanitaires (données fictives) est publiée et gérée dans
WSO2 API Manager 4.6.0. Le projet couvre l'ensemble du cycle de vie de l'API :

- le contrat OpenAPI ;
- le routage vers le backend ;
- un plan d'accès avec authentification OAuth2 et quota ;
- une application consommatrice et sa souscription ;
- la publication, le blocage, la nouvelle version et la dépréciation ;
- la distinction entre **retrait de publication** et **arrêt technique**.

## Architecture

```
 Client (Postman / e2e.py)
     │  HTTPS + jeton OAuth2 (JWT)
     ▼
 WSO2 API Manager 4.6.0  ── conteneur g3-wso2am
     │  9443 : Publisher, Developer Portal, Admin, /oauth2/token
     │  8243 : passerelle    /structures/1.0.0/*  ->  http://api:8000/v1/*
     │                       /structures/2.0.0/*  ->  http://api:8000/v2/*
     ▼
 API FastAPI (Python 3.12)  ── conteneur g3-api, port 8000
     │
     ▼
 PostgreSQL 16  ── conteneur g3-postgres (port 5433 sur la machine)
     base sante_db, table structures_sanitaires, 80 structures fictives
```

| Composant | Rôle | Dossier |
| --- | --- | --- |
| PostgreSQL | Base de référence | `db/` |
| FastAPI | Backend : lecture, recherche, pagination, erreurs | `api/` |
| Contrats OpenAPI 3.0.3 | Paramètres, réponses, erreurs ; v1 et v2 | `openapi/` |
| WSO2 API Manager | Passerelle, sécurité, quotas, cycle de vie | `wso2/` |
| Tests | pytest, Postman/Newman, bout en bout | `tests/`, `api/tests/` |

## Prérequis

| Outil | Version testée | Remarque |
| --- | --- | --- |
| Docker Desktop (ou Docker Engine + Compose v2) | 24 ou plus | Donner **au moins 4 Go de RAM** à Docker (WSO2 en prend environ 2 à 3) |
| Python | 3.10 ou plus (testé en 3.12 et 3.14) | Pour `wso2ctl.py`, `e2e.py` et les tests du backend |
| Postman ou Newman | Newman 6 (Node.js 18 ou plus) | `npm install -g newman` |
| Git | toute version récente | |

Ports libres nécessaires : 5433, 8000, 8243, 8280, 9443.

### Outils installés hors Docker

PostgreSQL, l'API et WSO2 tournent dans Docker. Les outils de configuration et de test s'installent sur la machine :

```bash
python --version                                   # 3.10 ou plus
python -m pip install -r wso2/requirements.txt     # wso2ctl.py et tests/e2e.py
python -m pip install -r api/requirements-dev.txt  # tests du backend (pytest)
npm install -g newman                              # facultatif : collection Postman en ligne de commande
```

La configuration de WSO2 (plan, API, publication, applications, souscription) se fait soit par `wso2ctl.py setup`,
soit à la main en suivant la procédure distincte [docs/wso2-setup.md](docs/wso2-setup.md).

## Installation sur une machine neuve

```bash
# 1. Récupérer le projet
git clone https://github.com/leilatirouda/projet-dev-composant_Groupe3.git
cd projet-dev-composant_Groupe3

# 2. Démarrer PostgreSQL, l'API et WSO2 (premier lancement : téléchargement d'environ 2 Go)
docker compose up -d --build

# 3. Attendre que WSO2 ait fini de démarrer (2 à 4 minutes)
docker compose logs -f wso2am        # attendre la ligne "WSO2 Carbon started", puis Ctrl+C

# 4. Vérifier le backend
curl http://localhost:8000/health    # {"status":"UP","database":"UP"}

# 5. Configurer WSO2 automatiquement : plan, API v1, publication, applications, souscription
python -m pip install -r wso2/requirements.txt
python wso2/wso2ctl.py setup
```

La commande `setup` termine par un appel réel via la passerelle (`HTTP 200`). Elle écrit
`tests/postman_environment.local.json`, qui contient les clés des applications et n'est pas versionné.

Pour faire la même configuration à la main dans l'interface, suivre [docs/wso2-setup.md](docs/wso2-setup.md).

Interfaces web (identifiant `admin` / mot de passe `admin`, accepter le certificat auto-signé) :

| Interface | URL |
| --- | --- |
| Publisher | https://localhost:9443/publisher |
| Developer Portal | https://localhost:9443/devportal |
| Admin Portal | https://localhost:9443/admin |
| Documentation du backend | http://localhost:8000/docs |

## Utilisation

```bash
# Obtenir un jeton pour l'application abonnée
TOKEN=$(python wso2/wso2ctl.py token)

# Appeler l'API via la passerelle
curl -k -H "Authorization: Bearer $TOKEN" "https://localhost:8243/structures/1.0.0/structures?page=1&size=5"
curl -k -H "Authorization: Bearer $TOKEN" "https://localhost:8243/structures/1.0.0/structures/search?q=ouaga"
curl -k -H "Authorization: Bearer $TOKEN" "https://localhost:8243/structures/1.0.0/structures/5"
```

Sous Windows PowerShell : `$TOKEN = python wso2/wso2ctl.py token`, puis `curl.exe -k -H "Authorization: Bearer $TOKEN" ...`.

### Endpoints

| Méthode | Chemin (après `/structures/<version>`) | Paramètres | Réponses |
| --- | --- | --- | --- |
| GET | `/structures` | `page`, `size` (1-100), `region`, `type`, `statut`, `district` (v2) | 200, 400 |
| GET | `/structures/search` | `q` (obligatoire, 2-100 car.), `page`, `size`, `region`, `type`, `district` (v2) | 200, 400 |
| GET | `/structures/{id}` | `id` entier >= 1 | 200, 400, 404 |

Erreurs de la passerelle sur toutes les routes : 401, 403, 429, 500 (backend injoignable) et 503 (API bloquée). Le détail est dans [openapi/v1.yaml](openapi/v1.yaml).

## Cycle de vie : commandes de démonstration

| Étape | Commande | État WSO2 |
| --- | --- | --- |
| Création + publication | `python wso2/wso2ctl.py setup` | CREATED -> PUBLISHED |
| Retrait temporaire | `python wso2/wso2ctl.py block` | PUBLISHED -> BLOCKED |
| Republication | `python wso2/wso2ctl.py republish` | BLOCKED -> PUBLISHED |
| Arrêt technique (panne) | `docker compose stop api` puis `docker compose start api` | PUBLISHED (inchangé) |
| Souscription bloquée | `python wso2/wso2ctl.py block-sub` / `unblock-sub` | souscription BLOCKED / UNBLOCKED |
| Nouvelle version | `python wso2/wso2ctl.py new-version` | v2 PUBLISHED, v1 DEPRECATED |
| Fin de vie de la v1 | `python wso2/wso2ctl.py retire-v1` | v1 RETIRED |
| Vérifier | `python wso2/wso2ctl.py status` | |

Faire `block` et `republish` **avant** `new-version`. Une fois la v1 dépréciée, elle ne peut plus être bloquée puis republiée.
L'explication complète se trouve dans [docs/cycle-de-vie.md](docs/cycle-de-vie.md).

## Tests

| Niveau | Commande | Couvre |
| --- | --- | --- |
| Backend seul | `cd api && pip install -r requirements-dev.txt && pytest -v` | 30 tests : pagination, filtres, erreurs, base indisponible, contrats OpenAPI |
| Postman / Newman | `newman run tests/postman_collection.json -e tests/postman_environment.local.json -k --folder "0 - Jetons" --folder "1 - Fonctionnel (T1-T4)" --folder "2 - Sécurité (T5-T7)"` | T1 à T7 |
| Quota | `newman run tests/postman_collection.json -e tests/postman_environment.local.json -k --folder "0 - Jetons" --folder "3 - Quota (T8) - lancer seul"` | T8 |
| Bout en bout | `python tests/e2e.py` | T1 à T12, avec changements d'état, rapport `tests/resultats-obtenus.md` |

Les tests du backend seul demandent une base chargée. Avec Docker : `DATABASE_URL=postgresql://sante:sante@localhost:5433/sante_db pytest -v`
(PowerShell : `$env:DATABASE_URL="postgresql://sante:sante@localhost:5433/sante_db"; pytest -v`).

- Résultats attendus : [tests/resultats-attendus.docx](tests/resultats-attendus.docx) (Word)
- Résultats obtenus sur une installation neuve (16/16 de bout en bout, 30/30 backend, 27/27 Postman) :
  [tests/resultats-obtenus.docx](tests/resultats-obtenus.docx) (Word)
- Versions texte : [resultats-attendus.md](tests/resultats-attendus.md) et [resultats-obtenus.md](tests/resultats-obtenus.md),
  ce dernier étant réécrit automatiquement à chaque `python tests/e2e.py`
- Captures des portails WSO2 et des réponses de la passerelle : [docs/captures/](docs/captures/README.md)

## Arrêt et remise à zéro

```bash
docker compose stop            # arrête sans rien perdre ; docker compose start pour reprendre
docker compose down            # supprime les conteneurs : la configuration WSO2 est perdue
docker compose down -v         # supprime aussi la base PostgreSQL
rm wso2/.state.json            # puis docker compose up -d et wso2ctl.py setup pour tout recréer
```

WSO2 garde sa configuration dans le conteneur. Après un `down`, on relance simplement `wso2ctl.py setup`, ce qui est le principe de l'installation reproductible.

## Problèmes fréquents

| Symptôme | Cause probable | Solution |
| --- | --- | --- |
| `wso2ctl.py setup` attend sans fin | WSO2 pas encore démarré ou manque de mémoire | `docker compose logs wso2am` ; augmenter la RAM de Docker |
| `g3-wso2am` en `Exited (0)`, `UnknownHostException` dans les logs | Conteneur WSO2 rattaché à aucun réseau (réseau du projet recréé après sa création) | `docker compose up -d --force-recreate wso2am`, attendre « WSO2 Carbon started », relancer `setup` |
| 101503 alors que l'API tourne | WSO2 ne joint pas le backend | Endpoint `http://api:8000/v1`, jamais `localhost` (localhost = le conteneur WSO2 lui-même) |
| 900908 avec la bonne application | Souscription absente ou sur une autre version | Developer Portal > Applications > Subscriptions |
| 429 pendant les autres tests | Le quota de 10/min a été consommé par T8 | Attendre une minute ; lancer T8 en dernier |
| Port 5432 déjà pris | PostgreSQL local | Le projet utilise 5433 côté machine |
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | Un autre service utilise le port 8000 | Libérer le port 8000 : `tests/e2e.py` l'utilise pour vérifier `/health` (T9b) |
| T10 met longtemps à répondre | WSO2 tente encore l'ancienne adresse du backend arrêté (40 à 75 s) | Normal ; `e2e.py` attend jusqu'à 120 s |
| Mac Apple Silicon : image WSO2 lente | Image amd64 émulée | Activer « Use Rosetta » dans Docker Desktop |

## Structure du dépôt

```
├── README.md
├── docker-compose.yml
├── api/                       backend FastAPI (Dockerfile, requirements, tests)
├── db/                        init.sql, seed.sql, generate_seed.py
├── openapi/                   v1.yaml, v2.yaml
├── wso2/                      wso2ctl.py (automatisation REST), requirements.txt
├── tests/                     Postman, e2e.py, résultats attendus et obtenus
├── docs/                      procédure WSO2 manuelle, cycle de vie, répartition, captures/
└── presentation/              PowerPoint
```

## Équipe

| Membre | Rôle |
| --- | --- |
| LOMPO Ephraim | Chef de projet, intégration, README, présentation |
| OUOBA Arnaud | Backend FastAPI et ses tests |
| NIKIEMA Abdoul Fatahou | Base de données et contrats OpenAPI |
| TIROUDA Leila | WSO2 : routage et cycle de vie |
| ROUAMBA Frank | WSO2 : sécurité, quotas, applications ; tests |
