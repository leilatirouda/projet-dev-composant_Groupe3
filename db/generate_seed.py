"""Génère db/seed.sql : 80 structures sanitaires FICTIVES.

Les noms, téléphones et coordonnées sont inventés. Le tirage est
déterministe (graine fixe) : relancer le script donne le même fichier.

Usage : python db/generate_seed.py
"""
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(2026)

# Découpage simplifié (région -> [(province, district, commune, lat, lon)])
ZONES = {
    "Centre": [("Kadiogo", "District de Baskuy", "Ouagadougou", 12.37, -1.52),
               ("Kadiogo", "District de Bogodogo", "Ouagadougou", 12.33, -1.47),
               ("Kadiogo", "District de Nongr-Massom", "Ouagadougou", 12.40, -1.49),
               ("Kadiogo", "District de Sig-Noghin", "Ouagadougou", 12.39, -1.56)],
    "Hauts-Bassins": [("Houet", "District de Dô", "Bobo-Dioulasso", 11.18, -4.29),
                      ("Houet", "District de Dafra", "Bobo-Dioulasso", 11.15, -4.31),
                      ("Kénédougou", "District de Orodara", "Orodara", 10.97, -4.91)],
    "Centre-Ouest": [("Boulkiemdé", "District de Koudougou", "Koudougou", 12.25, -2.36),
                     ("Sanguié", "District de Réo", "Réo", 12.32, -2.47)],
    "Nord": [("Yatenga", "District de Ouahigouya", "Ouahigouya", 13.58, -2.42),
             ("Passoré", "District de Yako", "Yako", 12.96, -2.26)],
    "Est": [("Gourma", "District de Fada N'Gourma", "Fada N'Gourma", 12.06, 0.36)],
    "Centre-Est": [("Boulgou", "District de Tenkodogo", "Tenkodogo", 11.78, -0.37)],
    "Boucle du Mouhoun": [("Mouhoun", "District de Dédougou", "Dédougou", 12.46, -3.46)],
    "Cascades": [("Comoé", "District de Banfora", "Banfora", 10.63, -4.76)],
    "Sud-Ouest": [("Poni", "District de Gaoua", "Gaoua", 10.33, -3.18)],
    "Plateau-Central": [("Oubritenga", "District de Ziniaré", "Ziniaré", 12.58, -1.30)],
}

TYPES = [("CSPS", 34), ("CM", 10), ("CMA", 10), ("DISPENSAIRE", 6), ("MATERNITE", 6),
         ("CLINIQUE", 8), ("CHR", 4), ("CHU", 2)]
LITS = {"CSPS": (4, 12), "CM": (10, 25), "CMA": (30, 80), "DISPENSAIRE": (2, 6),
        "MATERNITE": (8, 20), "CLINIQUE": (10, 40), "CHR": (120, 250), "CHU": (300, 600)}
SERVICES = {
    "CSPS": ["consultation", "vaccination", "maternite", "pharmacie"],
    "CM": ["consultation", "laboratoire", "maternite", "pharmacie"],
    "CMA": ["consultation", "chirurgie", "laboratoire", "radiologie", "maternite", "urgences"],
    "DISPENSAIRE": ["consultation", "soins infirmiers"],
    "MATERNITE": ["maternite", "planification familiale", "vaccination"],
    "CLINIQUE": ["consultation", "laboratoire", "radiologie", "chirurgie"],
    "CHR": ["urgences", "chirurgie", "pediatrie", "laboratoire", "radiologie", "maternite"],
    "CHU": ["urgences", "chirurgie", "pediatrie", "cardiologie", "laboratoire", "radiologie", "reanimation"],
}
NOMS = ["Wend-Panga", "Song-Taaba", "Nabonswendé", "Kamsaoghin", "Lafi Baoré", "Tanghin",
        "Zangouettin", "Pissy", "Somgandé", "Dassasgho", "Kalgondé", "Belle-Ville",
        "Sainte-Famille", "Espérance", "Bon Samaritain", "Saint-Camille", "Yennenga",
        "Laafi", "Nonsin", "Paspanga", "Koulouba", "Gounghin", "Sarfalao", "Accart-Ville",
        "Lafiabougou", "Kua", "Colsama", "Secteur 22", "Sinyiri", "Wayalghin"]
STATUT_PAR_TYPE = {"CLINIQUE": ["PRIVE"], "DISPENSAIRE": ["CONFESSIONNEL", "COMMUNAUTAIRE"],
                   "MATERNITE": ["PUBLIC", "CONFESSIONNEL"]}
LIBELLE = {"CSPS": "CSPS", "CM": "Centre médical", "CMA": "CMA", "DISPENSAIRE": "Dispensaire",
           "MATERNITE": "Maternité", "CLINIQUE": "Clinique", "CHR": "CHR", "CHU": "CHU"}


def q(v):
    """Échappe une valeur pour SQL."""
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def main():
    zones = [(r, *z) for r, lst in ZONES.items() for z in lst]
    lignes, compteurs, noms_pris = [], {}, set()
    for t, nb in TYPES:
        for _ in range(nb):
            region, prov, dist, commune, lat, lon = random.choice(zones)
            if t == "CHU":
                region, prov, dist, commune, lat, lon = zones[0] if not compteurs.get("CHU") else zones[4]
            compteurs[t] = compteurs.get(t, 0) + 1
            code = f"{t[:4]}-{compteurs[t]:04d}"
            base = random.choice(NOMS)
            nom = f"{LIBELLE[t]} {base} de {commune}"
            while nom in noms_pris:
                nom = f"{LIBELLE[t]} {random.choice(NOMS)} de {commune}"
            noms_pris.add(nom)
            statut = random.choice(STATUT_PAR_TYPE.get(t, ["PUBLIC"]))
            lits = random.randint(*LITS[t])
            services = sorted(random.sample(SERVICES[t], k=max(2, len(SERVICES[t]) - random.randint(0, 2))))
            tel = f"+226 25 {random.randint(30, 49)} {random.randint(10, 99)} {random.randint(10, 99)}"
            ouverture = date(1965, 1, 1) + timedelta(days=random.randint(0, 21000))
            lignes.append(
                "(" + ", ".join([
                    q(code), q(nom), q(t), q(statut), q(region), q(prov), q(dist), q(commune),
                    q(f"Secteur {random.randint(1, 30)}, {commune}"), q(tel),
                    q(f"contact.{code.lower()}@sante-fictive.bf"), q(lits),
                    "ARRAY[" + ", ".join(q(s) for s in services) + "]::TEXT[]",
                    q(round(lat + random.uniform(-0.05, 0.05), 6)),
                    q(round(lon + random.uniform(-0.05, 0.05), 6)),
                    q(ouverture.isoformat()),
                    "FALSE" if random.random() < 0.05 else "TRUE",
                ]) + ")"
            )
    sql = (
        "-- Données FICTIVES générées par db/generate_seed.py (ne pas modifier à la main)\n"
        "INSERT INTO structures_sanitaires\n"
        "  (code, nom, type, statut, region, province, district, commune, adresse, telephone,\n"
        "   email, capacite_lits, services, latitude, longitude, date_ouverture, actif)\nVALUES\n  "
        + ",\n  ".join(lignes)
        + "\nON CONFLICT (code) DO NOTHING;\n"
    )
    out = Path(__file__).with_name("seed.sql")
    out.write_text(sql, encoding="utf-8")
    print(f"{len(lignes)} structures écrites dans {out}")


if __name__ == "__main__":
    main()
