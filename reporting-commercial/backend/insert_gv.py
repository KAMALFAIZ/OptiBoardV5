import pyodbc
import json

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_cltKA;UID=sa;PWD=SQL@2019;'
)
cursor = conn.cursor()

# First, check what GVs 170-172 look like in the table
print("=== Existing GVs 170-172 ===")
cursor.execute("SELECT id, nom, columns_config, features FROM APP_GridViews WHERE id IN (170,171,172)")
for r in cursor.fetchall():
    print(f"id={r[0]}, nom={r[1]}")
    print(f"  columns={r[2][:200] if r[2] else 'NULL'}")
    print(f"  features={r[3][:200] if r[3] else 'NULL'}")

# Insert missing GridViews 173-179 with IDENTITY_INSERT
features_standard = 'show_search,show_column_filters,show_grouping,show_column_toggle,show_export,show_pagination,allow_sorting'

gridviews_to_insert = [
    (173, 'Balance Tiers', 'GV_balance_tiers', 'Balance Débit/Crédit/Solde par tiers', 'DS_CPT_BALANCE_TIERS',
     json.dumps([
         {"field": "Tiers", "header": "Tiers", "format": "text", "sortable": True, "filterable": True, "width": 200},
         {"field": "Total Debit", "header": "Total Débit", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Total Credit", "header": "Total Crédit", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Solde", "header": "Solde", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Nb Ecritures", "header": "Nb Écritures", "format": "number", "sortable": True, "filterable": True, "width": 120},
     ])),
    (174, 'Ecritures de Trésorerie', 'GV_ecritures_tresorerie', 'Ecritures sur les journaux de trésorerie', 'DS_CPT_TRESORERIE',
     json.dumps([
         {"field": "Date", "header": "Date", "format": "date", "sortable": True, "filterable": True, "width": 120},
         {"field": "Journal", "header": "Journal", "format": "text", "sortable": True, "filterable": True, "width": 150},
         {"field": "Num Piece", "header": "N° Pièce", "format": "text", "sortable": True, "filterable": True, "width": 130},
         {"field": "Compte", "header": "Compte", "format": "text", "sortable": True, "filterable": True, "width": 130},
         {"field": "Intitule Compte", "header": "Intitulé Compte", "format": "text", "sortable": True, "filterable": True, "width": 200},
         {"field": "Tiers", "header": "Tiers", "format": "text", "sortable": True, "filterable": True, "width": 150},
         {"field": "Libelle", "header": "Libellé", "format": "text", "sortable": True, "filterable": True, "width": 200},
         {"field": "Mode Reglement", "header": "Mode Règlement", "format": "text", "sortable": True, "filterable": True, "width": 150},
         {"field": "Num Piece Treso", "header": "N° Pièce Tréso", "format": "text", "sortable": True, "filterable": True, "width": 150},
     ])),
    (175, 'Détail des Charges', 'GV_detail_charges', 'Détail des charges par compte', 'DS_CPT_CHARGES',
     json.dumps([
         {"field": "Compte", "header": "Compte", "format": "text", "sortable": True, "filterable": True, "width": 130},
         {"field": "Intitule Compte", "header": "Intitulé Compte", "format": "text", "sortable": True, "filterable": True, "width": 250},
         {"field": "Total Debit", "header": "Total Débit", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Total Credit", "header": "Total Crédit", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Montant Charge", "header": "Montant Charge", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Nb Ecritures", "header": "Nb Écritures", "format": "number", "sortable": True, "filterable": True, "width": 120},
     ])),
    (176, 'Détail des Produits', 'GV_detail_produits', 'Détail des produits par compte', 'DS_CPT_PRODUITS',
     json.dumps([
         {"field": "Compte", "header": "Compte", "format": "text", "sortable": True, "filterable": True, "width": 130},
         {"field": "Intitule Compte", "header": "Intitulé Compte", "format": "text", "sortable": True, "filterable": True, "width": 250},
         {"field": "Total Debit", "header": "Total Débit", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Total Credit", "header": "Total Crédit", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Montant Produit", "header": "Montant Produit", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Nb Ecritures", "header": "Nb Écritures", "format": "number", "sortable": True, "filterable": True, "width": 120},
     ])),
    (177, 'Échéances Clients', 'GV_echeances_clients', 'Échéances des comptes clients', 'DS_CPT_ECHEANCES_CLIENTS',
     json.dumps([
         {"field": "Client", "header": "Client", "format": "text", "sortable": True, "filterable": True, "width": 200},
         {"field": "Date Echeance", "header": "Date Échéance", "format": "date", "sortable": True, "filterable": True, "width": 130},
         {"field": "Date Ecriture", "header": "Date Écriture", "format": "date", "sortable": True, "filterable": True, "width": 130},
         {"field": "Num Piece", "header": "N° Pièce", "format": "text", "sortable": True, "filterable": True, "width": 130},
         {"field": "Num Facture", "header": "N° Facture", "format": "text", "sortable": True, "filterable": True, "width": 130},
         {"field": "Libelle", "header": "Libellé", "format": "text", "sortable": True, "filterable": True, "width": 200},
         {"field": "Solde", "header": "Solde", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Mode Reglement", "header": "Mode Règlement", "format": "text", "sortable": True, "filterable": True, "width": 150},
     ])),
    (178, 'Échéances Fournisseurs', 'GV_echeances_fournisseurs', 'Échéances des comptes fournisseurs', 'DS_CPT_ECHEANCES_FOURN',
     json.dumps([
         {"field": "Fournisseur", "header": "Fournisseur", "format": "text", "sortable": True, "filterable": True, "width": 200},
         {"field": "Date Echeance", "header": "Date Échéance", "format": "date", "sortable": True, "filterable": True, "width": 130},
         {"field": "Date Ecriture", "header": "Date Écriture", "format": "date", "sortable": True, "filterable": True, "width": 130},
         {"field": "Num Piece", "header": "N° Pièce", "format": "text", "sortable": True, "filterable": True, "width": 130},
         {"field": "Num Facture", "header": "N° Facture", "format": "text", "sortable": True, "filterable": True, "width": 130},
         {"field": "Libelle", "header": "Libellé", "format": "text", "sortable": True, "filterable": True, "width": 200},
         {"field": "Solde", "header": "Solde", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Mode Reglement", "header": "Mode Règlement", "format": "text", "sortable": True, "filterable": True, "width": 150},
     ])),
    (179, 'Lettrage et Rapprochement', 'GV_lettrage_rapprochement', 'Lettrage et rapprochement des tiers', 'DS_CPT_LETTRAGE',
     json.dumps([
         {"field": "Tiers", "header": "Tiers", "format": "text", "sortable": True, "filterable": True, "width": 200},
         {"field": "Total Debit", "header": "Total Débit", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Total Credit", "header": "Total Crédit", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Solde", "header": "Solde", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Lettre", "header": "Lettré", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Non Lettre", "header": "Non Lettré", "format": "currency", "sortable": True, "filterable": True, "width": 150},
         {"field": "Nb Ecritures", "header": "Nb Écritures", "format": "number", "sortable": True, "filterable": True, "width": 120},
     ])),
]

print("\n=== Inserting GridViews 173-179 ===")
cursor.execute("SET IDENTITY_INSERT APP_GridViews ON")
for gv in gridviews_to_insert:
    gv_id, nom, code, description, ds_code, columns_config = gv
    try:
        cursor.execute("""
            INSERT INTO APP_GridViews (id, nom, code, description, data_source_code, columns_config, features, is_custom, actif)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)
        """, (gv_id, nom, code, description, ds_code, columns_config, features_standard))
        print(f"  Inserted GV id={gv_id}: {nom} -> {ds_code}")
    except Exception as e:
        print(f"  ERROR GV id={gv_id}: {e}")
cursor.execute("SET IDENTITY_INSERT APP_GridViews OFF")
conn.commit()

# FINAL VERIFICATION
print("\n=== FINAL VERIFICATION ===")
cursor.execute("SELECT id, nom, data_source_code FROM APP_GridViews WHERE id BETWEEN 170 AND 179 ORDER BY id")
print("GridViews 170-179:")
for r in cursor.fetchall():
    print(f"  id={r[0]}, nom={r[1]}, ds={r[2]}")

cursor.execute("SELECT id, nom, data_source_code FROM APP_Pivots_V2 ORDER BY id")
print("\nPivots V2 (all):")
for r in cursor.fetchall():
    print(f"  id={r[0]}, nom={r[1]}, ds={r[2]}")

cursor.execute("SELECT id, nom FROM APP_Dashboards ORDER BY id")
print("\nDashboards (all):")
for r in cursor.fetchall():
    print(f"  id={r[0]}, nom={r[1]}")

conn.close()
print("\n=== COMPLETE ===")
