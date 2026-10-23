# Résultats attendus

Tous les appels passent par la passerelle WSO2 : `https://localhost:8243/structures/<version>/...`.
Les codes WSO2 viennent de la [documentation officielle des erreurs](https://github.com/wso2/docs-apim/blob/master/en/docs/reference/troubleshooting/error-handling.md).

Automatique : `python tests/e2e.py` rejoue tout et écrit `tests/resultats-obtenus.md`.
Manuel : collection `tests/postman_collection.json` (dossiers 0 à 5).

| N° | Scénario | Préparation | Requête | Résultat attendu |
| --- | --- | --- | --- | --- |
| T1 | Liste paginée (bout en bout) | aucune | `GET /structures/1.0.0/structures?page=1&size=10` | 200, 10 éléments, `totalPages = ceil(total / size)`, aucun champ v2 |
| T2 | Détail | aucune | `GET .../structures/5` | 200, `id = 5` |
| T3 | Structure inexistante | aucune | `GET .../structures/9999` | 404, `code = STRUCTURE_NOT_FOUND`, format `{code, message, details, path, timestamp}` |
| T4 | Paramètre invalide | aucune | `page=-1`, `size=abc`, `type=HOPITAL` | 400, `code = VALIDATION_ERROR`, champ fautif dans `details` |
| T5 | Jeton absent | aucune | sans en-tête `Authorization` | 401, code WSO2 **900902** |
| T6 | Jeton invalide | aucune | `Authorization: Bearer faux` | 401, code WSO2 **900901** |
| T7 | Application non abonnée | jeton de `AppNonAbonnee` | `GET .../structures` | 403, code WSO2 **900908** |
| T7b | Souscription bloquée | `python wso2/wso2ctl.py block-sub` | `GET .../structures` | 401, code WSO2 **900907** (débloquer ensuite : `unblock-sub`) |
| T8 | Dépassement de quota | plan `Plan10ParMinute` | 11 appels ou plus en moins d'une minute | 429, code WSO2 **900800** |
| T9 | Retrait temporaire de publication | `python wso2/wso2ctl.py block` | `GET .../structures` | 503, code WSO2 **700700** ; `GET http://localhost:8000/health` répond toujours 200 |
| T10 | Arrêt technique | `docker compose stop api` (API toujours PUBLISHED) | `GET .../structures` | 5xx, code WSO2 **101503** (connexion au backend impossible) |
| T11 | Nouvelle version | `python wso2/wso2ctl.py new-version` | `GET /structures/2.0.0/structures/1` | 200 avec `district`, `capacite_lits`, `services` ; la v1 passe en DEPRECATED et répond encore |
| T12 | Republication | `python wso2/wso2ctl.py republish` | `GET .../structures` | 200, sans autre reconfiguration |

## Pourquoi T9 et T10 prouvent deux états distincts

| | T9 - Retrait de publication | T10 - Arrêt technique |
| --- | --- | --- |
| Origine | Décision de gestion dans le Publisher | Panne ou arrêt du conteneur backend |
| État du cycle de vie WSO2 | BLOCKED | PUBLISHED (inchangé) |
| Qui répond au client | La passerelle, sans appeler le backend | La passerelle, après échec de connexion au backend |
| Code d'erreur | 700700 | 101503 |
| Backend `/health` | 200 (il tourne) | inaccessible |
| Retour à la normale | `wso2ctl republish` | `docker compose start api` |

## Tests du backend seul (sans WSO2)

`cd api && pytest -v` : 30 tests (pagination, filtres, recherche, 400/404/503, conformité aux contrats OpenAPI v1 et v2).
