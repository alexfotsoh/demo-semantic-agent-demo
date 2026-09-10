"""
Générateur du jeu de données "facturation énergie".

Produit trois tables (contrats, releves, factures, lignes_facture) contenant
délibérément les cas qui mettent un agent en difficulté :

  A. Facturation sur estimation puis régularisation semestrielle
     -> l'écart entre date d'émission et période couverte
  B. Avoirs émis plusieurs mois après la facture d'origine
  C. Changement d'offre en cours d'année (deux contrats, même client)
  D. Résiliation en cours de mois avec prorata
  E. Contrats internes / de test à exclure du CA
  F. Relevés mêlant réel et estimé, sans que la métrique le dise
  G. Clients en sur-consommation par rapport à leur estimation annuelle

Déterministe : SEED fixe. Rejouable à l'identique.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20260909
random.seed(SEED)

OUT = Path("/mnt/user-data/outputs/dataset")
OUT.mkdir(parents=True, exist_ok=True)

DEBUT = date(2024, 1, 1)
FIN = date(2025, 12, 31)

# ---------------------------------------------------------------- paramètres

OFFRES = {
    "BASE":  {"abo_mensuel": 13.20, "prix_kwh": 0.2016, "part": 0.40},
    "HPHC":  {"abo_mensuel": 14.60, "prix_kwh": 0.1950, "part": 0.25},
    "VERTE": {"abo_mensuel": 15.90, "prix_kwh": 0.2180, "part": 0.20},
    "PRO":   {"abo_mensuel": 42.00, "prix_kwh": 0.1870, "part": 0.15},
}

REGIONS = [
    "Auvergne-Rhône-Alpes", "Bretagne", "Grand Est", "Hauts-de-France",
    "Île-de-France", "Normandie", "Nouvelle-Aquitaine", "Occitanie",
    "Pays de la Loire", "Provence-Alpes-Côte d'Azur",
]

# Profil de consommation mensuel (part de la conso annuelle) : creux l'été.
SAISON = [0.128, 0.118, 0.101, 0.078, 0.058, 0.044,
          0.040, 0.042, 0.056, 0.079, 0.106, 0.150]

N_CLIENTS = 320
TVA = 0.20

# Proportions des cas piégeux
P_ESTIME = 0.35      # contrats facturés sur estimation puis régularisés (cas A)
P_AVOIR = 0.06       # factures donnant lieu à un avoir tardif (cas B)
P_CHANGE_OFFRE = 0.15  # clients changeant d'offre en cours de période (cas C)
P_RESILIE = 0.12     # contrats résiliés en cours de période (cas D)
N_INTERNES = 9       # contrats internes / de test (cas E)
P_SURCONSO = 0.18    # contrats en sur-consommation nette (cas G)


def fin_de_mois(d: date) -> date:
    if d.month == 12:
        return date(d.year, 12, 31)
    return date(d.year, d.month + 1, 1) - timedelta(days=1)


def mois_entre(debut: date, fin: date):
    """Itère sur les 1ers de mois entre deux dates incluses."""
    cur = date(debut.year, debut.month, 1)
    while cur <= fin:
        yield cur
        cur = date(cur.year + 1, 1, 1) if cur.month == 12 else date(cur.year, cur.month + 1, 1)


def tirer_offre() -> str:
    r = random.random()
    cum = 0.0
    for code, cfg in OFFRES.items():
        cum += cfg["part"]
        if r <= cum:
            return code
    return "BASE"


def conso_annuelle(offre: str) -> int:
    if offre == "PRO":
        return random.randint(18000, 96000)
    return random.randint(1900, 7400)


# ---------------------------------------------------------------- contrats

contrats = []
compteur_contrat = 0


def nouveau_contrat(customer_id, offre, debut, fin_contrat, interne=False):
    global compteur_contrat
    compteur_contrat += 1
    annuel = conso_annuelle(offre)
    # Cas G : l'estimation contractuelle est volontairement basse pour une part
    # des contrats, ce qui produit une sur-consommation réelle constatée.
    if random.random() < P_SURCONSO:
        estimation = int(annuel * random.uniform(0.62, 0.82))
    else:
        estimation = int(annuel * random.uniform(0.94, 1.10))
    c = {
        "contract_id": f"CTR{compteur_contrat:05d}",
        "customer_id": customer_id,
        "offer_code": offre,
        "region": random.choice(REGIONS),
        "start_date": debut,
        "end_date": fin_contrat,
        "estimated_annual_kwh": estimation,
        "real_annual_kwh": annuel,          # non exporté : sert à générer les relevés
        "is_internal": interne,
        # Cas A : facturation sur estimation, régularisée en juillet et janvier
        "facture_sur_estimation": random.random() < P_ESTIME,
    }
    contrats.append(c)
    return c


for i in range(1, N_CLIENTS + 1):
    customer_id = f"CLI{i:05d}"
    offre = tirer_offre()

    # ancienneté variable : une partie des contrats démarre en cours de période
    if random.random() < 0.22:
        debut = DEBUT + timedelta(days=random.randint(15, 500))
        debut = date(debut.year, debut.month, random.randint(1, 28))
    else:
        debut = DEBUT

    if random.random() < P_CHANGE_OFFRE:
        # Cas C : changement d'offre -> deux contrats successifs, même client
        bascule = date(random.choice([2024, 2025]), random.randint(3, 10), 1)
        if bascule <= debut:
            bascule = debut + timedelta(days=200)
        nouveau_contrat(customer_id, offre, debut, bascule - timedelta(days=1))
        nouvelle_offre = random.choice([o for o in OFFRES if o != offre])
        nouveau_contrat(customer_id, nouvelle_offre, bascule, None)
    elif random.random() < P_RESILIE:
        # Cas D : résiliation en cours de mois -> prorata d'abonnement
        fin_c = date(random.choice([2024, 2025]), random.randint(2, 11), random.randint(6, 26))
        if fin_c <= debut:
            fin_c = debut + timedelta(days=120)
        nouveau_contrat(customer_id, offre, debut, fin_c)
    else:
        nouveau_contrat(customer_id, offre, debut, None)

# Cas E : contrats internes, indiscernables sans le drapeau
for j in range(N_INTERNES):
    nouveau_contrat(f"INT{j+1:05d}", tirer_offre(), DEBUT, None, interne=True)


# ---------------------------------------------------------------- relevés

releves = []
compteur_releve = 0
conso_par_contrat_mois = {}

for c in contrats:
    debut_c = c["start_date"]
    fin_c = c["end_date"] or FIN
    for m in mois_entre(debut_c, min(fin_c, FIN)):
        part = SAISON[m.month - 1]
        base = c["real_annual_kwh"] * part
        kwh = base * random.uniform(0.88, 1.14)

        # prorata sur le mois d'entrée et le mois de sortie
        dernier = fin_de_mois(m)
        jours_mois = dernier.day
        d1 = max(m, debut_c)
        d2 = min(dernier, fin_c)
        jours_couverts = (d2 - d1).days + 1
        if jours_couverts < jours_mois:
            kwh *= jours_couverts / jours_mois

        kwh = round(max(kwh, 0), 1)
        conso_par_contrat_mois[(c["contract_id"], m)] = (kwh, jours_couverts, jours_mois)

        # Cas F : le type de relevé mélange réel et estimé.
        # Les contrats "facturés sur estimation" ont une majorité d'estimés,
        # avec un relevé réel semestriel (juin et décembre).
        if c["facture_sur_estimation"]:
            type_releve = "REEL" if m.month in (6, 12) else "ESTIME"
        else:
            type_releve = "ESTIME" if random.random() < 0.18 else "REEL"

        compteur_releve += 1
        releves.append({
            "reading_id": f"REL{compteur_releve:07d}",
            "contract_id": c["contract_id"],
            "reading_date": dernier.isoformat(),
            "period_start": d1.isoformat(),
            "period_end": d2.isoformat(),
            "kwh": kwh,
            "reading_type": type_releve,
        })


# ---------------------------------------------------------------- factures

factures = []
lignes = []
compteur_facture = 0
compteur_ligne = 0


def ajouter_facture(contrat, type_facture, emission, p_start, p_end,
                    postes, facture_liee=None):
    """postes : liste de (line_type, kwh, unit_price, amount_ht)"""
    global compteur_facture, compteur_ligne
    compteur_facture += 1
    invoice_id = f"FAC{compteur_facture:07d}"
    montant_ht = round(sum(p[3] for p in postes), 2)
    tva = round(montant_ht * TVA, 2)
    factures.append({
        "invoice_id": invoice_id,
        "contract_id": contrat["contract_id"],
        "invoice_type": type_facture,
        "issue_date": emission.isoformat(),
        "period_start": p_start.isoformat(),
        "period_end": p_end.isoformat(),
        "amount_ht": montant_ht,
        "vat_amount": tva,
        "amount_ttc": round(montant_ht + tva, 2),
        "related_invoice_id": facture_liee or "",
    })
    for line_type, kwh, pu, montant in postes:
        compteur_ligne += 1
        lignes.append({
            "line_id": f"LIG{compteur_ligne:08d}",
            "invoice_id": invoice_id,
            "line_type": line_type,
            "kwh": round(kwh, 1) if kwh is not None else "",
            "unit_price": round(pu, 4) if pu is not None else "",
            "amount_ht": round(montant, 2),
        })
    return invoice_id


# on mémorise ce qui a été facturé sur estimation, pour régulariser ensuite
a_regulariser = {}   # (contract_id, annee, semestre) -> [(mois, kwh_facture, kwh_reel)]

for c in contrats:
    cfg = OFFRES[c["offer_code"]]
    debut_c = c["start_date"]
    fin_c = c["end_date"] or FIN

    for m in mois_entre(debut_c, min(fin_c, FIN)):
        cle = (c["contract_id"], m)
        if cle not in conso_par_contrat_mois:
            continue
        kwh_reel, jours_couverts, jours_mois = conso_par_contrat_mois[cle]
        dernier = fin_de_mois(m)
        p_start = max(m, debut_c)
        p_end = min(dernier, fin_c)

        # Cas A : les contrats sur estimation sont facturés au douzième de
        # l'estimation contractuelle, et non sur la consommation réelle.
        if c["facture_sur_estimation"]:
            kwh_facture = c["estimated_annual_kwh"] * SAISON[m.month - 1]
            kwh_facture *= jours_couverts / jours_mois
            semestre = 1 if m.month <= 6 else 2
            a_regulariser.setdefault((c["contract_id"], m.year, semestre), []).append(
                (m, kwh_facture, kwh_reel)
            )
        else:
            kwh_facture = kwh_reel

        # Cas D : prorata de l'abonnement sur mois partiel
        abo = cfg["abo_mensuel"] * jours_couverts / jours_mois
        postes = [
            ("ABONNEMENT", None, None, abo),
            ("CONSO", kwh_facture, cfg["prix_kwh"], kwh_facture * cfg["prix_kwh"]),
        ]
        # remise commerciale occasionnelle
        if random.random() < 0.07:
            base = abo + kwh_facture * cfg["prix_kwh"]
            postes.append(("REMISE", None, None, -round(base * random.uniform(0.05, 0.15), 2)))

        emission = dernier + timedelta(days=random.randint(2, 6))
        fid = ajouter_facture(c, "NORMALE", emission, p_start, p_end, postes)

        # Cas B : avoir émis 1 à 4 mois après la facture d'origine,
        # rattaché à la période de la facture initiale.
        if random.random() < P_AVOIR:
            decalage = random.randint(35, 130)
            montant = -round(sum(p[3] for p in postes) * random.uniform(0.12, 0.55), 2)
            ajouter_facture(
                c, "AVOIR", emission + timedelta(days=decalage),
                p_start, p_end,
                [("AVOIR", None, None, montant)],
                facture_liee=fid,
            )

# Cas A (suite) : régularisations semestrielles.
# Émises en juillet (S1) et en janvier de l'année suivante (S2),
# mais portant sur une période antérieure.
for (contract_id, annee, semestre), postes_mois in a_regulariser.items():
    contrat = next(c for c in contrats if c["contract_id"] == contract_id)
    cfg = OFFRES[contrat["offer_code"]]
    ecart_kwh = sum(reel - facture for _, facture, reel in postes_mois)
    if abs(ecart_kwh) < 1:
        continue
    if semestre == 1:
        emission = date(annee, 7, random.randint(8, 20))
        p_start, p_end = date(annee, 1, 1), date(annee, 6, 30)
    else:
        emission = date(annee + 1, 1, random.randint(8, 20))
        p_start, p_end = date(annee, 7, 1), date(annee, 12, 31)
    if emission > FIN + timedelta(days=40):
        continue
    p_start = max(p_start, contrat["start_date"])
    p_end = min(p_end, contrat["end_date"] or FIN)
    if p_start > p_end:
        continue
    montant = ecart_kwh * cfg["prix_kwh"]
    ajouter_facture(
        contrat, "REGULARISATION", emission, p_start, p_end,
        [("CONSO", ecart_kwh, cfg["prix_kwh"], montant)],
    )


# ---------------------------------------------------------------- export

def ecrire(nom, rows, colonnes):
    chemin = OUT / f"{nom}.csv"
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return chemin


for c in contrats:
    c["start_date"] = c["start_date"].isoformat()
    c["end_date"] = c["end_date"].isoformat() if c["end_date"] else ""
    c["is_internal"] = "true" if c["is_internal"] else "false"

ecrire("contrats", contrats, [
    "contract_id", "customer_id", "offer_code", "region",
    "start_date", "end_date", "estimated_annual_kwh", "is_internal",
])
ecrire("releves", releves, [
    "reading_id", "contract_id", "reading_date",
    "period_start", "period_end", "kwh", "reading_type",
])
ecrire("factures", factures, [
    "invoice_id", "contract_id", "invoice_type", "issue_date",
    "period_start", "period_end", "amount_ht", "vat_amount",
    "amount_ttc", "related_invoice_id",
])
ecrire("lignes_facture", lignes, [
    "line_id", "invoice_id", "line_type", "kwh", "unit_price", "amount_ht",
])

print(f"contrats        : {len(contrats)}")
print(f"relevés         : {len(releves)}")
print(f"factures        : {len(factures)}")
print(f"lignes          : {len(lignes)}")
