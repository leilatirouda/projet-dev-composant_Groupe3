# Configuration manuelle de WSO2 (interface web)

Ce document décrit pas à pas, dans les interfaces web, ce que fait `python wso2/wso2ctl.py setup`.
Il sert de secours si le script échoue, et pour la démonstration pendant la soutenance.
Les intitulés de menus peuvent légèrement varier selon la version. Les écrans obtenus sont dans [captures/](captures/README.md).

Identifiant : `admin` / `admin`. Le navigateur signale un certificat non sûr : c'est normal en local, cliquer sur « Avancé » puis « Continuer ».

## 1. Créer le plan d'accès avec quota (Admin Portal)

1. Ouvrir https://localhost:9443/admin
2. Menu **Rate Limiting Policies** > **Subscription Policies** > **Add Policy**
3. Remplir :
    - Name : `Plan10ParMinute`
    - Display name : `Plan 10 requêtes/minute`
    - Request Count : `10`, Unit Time : `1 minute`
    - Policy Flags : cocher **Stop on Quota Reach** (les requêtes en trop sont rejetées en 429)
    - Billing plan : Free
4. **Save**

Capture : la liste des Subscription Policies avec `Plan10ParMinute`.

## 2. Créer l'API depuis le contrat OpenAPI (Publisher)

1. Ouvrir https://localhost:9443/publisher
2. **Create API** > **Import OpenAPI** > **OpenAPI File/Archive** > choisir `openapi/v1.yaml` > **Next**
3. Remplir :
    - Name : `StructuresSanitaires`
    - Context : `/structures` (WSO2 ajoute la version : `/structures/1.0.0`)
    - Version : `1.0.0`
    - Endpoint : `http://api:8000/v1`, nom du service Docker et non `localhost`
4. **Create** : l'API est dans l'état **CREATED**

Capture : la page Overview de l'API, avec l'état CREATED.

## 3. Configurer l'API

1. Menu de gauche **Portal Configurations** > **Subscriptions** (ou **Business Plans**) : cocher `Plan10ParMinute` et `Unlimited`, **Save**
2. **API Configurations** > **Runtime** : vérifier que la sécurité **OAuth2** est active
3. **Endpoints** : vérifier `http://api:8000/v1` pour Production et Sandbox
4. **API Configurations** > **Resources** : les 3 ressources GET du contrat apparaissent (`/structures`, `/structures/search`, `/structures/{id}`)

## 4. Déployer et publier

1. **Deploy** > **Deployments** > cocher la passerelle **Default** > **Deploy**
2. **Publish** > **Lifecycle** > **Publish** : l'état passe à **PUBLISHED**

Capture : la page Lifecycle avec l'état PUBLISHED.

## 5. Application consommatrice (Developer Portal)

1. Ouvrir https://localhost:9443/devportal
2. **Applications** > **Add New Application** :
    - Name : `AppPortailSante`
    - Shared Quota : `Unlimited`
    - **Save**
3. Dans l'application > **Production Keys** > **OAuth2 Tokens** > cocher `Client Credentials` > **Generate Keys**
4. Noter le **Consumer Key** et le **Consumer Secret** et les mettre dans l'environnement Postman
5. Recommencer pour `AppNonAbonnee`, mais **sans** souscription : elle sert au test 403

## 6. Souscription

1. Developer Portal > **APIs** > `StructuresSanitaires` > **Subscriptions** (ou bouton **Subscribe**)
2. Application : `AppPortailSante`, Business Plan : `Plan10ParMinute` > **Subscribe**
3. Dans l'application > **Production Keys** > **Generate Access Token** pour un jeton de test

Test rapide :

```bash
curl -k -H "Authorization: Bearer <jeton>" "https://localhost:8243/structures/1.0.0/structures?size=2"
```

Le Developer Portal propose aussi une **Try Out** console sur la page de l'API.

## 7. Cycle de vie (Publisher > Publish > Lifecycle)

| Démonstration | Action dans le Publisher | Résultat |
| --- | --- | --- |
| Retrait temporaire | **Block** | API toujours visible ; la passerelle répond 503 / 700700 |
| Remise en service | **Re-Publish** | 200 à nouveau |
| Nouvelle version | Page Overview > **Create New Version** : `2.0.0` | Nouvelle API en état CREATED |
| | Dans la v2 : **API Definition** > importer `openapi/v2.yaml` ; **Endpoints** : `http://api:8000/v2` | |
| | **Deploy**, puis **Publish** en cochant « Deprecate old versions after publishing the API » | v2 PUBLISHED, v1 DEPRECATED |
| Fin de vie | Dans la v1 : **Retire** | La v1 disparaît de la passerelle et du portail |

## 8. Bloquer une souscription (Publisher)

Dans l'API, menu **Portal Configurations** > **Subscriptions**, sur la ligne de `AppPortailSante` > **Block All**, et plus tard **Unblock**.
La passerelle répond alors 401 avec le code 900907.

## 9. Arrêt technique

```bash
docker compose stop api      # le backend s'arrête ; l'API reste PUBLISHED dans WSO2
# appel via la passerelle : erreur 5xx, code 101503
docker compose start api
```

Comparer avec le blocage (étape 7), comme décrit dans [cycle-de-vie.md](cycle-de-vie.md).
