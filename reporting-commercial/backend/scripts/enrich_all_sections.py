# -*- coding: utf-8 -*-
"""
Enrichissement de toutes les sections avec Pivots et Dashboards existants.
Ordre de traitement :
  1. Tableau de Bord        (1180)
  2. Chiffre d'Affaires     (1185)
  3. Marges & Rentabilite   (1202)
  4. Analyse Clients        (1210)
  5. Documents Commerciaux  (1196)
  6. Tendances Saisonnalite (1230)
  7. Recouvrement Tresorerie(1237)
  8. Stock Approvisionnement(1246)
  9. Achats Fournisseurs    (1257)
 10. Service Logistique     (1268)
"""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# ── Utilitaire ────────────────────────────────────────────────────────────
def next_ordre(parent_id):
    r = execute_central(f"SELECT ISNULL(MAX(ordre),0)+1 AS n FROM APP_Menus WHERE parent_id={parent_id}")
    return r[0]['n']

def already_in(parent_id, typ, target_id):
    r = execute_central(
        f"SELECT COUNT(1) AS n FROM APP_Menus WHERE parent_id={parent_id} AND type='{typ}' AND target_id={target_id}"
    )
    return r[0]['n'] > 0

def add_item(parent_id, nom, typ, target_id, code, ordre=None):
    if already_in(parent_id, typ, target_id):
        return False
    o = ordre if ordre is not None else next_ordre(parent_id)
    nom_sql = nom.replace("'", "''")
    execute_central(f"""
        INSERT INTO APP_Menus (nom, type, target_id, parent_id, ordre, code, actif)
        VALUES ('{nom_sql}', '{typ}', {target_id}, {parent_id}, {o}, '{code}', 1)
    """)
    return True

inserted = 0

# ══════════════════════════════════════════════════════════════════════════
# 1. TABLEAU DE BORD (1180)
# ══════════════════════════════════════════════════════════════════════════
print("\n[1] TABLEAU DE BORD (1180)")
sec = 1180

plan = [
    # (nom,                               type,        target_id, code)
    ("Tableau de Bord Global",            "dashboard", 6,   "TB_DB_GLOBAL"),
    ("Comparatif N / N-1",               "dashboard", 10,  "TB_DB_COMPARATIF"),
    ("TB Direction Generale",             "dashboard", 170, "TB_DB_DG"),
    ("Vue Commerciale",                   "dashboard", 166, "TB_DB_COMMERCIALE"),
    ("Comparatif N/N-1/N-2 (Pivot)",     "pivot",     119, "TB_PV_COMP3ANS"),
    ("Evolution CA 12 mois (Pivot)",      "pivot",     120, "TB_PV_EVOL12M"),
    ("Synthese Mensuelle Direction",      "pivot",     121, "TB_PV_SYNTHESE_DIR"),
]
for nom, typ, tid, code in plan:
    ok = add_item(sec, nom, typ, tid, code)
    if ok: print(f"  + {nom}"); inserted += 1
    else:  print(f"  . {nom} (existe)")

# ══════════════════════════════════════════════════════════════════════════
# 2. CHIFFRE D'AFFAIRES (1185)
# ══════════════════════════════════════════════════════════════════════════
print("\n[2] CHIFFRE D'AFFAIRES (1185)")
sec = 1185

plan = [
    ("CA par Periode (Pivot)",            "pivot",     124, "CA_PV_PERIODE"),
    ("CA par Client (Pivot)",             "pivot",     125, "CA_PV_CLIENT"),
    ("CA par Article (Pivot)",            "pivot",     126, "CA_PV_ARTICLE"),
    ("CA par Famille (Pivot)",            "pivot",     127, "CA_PV_FAMILLE"),
    ("CA par Region / Ville (Pivot)",     "pivot",     129, "CA_PV_REGION"),
    ("CA par Depot (Pivot)",              "pivot",     130, "CA_PV_DEPOT"),
    ("CA par Affaire (Pivot)",            "pivot",     131, "CA_PV_AFFAIRE"),
    ("Evolution CA Mensuelle",            "dashboard", 7,   "CA_DB_EVOL"),
    ("Comparatif N / N-1",               "dashboard", 10,  "CA_DB_COMP"),
]
for nom, typ, tid, code in plan:
    ok = add_item(sec, nom, typ, tid, code)
    if ok: print(f"  + {nom}"); inserted += 1
    else:  print(f"  . {nom} (existe)")

# ══════════════════════════════════════════════════════════════════════════
# 3. MARGES & RENTABILITE (1202)
# ══════════════════════════════════════════════════════════════════════════
print("\n[3] MARGES & RENTABILITE (1202)")
sec = 1202

plan = [
    ("Analyse Marges (Pivot)",            "pivot",     8,   "MRG_PV_MARGES"),
    ("Rentabilite par Client (Pivot)",    "pivot",     13,  "MRG_PV_RENT_CLIENT"),
    ("Marge par Ligne (Pivot)",           "pivot",     134, "MRG_PV_MARGE_LIGNE"),
    ("Rentabilite Mensuelle (Pivot)",     "pivot",     117, "MRG_PV_RENT_MENS"),
    ("Rentabilite Annuelle (Pivot)",      "pivot",     118, "MRG_PV_RENT_ANN"),
    ("Vue Commerciale - CA & Marge",      "dashboard", 166, "MRG_DB_VUE_COM"),
    ("TB Direction Generale",             "dashboard", 170, "MRG_DB_DG"),
]
for nom, typ, tid, code in plan:
    ok = add_item(sec, nom, typ, tid, code)
    if ok: print(f"  + {nom}"); inserted += 1
    else:  print(f"  . {nom} (existe)")

# ══════════════════════════════════════════════════════════════════════════
# 4. ANALYSE CLIENTS (1210)
# ══════════════════════════════════════════════════════════════════════════
print("\n[4] ANALYSE CLIENTS (1210)")
sec = 1210

plan = [
    ("CA par Client (Pivot)",             "pivot",     3,   "CLI_PV_CA_CLIENT"),
    ("CA par Client v2 (Pivot)",          "pivot",     125, "CLI_PV_CA_CLIENT2"),
    ("Panier Moyen Client (Pivot)",       "pivot",     11,  "CLI_PV_PANIER"),
    ("Analyse ABC Clients (Pivot)",       "pivot",     132, "CLI_PV_ABC"),
    ("Comparatif N/N-1 Client (Pivot)",   "pivot",     133, "CLI_PV_COMP"),
    ("Segmentation RFM (Pivot)",          "pivot",     135, "CLI_PV_RFM"),
    ("Fidelite Clients (Pivot)",          "pivot",     139, "CLI_PV_FIDELITE"),
    ("Analyse RFM Clients",               "dashboard", 11,  "CLI_DB_RFM"),
    ("Clients a Risque de Churn",         "dashboard", 12,  "CLI_DB_CHURN"),
    ("Fidelite Clients",                  "dashboard", 15,  "CLI_DB_FIDELITE"),
    ("Top 20 Clients",                    "dashboard", 8,   "CLI_DB_TOP20"),
]
for nom, typ, tid, code in plan:
    ok = add_item(sec, nom, typ, tid, code)
    if ok: print(f"  + {nom}"); inserted += 1
    else:  print(f"  . {nom} (existe)")

# ══════════════════════════════════════════════════════════════════════════
# 5. DOCUMENTS COMMERCIAUX (1196)
# ══════════════════════════════════════════════════════════════════════════
print("\n[5] DOCUMENTS COMMERCIAUX (1196)")
sec = 1196

plan = [
    ("Performance des Devis",             "dashboard", 16,  "DOC_DB_DEVIS"),
    ("Analyse des Retours",               "dashboard", 14,  "DOC_DB_RETOURS"),
]
for nom, typ, tid, code in plan:
    ok = add_item(sec, nom, typ, tid, code)
    if ok: print(f"  + {nom}"); inserted += 1
    else:  print(f"  . {nom} (existe)")

# ══════════════════════════════════════════════════════════════════════════
# 6. TENDANCES & SAISONNALITE (1230)
# ══════════════════════════════════════════════════════════════════════════
print("\n[6] TENDANCES & SAISONNALITE (1230)")
sec = 1230

plan = [
    ("Saisonnalite des Ventes (Pivot)",   "pivot",     14,  "TND_PV_SAISON"),
    ("Saisonnalite CA (Pivot)",           "pivot",     136, "TND_PV_SAISON_CA"),
    ("Saisonnalite des Ventes",           "dashboard", 17,  "TND_DB_SAISON"),
    ("Comparatif N / N-1",               "dashboard", 10,  "TND_DB_COMP"),
]
for nom, typ, tid, code in plan:
    ok = add_item(sec, nom, typ, tid, code)
    if ok: print(f"  + {nom}"); inserted += 1
    else:  print(f"  . {nom} (existe)")

# ══════════════════════════════════════════════════════════════════════════
# 7. RECOUVREMENT & TRESORERIE (1237)
# ══════════════════════════════════════════════════════════════════════════
print("\n[7] RECOUVREMENT & TRESORERIE (1237)")
sec = 1237

plan = [
    ("Creances par Tranche Age (Pivot)",  "pivot",     105, "REC_PV_BALANCE_AGEE"),
    ("Reglements par Mode (Pivot)",       "pivot",     106, "REC_PV_MODE_REGL"),
    ("Evolution Mensuelle (Pivot)",       "pivot",     108, "REC_PV_EVOL"),
    ("Taux Recouvrement Client (Pivot)",  "pivot",     109, "REC_PV_TAUX"),
    ("Reglements par Tiers (Pivot)",      "pivot",     110, "REC_PV_TIERS"),
    ("TB Recouvrement Global",            "dashboard", 155, "REC_DB_GLOBAL"),
    ("Evolution Mensuelle Recouvrement",  "dashboard", 156, "REC_DB_EVOL"),
    ("Top 20 Debiteurs",                  "dashboard", 158, "REC_DB_TOP20"),
    ("Niveau de Risque Clients",          "dashboard", 161, "REC_DB_RISQUE"),
    ("Synthese Annuelle Recouvrement",    "dashboard", 163, "REC_DB_SYNTHESE"),
]
for nom, typ, tid, code in plan:
    ok = add_item(sec, nom, typ, tid, code)
    if ok: print(f"  + {nom}"); inserted += 1
    else:  print(f"  . {nom} (existe)")

# ══════════════════════════════════════════════════════════════════════════
# 8. STOCK & APPROVISIONNEMENT (1246)
# ══════════════════════════════════════════════════════════════════════════
print("\n[8] STOCK & APPROVISIONNEMENT (1246)")
sec = 1246

plan = [
    ("Valorisation Stock (Pivot)",        "pivot",     148, "STK_PV_VALORI"),
    ("Rotation Stock (Pivot)",            "pivot",     149, "STK_PV_ROTATION"),
    ("ABC Stock (Pivot)",                 "pivot",     150, "STK_PV_ABC"),
    ("Stock par Depot (Pivot)",           "pivot",     151, "STK_PV_DEPOT"),
    ("Evolution Mouvements (Pivot)",      "pivot",     152, "STK_PV_EVOL"),
    ("Matrice ABC/XYZ (Pivot)",           "pivot",     153, "STK_PV_ABC_XYZ"),
    ("Couverture Stock Jours (Pivot)",    "pivot",     154, "STK_PV_COUVERTURE"),
    ("Cout Possession Stock (Pivot)",     "pivot",     155, "STK_PV_COUT"),
    ("Rotation des Stocks",               "dashboard", 27,  "STK_DB_ROTATION"),
    ("Analyse ABC Stock",                 "dashboard", 29,  "STK_DB_ABC"),
    ("Couverture de Stock",               "dashboard", 30,  "STK_DB_COUVERTURE"),
    ("Classification ABC/XYZ",            "dashboard", 31,  "STK_DB_ABC_XYZ"),
    ("Prevision de Rupture",              "dashboard", 32,  "STK_DB_RUPTURE"),
    ("Cout de Possession du Stock",       "dashboard", 33,  "STK_DB_COUT"),
    ("Evolution Stock Mensuelle",         "dashboard", 28,  "STK_DB_EVOL"),
]
for nom, typ, tid, code in plan:
    ok = add_item(sec, nom, typ, tid, code)
    if ok: print(f"  + {nom}"); inserted += 1
    else:  print(f"  . {nom} (existe)")

# ══════════════════════════════════════════════════════════════════════════
# 9. ACHATS & FOURNISSEURS (1257)
# ══════════════════════════════════════════════════════════════════════════
print("\n[9] ACHATS & FOURNISSEURS (1257)")
sec = 1257

plan = [
    ("Achats par Fournisseur (Pivot)",    "pivot",     141, "ACH_PV_FOURN"),
    ("Achats par Periode (Pivot)",        "pivot",     142, "ACH_PV_PERIODE"),
    ("Achats par Article (Pivot)",        "pivot",     143, "ACH_PV_ARTICLE"),
    ("Achats par Famille (Pivot)",        "pivot",     144, "ACH_PV_FAMILLE"),
    ("ABC Fournisseurs (Pivot)",          "pivot",     145, "ACH_PV_ABC"),
    ("Evolution Prix Achat (Pivot)",      "pivot",     147, "ACH_PV_PRIX"),
    ("Evolution Achats Mensuelle",        "dashboard", 18,  "ACH_DB_EVOL"),
    ("Top 20 Fournisseurs",               "dashboard", 19,  "ACH_DB_TOP20"),
    ("Scoring Fournisseurs",              "dashboard", 21,  "ACH_DB_SCORING"),
    ("Dependance Fournisseur",            "dashboard", 22,  "ACH_DB_DEPEND"),
    ("Analyse Delais Livraison",          "dashboard", 20,  "ACH_DB_DELAI"),
]
for nom, typ, tid, code in plan:
    ok = add_item(sec, nom, typ, tid, code)
    if ok: print(f"  + {nom}"); inserted += 1
    else:  print(f"  . {nom} (existe)")

# ══════════════════════════════════════════════════════════════════════════
# 10. SERVICE & LOGISTIQUE (1268)
# ══════════════════════════════════════════════════════════════════════════
print("\n[10] SERVICE & LOGISTIQUE (1268)")
sec = 1268

plan = [
    ("Taux de Service Client",            "dashboard", 13,  "SRV_DB_TAUX_SRV"),
    ("Analyse des Retours",               "dashboard", 14,  "SRV_DB_RETOURS"),
    ("Productivite Logistique",           "dashboard", 37,  "SRV_DB_PRODUCT"),
    ("Flux de Stock par Depot",           "dashboard", 35,  "SRV_DB_FLUX"),
    ("Delai Moyen de Livraison",          "dashboard", 23,  "SRV_DB_DELAI"),
    ("Taux de Conformite Reception",      "dashboard", 24,  "SRV_DB_CONFORM"),
    ("Lead Time vs Stock Securite",       "dashboard", 36,  "SRV_DB_LEAD"),
    ("Analyse des Prix de Vente (Pivot)", "pivot",     12,  "SRV_PV_PRIX"),
]
for nom, typ, tid, code in plan:
    ok = add_item(sec, nom, typ, tid, code)
    if ok: print(f"  + {nom}"); inserted += 1
    else:  print(f"  . {nom} (existe)")

# ── Rapport final ─────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"TOTAL INSERE : {inserted} nouveaux items de menu")
print(f"{'='*65}")

print("\n=== ETAT FINAL DE TOUTES LES SECTIONS ===")
sections = execute_central("SELECT id, nom FROM APP_Menus WHERE parent_id IS NULL ORDER BY ordre")
for s in sections:
    cnt = execute_central(f"SELECT COUNT(1) AS n FROM APP_Menus WHERE parent_id={s['id']}")[0]['n']
    by_type = execute_central(f"""
        SELECT type, COUNT(1) AS n FROM APP_Menus WHERE parent_id={s['id']} GROUP BY type
    """)
    parts = [f"{r['type']}:{r['n']}" for r in by_type]
    print(f"  [{s['id']}] {s['nom']:30} total={cnt:3}  ({', '.join(parts)})")
