# Qui pousse quoi dans le dépôt

Chaque membre pousse les fichiers de son rôle, sur sa branche, puis ouvre une Pull Request vers `main`.
Le Membre 1 relit et fusionne. **Avant de pousser, chacun lit et comprend ses fichiers** : le prof posera des questions.

| Ordre | Membre | Branche | Fichiers | Message de commit proposé |
| --- | --- | --- | --- | --- |
| 1 | Membre 1 | `feat/socle` | `README.md`, `docker-compose.yml`, `.gitignore`, `docs/repartition-commits.md` | `Socle du projet : docker compose et README` |
| 2 | Membre 3 | `feat/base-donnees` | `db/init.sql`, `db/generate_seed.py`, `db/seed.sql` | `Base PostgreSQL et données fictives des structures` |
| 3 | Membre 2 | `feat/api-v1` | `api/` sauf `tests/` et `pytest.ini` | `API FastAPI : liste, recherche, détail, erreurs` |
| 4 | Membre 3 | `feat/openapi` | `openapi/v1.yaml`, `openapi/v2.yaml` | `Contrats OpenAPI v1 et v2` |
| 5 | Membre 2 | `feat/tests-api` | `api/tests/`, `api/pytest.ini` | `Tests du backend et des contrats` |
| 6 | Membre 4 | `feat/wso2-cycle-de-vie` | `wso2/`, `docs/wso2-setup.md`, `docs/cycle-de-vie.md` | `Automatisation WSO2 et cycle de vie` |
| 7 | Membre 5 | `feat/tests-wso2` | `tests/` | `Tests Postman et bout en bout` |
| 8 | Membre 1 | `feat/presentation` | `presentation/`, `docs/captures/` | `Présentation et captures` |

## Commandes pour chaque membre

```bash
# une seule fois : récupérer le dépôt du groupe
git clone https://github.com/leilatirouda/projet-dev-composant_Groupe3.git
cd projet-dev-composant_Groupe3

# pour chaque ligne du tableau
git checkout main
git pull
git checkout -b feat/base-donnees            # la branche de la ligne
# copier SES fichiers depuis le .zip dans le dossier du dépôt
git add db/
git commit -m "Base PostgreSQL et données fictives des structures"
git push -u origin feat/base-donnees
# puis sur GitHub : Compare & pull request
```

## Ensuite

Chaque correction faite pendant les tests (captures, ajustements WSO2, résultats obtenus) fait l'objet d'un nouveau commit par la personne concernée.
Ne jamais pousser `tests/postman_environment.local.json` ni `wso2/.state.json` : ils contiennent des clés. Ils sont exclus par `.gitignore`.
