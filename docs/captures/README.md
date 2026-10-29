# Captures d'écran

Prises sur l'installation locale (WSO2 API Manager 4.6.0), après `python wso2/wso2ctl.py setup` puis `python tests/e2e.py` :
la v1 est donc DEPRECATED et la v2 PUBLISHED.

Les captures de la passerelle montrent des appels réellement exécutés ; seul le jeton est remplacé par `$TOKEN`.

## Publisher, Admin Portal et Developer Portal

| Fichier | Ce qu'on y voit |
| --- | --- |
| `01-publisher-liste-apis.png` | Les deux versions de l'API : 1.0.0 DEPRECATED, 2.0.0 PUBLISHED |
| `02-publisher-endpoint-backend.png` | Routage vers le backend : `http://api:8000/v1` |
| `03-publisher-cycle-de-vie-v1.png` | Historique du cycle de vie : CREATED, PUBLISHED, BLOCKED, PUBLISHED, DEPRECATED |
| `04-publisher-apercu-v2.png` | v2 publiée, sécurité OAuth2, plan `Plan10ParMinute` |
| `05-publisher-souscriptions-v1.png` | Plans de la v1 et souscription de `AppPortailSante` |
| `06-admin-plan-quota.png` | Plan `Plan10ParMinute` : 10 requêtes par minute |
| `07-devportal-catalogue.png` | Catalogue du Developer Portal : seule la v2 est proposée aux nouvelles souscriptions |
| `08-devportal-applications.png` | Applications consommatrices : `AppPortailSante` (2 souscriptions) et `AppNonAbonnee` (0) |
| `09-devportal-souscriptions-app.png` | Souscriptions de `AppPortailSante` à la v1 et à la v2 |

## Réponses de la passerelle

| Fichier | Scénario | Réponse |
| --- | --- | --- |
| `10-passerelle-t1-liste-200.png` | T1 - Liste paginée (v1 dépréciée, souscription existante) | 200 |
| `11-passerelle-t11-v2-detail-200.png` | T11 - Nouvelle version avec ses champs supplémentaires | 200 |
| `12-passerelle-t3-inexistante-404.png` | T3 - Structure inexistante | 404 / `STRUCTURE_NOT_FOUND` |
| `13-passerelle-t5-sans-jeton-401.png` | T5 - Jeton absent | 401 / 900902 |
| `14-passerelle-t7-non-abonnee-403.png` | T7 - Application non abonnée | 403 / 900908 |
| `15-passerelle-t9-api-bloquee-503.png` | T9 - Retrait de publication (API BLOCKED) | 503 / 700700 |
| `16-passerelle-t10-arret-technique-500.png` | T10 - Arrêt technique (backend arrêté, API toujours PUBLISHED) | 500 / 101503 |
| `17-passerelle-t8-quota-429.png` | T8 - Dépassement du quota | 429 / 900804 |

T9 et T10 illustrent les deux états distincts demandés : retrait de publication décidé dans WSO2, et arrêt technique du backend.
