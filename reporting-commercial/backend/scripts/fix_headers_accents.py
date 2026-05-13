# -*- coding: utf-8 -*-
"""
Corrige les accents manquants dans les headers de columns_config des GridViews.
Ne touche PAS aux 'field' (alias SQL) — uniquement les 'header' (affichage UI).
"""
import pyodbc
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

# =====================================================================
#  TABLE DE CORRESPONDANCE : header sans accent → header avec accent
#  On corrige aussi les N° manquants, les é/è/ê/ô/û/ç
# =====================================================================
HEADER_FIXES = {
    # --- Société ---
    "Societe": "Société",
    # --- Quantité ---
    "Quantite": "Quantité",
    "Qte": "Qté",
    "Qte BC": "Qté BC",
    "Qte BL": "Qté BL",
    "Qte PL": "Qté PL",
    "Qte Cmd": "Qté Cmd",
    "Qte Livree": "Qté Livrée",
    "Qte Commandee": "Qté Commandée",
    "Qte Reservee": "Qté Réservée",
    "Qte Vendue": "Qté Vendue",
    "Qte Stock": "Qté Stock",
    "Qte Min": "Qté Min",
    "Qte Max": "Qté Max",
    "Qte Totale": "Qté Totale",
    "Qte Moy/Trans": "Qté Moy/Trans",
    "Qte a Commander": "Qté à Commander",
    "Qte Retour": "Qté Retour",
    "Qte Sortie Periode": "Qté Sortie Période",
    # --- Année ---
    "Annee": "Année",
    # --- Période ---
    "Periode": "Période",
    # --- Désignation ---
    "Designation": "Désignation",
    # --- Dépôt ---
    "Depot": "Dépôt",
    "Depot Principal": "Dépôt Principal",
    "Code Depot": "Code Dépôt",
    # --- Numéro / Pièce ---
    "Num Piece": "N° Pièce",
    "N. Piece": "N° Pièce",
    "Num BL": "N° BL",
    "N. BL": "N° BL",
    "N. BC": "N° BC",
    "N. PL": "N° PL",
    "N Facture": "N° Facture",
    "Num Serie Lot": "N° Série/Lot",
    # --- Échéance ---
    "Montant Echeance": "Montant Échéance",
    "Date Echeance": "Date Échéance",
    "Nb Echeances": "Nb Échéances",
    "Statut Reglement": "Statut Règlement",
    # --- Règlement ---
    "Mode Reglement": "Mode Règlement",
    "Mode Reglement Imp": "Mode Règlement Imp",
    "Montant Reglement": "Montant Règlement",
    "Date Reglement": "Date Règlement",
    "Nb Reglements": "Nb Règlements",
    "Montant Regle": "Montant Réglé",
    "Montant A Regler": "Montant à Régler",
    "Montant Regler": "Montant à Régler",
    "Reference": "Référence",
    "Delai Paiement Jours": "Délai Paiement Jours",
    "Delai Moyen Jours": "Délai Moyen Jours",
    "Delai Min": "Délai Min",
    "Delai Max": "Délai Max",
    "Total Paye": "Total Payé",
    "Nb Factures Impayees": "Nb Factures Impayées",
    "Montant Impaye": "Montant Impayé",
    "Plus Ancienne Echeance": "Plus Ancienne Échéance",
    "Moy Jours Retard": "Moy Jours Retard",
    "Max Jours Retard": "Max Jours Retard",
    "Jours Retard": "Jours Retard",
    "Jours Restants": "Jours Restants",
    "Tier Encaisseur": "Tiers Encaisseur",
    "Tranche Retard": "Tranche Retard",
    # --- Non Échu ---
    "Non Echu": "Non Échu",
    # --- Catégorie ---
    "Categorie Tarifaire": "Catégorie Tarifaire",
    "Cat. Comptable": "Cat. Comptable",
    # --- Région ---
    "Region": "Région",
    # --- Ancienneté ---
    "Anciennete (mois)": "Ancienneté (mois)",
    # --- Fidélité ---
    "Segment Fidelite": "Segment Fidélité",
    # --- Fréquence ---
    "Frequence": "Fréquence",
    # --- Récence ---
    "Recence (j)": "Récence (j)",
    # --- Écart ---
    "Ecart": "Écart",
    "Ecart Type": "Écart Type",
    # --- Excédent ---
    "Excedent": "Excédent",
    # --- Mouvementé / Valorisé ---
    "Mouvemente": "Mouvementé",
    "Val. CA": "Val. CA",
    # --- Coût ---
    "Cout Revient": "Coût Revient",
    "Cout Rev. Moy": "Coût Rev. Moy",
    # --- Lot/Série ---
    "Lot Serie": "Lot/Série",
    # --- Divers ---
    "1er Achat": "1er Achat",
    "1ere Vente": "1ère Vente",
    "Derniere Vente": "Dernière Vente",
    "Date Reception": "Date Réception",
    "J. Inactif": "J. Inactif",
    "J. Sans Achat": "J. Sans Achat",
    "CA Historique": "CA Historique",
    "Nb Docs Hist.": "Nb Docs Hist.",
    "Mois Actifs": "Mois Actifs",
    "Age (j)": "Âge (j)",
    "Articles Rupture": "Articles Rupture",
    "Articles Surstock": "Articles Surstock",
    "Date Cmd": "Date Cmd",
    "Reste": "Reste à Livrer",
    "Montant Facture": "Montant Facture",
    "Statut Livraison": "Statut Livraison",
    "Date BL": "Date BL",
    "Date BC": "Date BC",
    "Date PL": "Date PL",
    "Date Document": "Date Document",
    "Date": "Date",
    "Montant Stock": "Montant Stock",
    "Unite": "Unité",
    "Evol %": "Évol %",
    "Evol. %": "Évol. %",
    "Nb Documents": "Nb Documents",
    "CA 6M Prec.": "CA 6M Préc.",
    "Peremption": "Péremption",
    "Date Fabrication": "Date Fabrication",
    "Suivi Stock": "Suivi Stock",
    "Type Mouvement": "Type Mouvement",
    "Cout standard": "Coût Standard",
    "Code tiers": "Code Tiers",
    "Code article": "Code Article",
    "Code famille": "Code Famille",
    "CMUP": "CMUP",
    "Prix unitaire": "Prix Unitaire",
    "DPA Periode": "DPA Période",
    "DPA Vente": "DPA Vente",
    "DPR Vente": "DPR Vente",
    "Date Peremption": "Date Péremption",
}

conn = pyodbc.connect(CONN_STR, autocommit=True)
cursor = conn.cursor()

rows = cursor.execute(
    "SELECT id, nom, data_source_code, columns_config FROM APP_GridViews WHERE actif = 1 AND columns_config IS NOT NULL"
).fetchall()

print(f"{'=' * 70}")
print(f"  CORRECTION ACCENTS HEADERS — {len(rows)} GridViews")
print(f"{'=' * 70}")

total_fixed = 0
gv_fixed = 0

for row in rows:
    gv_id, nom, ds_code, cols_json = row
    cols = json.loads(cols_json)
    changes = []

    for col in cols:
        old_header = col.get("header", "")
        if old_header in HEADER_FIXES:
            new_header = HEADER_FIXES[old_header]
            if old_header != new_header:
                changes.append(f"{old_header} → {new_header}")
                col["header"] = new_header

    if changes:
        new_json = json.dumps(cols, ensure_ascii=False)
        cursor.execute(
            "UPDATE APP_GridViews SET columns_config = ? WHERE id = ?",
            (new_json, gv_id)
        )
        gv_fixed += 1
        total_fixed += len(changes)
        print(f"  [{gv_id}] {ds_code or '?':<35} {len(changes)} corrections:")
        for c in changes:
            print(f"        {c}")

print(f"\n{'=' * 70}")
print(f"  {total_fixed} headers corrigés dans {gv_fixed} / {len(rows)} GridViews")
print(f"{'=' * 70}")

cursor.close()
conn.close()
