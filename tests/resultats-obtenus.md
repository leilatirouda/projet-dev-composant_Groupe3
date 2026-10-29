# Résultats obtenus (générés par tests/e2e.py)

Exécution du 29/10/2026 à 09:50 : **16/16 scénarios réussis**.

| N° | Scénario | Attendu | Obtenu | Résultat |
| --- | --- | --- | --- | --- |
| T1 | Liste paginée | 200 | `200 {"page":1,"size":10,"total":77,"totalPages":8,"items":[{"id":1,"code":"CSPS-0001","nom":"C` | OK |
| T2 | Détail id=5 | 200 | `200 {"id":5,"code":"CSPS-0005","nom":"CSPS Sarfalao de Ouagadougou","type":"CSPS","statut":"PU` | OK |
| T3 | Structure inexistante | 404 + STRUCTURE_NOT_FOUND | `404 {"code":"STRUCTURE_NOT_FOUND","message":"Aucune structure active avec l'identifiant 9999",` | OK |
| T4 | Paramètre invalide page=-1 | 400 + VALIDATION_ERROR | `400 {"code":"VALIDATION_ERROR","message":"Paramètres de requête invalides","details":[{"field"` | OK |
| T5 | Jeton absent | 401 + 900902 | `401 {"code":"900902","message":"Missing Credentials","description":"Invalid Credentials. Make` | OK |
| T6 | Jeton invalide | 401 + 900901 | `401 {"code":"900901","message":"Invalid Credentials","description":"Access failure for API: /s` | OK |
| T7 | Application non abonnée | 403 + 900908 | `403 {"code":"900908","message":"Resource forbidden ","description":"User is NOT authorized to` | OK |
| T7b | Souscription bloquée | 401 + 900907 | `401 {"code":"900907","message":"The requested API is temporarily blocked","description":"User` | OK |
| T9 | API bloquée (retrait de publication) | 503 + 700700 | `503 {"code":"700700","type":"API blocked","description":"This API has been blocked temporarily` | OK |
| T9b | Backend toujours en marche pendant le blocage | 200 | `200 {"status":"UP","database":"UP"}` | OK |
| T12 | Republication | 200 | `200 {"page":1,"size":10,"total":77,"totalPages":8,"items":[{"id":1,"code":"CSPS-0001","nom":"C` | OK |
| T10 | Arrêt technique (backend coupé) | 5xx + 101503 | `500 {"code":"101503","type":"Status report","message":"Runtime Error","description":"Error con` | OK |
| T10b | Retour à la normale après redémarrage | 200 | `200 {"page":1,"size":10,"total":77,"totalPages":8,"items":[{"id":1,"code":"CSPS-0001","nom":"C` | OK |
| T11 | v2 avec champs supplémentaires | 200 | `200 {"id":1,"code":"CSPS-0001","nom":"CSPS Kalgondé de Ouagadougou","type":"CSPS","statut":"PU` | OK |
| T11b | v1 dépréciée répond toujours | 200 | `200 {"id":1,"code":"CSPS-0001","nom":"CSPS Kalgondé de Ouagadougou","type":"CSPS","statut":"PU` | OK |
| T8 | Dépassement du quota (rejet au 13e appel) | 429 + 900804 | `429 {"code":"900804","message":"Message throttled out","description":"You have exceeded your q` | OK |
