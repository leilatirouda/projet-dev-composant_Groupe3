# Cycle de vie de l'API Structures

## États utilisés

```
            Publish            Publish v2 (+ « Deprecate old versions »)     Retire
 CREATED ───────────▶ PUBLISHED ─────────────────────────────▶ DEPRECATED ──────────▶ RETIRED
                        │   ▲
                 Block  │   │  Re-Publish
                        ▼   │
                       BLOCKED      (retrait temporaire de publication)

 ── Hors cycle de vie ──────────────────────────────────────────────────────────────────────
 Arrêt technique : backend arrêté ou en panne. WSO2 reste PUBLISHED : rien n'a été décidé,
 la passerelle essaie d'appeler le backend et échoue.
```

| État | Visible dans le Developer Portal | Nouvelles souscriptions | Appels via la passerelle |
| --- | --- | --- | --- |
| CREATED | non | non | non déployée |
| PUBLISHED | oui | oui | 200 |
| BLOCKED | oui | non | 503, code 700700 |
| DEPRECATED | oui | non | 200 pour les souscriptions existantes |
| RETIRED | non | non | API retirée de la passerelle |

## Retrait de publication et arrêt technique : deux états distincts

| Question | Retrait de publication (BLOCKED) | Arrêt technique |
| --- | --- | --- |
| Qui décide ? | L'éditeur de l'API dans le Publisher | Personne : panne, maintenance, crash |
| L'état WSO2 change-t-il ? | Oui : BLOCKED | Non : reste PUBLISHED |
| Le backend tourne-t-il ? | Oui (`/health` = 200) | Non |
| La passerelle appelle-t-elle le backend ? | Non, elle refuse avant | Oui, et la connexion échoue |
| Code renvoyé | 503 / **700700** « API blocked » | 5xx / **101503** « Connection failed » |
| Comment le voir | Publisher > Lifecycle : BLOCKED | Publisher : PUBLISHED ; `docker compose ps` : api arrêté |
| Retour à la normale | Re-Publish | Redémarrer le backend |

Démonstration : `python tests/e2e.py` exécute T9 puis T10 et enregistre les deux réponses dans `tests/resultats-obtenus.md`.

## Stratégie de versionnement

- **Version majeure dans l'URL** : `/structures/1.0.0` et `/structures/2.0.0` coexistent.
- **v2 compatible avec v1** : mêmes routes, mêmes champs, plus des champs et un filtre en plus. Un client v1 peut passer en v2 sans rien casser. Le test `test_v1_v2_memes_identifiants` le vérifie.
- **Dépréciation** : la v1 est dépréciée à la publication de la v2. Les souscriptions existantes continuent de fonctionner, mais aucune nouvelle n'est acceptée.
- **Retrait** : la v1 passe en RETIRED quand plus aucune application ne l'utilise.

## Application consommatrice et droits

| Cas | Application | Résultat |
| --- | --- | --- |
| Abonnée, souscription active | AppPortailSante | 200 |
| Non abonnée | AppNonAbonnee | 403 / 900908 |
| Souscription bloquée par le Publisher | AppPortailSante | 401 / 900907 |
| Quota du plan dépassé | AppPortailSante | 429 / 900804 |
