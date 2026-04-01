import pyodbc
import json

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_cltKA;UID=sa;PWD=SQL@2019;'
)
cursor = conn.cursor()

# STEP 1: Add data_source_code to APP_GridViews
print("STEP 1: Adding data_source_code column to APP_GridViews...")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('APP_GridViews') AND name = 'data_source_code')
    ALTER TABLE APP_GridViews ADD data_source_code VARCHAR(100)
""")
conn.commit()
print("  OK")

# STEP 2: Update GridViews 170-179 with data_source_code
print("\nSTEP 2: Updating GridViews 170-179...")
mappings = [
    (170, 'DS_CPT_GRAND_LIVRE'),
    (171, 'DS_CPT_BALANCE'),
    (172, 'DS_CPT_JOURNAL'),
    (173, 'DS_CPT_BALANCE_TIERS'),
    (174, 'DS_CPT_TRESORERIE'),
    (175, 'DS_CPT_CHARGES'),
    (176, 'DS_CPT_PRODUITS'),
    (177, 'DS_CPT_ECHEANCES_CLIENTS'),
    (178, 'DS_CPT_ECHEANCES_FOURN'),
    (179, 'DS_CPT_LETTRAGE'),
]
for gv_id, ds_code in mappings:
    cursor.execute("UPDATE APP_GridViews SET data_source_code = ? WHERE id = ?", (ds_code, gv_id))
    print(f"  GV {gv_id} -> {ds_code}: {cursor.rowcount} row(s) updated")
conn.commit()

# STEP 3: Insert Pivots V2 (IDs 27-32)
print("\nSTEP 3: Inserting Pivots V2...")
cursor.execute("SELECT COUNT(*) FROM APP_Pivots_V2 WHERE id IN (27,28,29,30,31,32)")
existing = cursor.fetchone()[0]
if existing > 0:
    print(f"  WARNING: {existing} pivots already exist with IDs 27-32, skipping inserts")
else:
    pivots = [
        (27, 'Resultat par Nature', 'PV_resultat_par_nature', 'Analyse resultat par nature de compte', 'DS_CPT_RESULTAT_NATURE',
         '[{"field":"Nature Compte"},{"field":"Classe"}]', '[]',
         '[{"field":"Debit","aggregation":"sum","format":"currency"},{"field":"Credit","aggregation":"sum","format":"currency"},{"field":"Solde","aggregation":"sum","format":"currency"}]',
         '[{"field":"Societe","label":"Societe"},{"field":"Annee","label":"Annee"}]'),
        (28, 'Balance par Journal', 'PV_balance_par_journal', 'Balance Debit/Credit/Solde par journal', 'DS_CPT_BALANCE_JOURNAL',
         '[{"field":"Code Journal"},{"field":"Journal"}]', '[]',
         '[{"field":"Debit","aggregation":"sum","format":"currency"},{"field":"Credit","aggregation":"sum","format":"currency"},{"field":"Solde","aggregation":"sum","format":"currency"}]',
         '[{"field":"Societe","label":"Societe"},{"field":"Type Journal","label":"Type Journal"}]'),
        (29, 'Balance par Classe', 'PV_balance_par_classe', 'Balance par classe comptable PCM Marocain', 'DS_CPT_BALANCE_CLASSE',
         '[{"field":"Classe"},{"field":"Libelle Classe"}]', '[]',
         '[{"field":"Debit","aggregation":"sum","format":"currency"},{"field":"Credit","aggregation":"sum","format":"currency"},{"field":"Solde","aggregation":"sum","format":"currency"},{"field":"Nb Ecritures","aggregation":"sum","format":"number"}]',
         '[{"field":"Societe","label":"Societe"},{"field":"Annee","label":"Annee"}]'),
        (30, 'Tresorerie par Banque', 'PV_tresorerie_par_banque', 'Encaissements et decaissements par banque', 'DS_CPT_TRESO_BANQUE',
         '[{"field":"Code Journal"},{"field":"Banque"}]', '[]',
         '[{"field":"Encaissements","aggregation":"sum","format":"currency"},{"field":"Decaissements","aggregation":"sum","format":"currency"},{"field":"Solde","aggregation":"sum","format":"currency"}]',
         '[{"field":"Societe","label":"Societe"}]'),
        (31, 'Soldes Clients', 'PV_soldes_clients', 'Soldes debiteurs des comptes clients', 'DS_CPT_SOLDES_CLIENTS',
         '[{"field":"Compte Tiers"},{"field":"Client"}]', '[]',
         '[{"field":"Debit","aggregation":"sum","format":"currency"},{"field":"Credit","aggregation":"sum","format":"currency"},{"field":"Solde","aggregation":"sum","format":"currency"}]',
         '[{"field":"Societe","label":"Societe"}]'),
        (32, 'Soldes Fournisseurs', 'PV_soldes_fournisseurs', 'Soldes crediteurs des comptes fournisseurs', 'DS_CPT_SOLDES_FOURN',
         '[{"field":"Compte Tiers"},{"field":"Fournisseur"}]', '[]',
         '[{"field":"Debit","aggregation":"sum","format":"currency"},{"field":"Credit","aggregation":"sum","format":"currency"},{"field":"Solde","aggregation":"sum","format":"currency"}]',
         '[{"field":"Societe","label":"Societe"}]'),
    ]
    cursor.execute("SET IDENTITY_INSERT APP_Pivots_V2 ON")
    for p in pivots:
        try:
            cursor.execute("""
                INSERT INTO APP_Pivots_V2 (id, nom, code, description, data_source_code, rows_config, columns_config, values_config, filters_config, is_public, is_custom)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
            """, p)
            print(f"  Inserted Pivot id={p[0]}: {p[1]}")
        except Exception as e:
            print(f"  ERROR Pivot id={p[0]}: {e}")
    cursor.execute("SET IDENTITY_INSERT APP_Pivots_V2 OFF")
    conn.commit()

# STEP 4: Insert Dashboards (IDs 38-46)
print("\nSTEP 4: Inserting Dashboards...")
cursor.execute("SELECT COUNT(*) FROM APP_Dashboards WHERE id IN (38,39,40,41,42,43,44,45,46)")
existing_d = cursor.fetchone()[0]
if existing_d > 0:
    print(f"  WARNING: {existing_d} dashboards already exist with IDs 38-46, skipping inserts")
else:
    dashboards = [
        (38, 'TB Comptabilite Globale', 'DB_comptabilite_globale', 'Tableau de bord global de comptabilite',
         json.dumps([
             {"id":"w1","type":"kpi","title":"Total Debit","x":0,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","value_field":"Total Debit","format":"currency","suffix":" DH","color":"#3b82f6"}},
             {"id":"w2","type":"kpi","title":"Total Credit","x":3,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","value_field":"Total Credit","format":"currency","suffix":" DH","color":"#10b981"}},
             {"id":"w3","type":"kpi","title":"Solde Net","x":6,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","value_field":"Solde Net","format":"currency","suffix":" DH","color":"#f59e0b"}},
             {"id":"w4","type":"kpi","title":"Nb Ecritures","x":9,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","value_field":"Nb Ecritures","format":"number","color":"#8b5cf6"}},
             {"id":"w5","type":"bar","title":"Evolution Mensuelle Debit / Credit","x":0,"y":3,"w":8,"h":8,"config":{"dataSourceCode":"DS_CPT_EVOLUTION_MENSUELLE","category_field":"Periode","value_fields":["Total Debit","Total Credit"],"colors":["#3b82f6","#10b981"]}},
             {"id":"w6","type":"pie","title":"Repartition par Nature","x":8,"y":3,"w":4,"h":8,"config":{"dataSourceCode":"DS_CPT_REPARTITION_NATURE","category_field":"Nature Compte","value_field":"Nb Ecritures"}}
         ])),
        (39, 'Evolution Mensuelle Comptable', 'DB_evolution_mensuelle_comptable', 'Evolution Debit/Credit par mois',
         json.dumps([
             {"id":"w1","type":"bar","title":"Debit / Credit par Mois","x":0,"y":0,"w":12,"h":8,"config":{"dataSourceCode":"DS_CPT_EVOLUTION_MENSUELLE","category_field":"Periode","value_fields":["Total Debit","Total Credit"],"colors":["#3b82f6","#10b981"]}},
             {"id":"w2","type":"line","title":"Solde Net par Mois","x":0,"y":8,"w":12,"h":6,"config":{"dataSourceCode":"DS_CPT_EVOLUTION_MENSUELLE","category_field":"Periode","value_fields":["Solde"],"colors":["#f59e0b"]}}
         ])),
        (40, 'Charges vs Produits', 'DB_charges_vs_produits', 'Comparatif Charges et Produits par mois',
         json.dumps([
             {"id":"w1","type":"bar","title":"Charges vs Produits par Mois","x":0,"y":0,"w":12,"h":8,"config":{"dataSourceCode":"DS_CPT_CHARGES_PRODUITS_MENS","category_field":"Periode","value_fields":["Charges","Produits"],"colors":["#ef4444","#10b981"]}},
             {"id":"w2","type":"line","title":"Resultat Net par Mois","x":0,"y":8,"w":12,"h":6,"config":{"dataSourceCode":"DS_CPT_CHARGES_PRODUITS_MENS","category_field":"Periode","value_fields":["Resultat"],"colors":["#3b82f6"]}}
         ])),
        (41, 'Repartition par Nature Compte', 'DB_repartition_nature_compte', 'Repartition du volume par nature de compte',
         json.dumps([
             {"id":"w1","type":"pie","title":"Repartition par Nature (Volume)","x":0,"y":0,"w":6,"h":8,"config":{"dataSourceCode":"DS_CPT_REPARTITION_NATURE","category_field":"Nature Compte","value_field":"Nb Ecritures"}},
             {"id":"w2","type":"pie","title":"Repartition par Nature (Debit)","x":6,"y":0,"w":6,"h":8,"config":{"dataSourceCode":"DS_CPT_REPARTITION_NATURE","category_field":"Nature Compte","value_field":"Debit"}}
         ])),
        (42, 'Flux de Tresorerie', 'DB_flux_tresorerie', 'Encaissements et decaissements mensuels',
         json.dumps([
             {"id":"w1","type":"bar","title":"Encaissements vs Decaissements","x":0,"y":0,"w":12,"h":8,"config":{"dataSourceCode":"DS_CPT_FLUX_TRESORERIE","category_field":"Periode","value_fields":["Encaissements","Decaissements"],"colors":["#10b981","#ef4444"]}},
             {"id":"w2","type":"line","title":"Solde de Tresorerie","x":0,"y":8,"w":12,"h":6,"config":{"dataSourceCode":"DS_CPT_FLUX_TRESORERIE","category_field":"Periode","value_fields":["Solde"],"colors":["#3b82f6"]}}
         ])),
        (43, 'Top 20 Clients Comptable', 'DB_top_clients_comptable', 'Top 20 clients par solde debiteur',
         json.dumps([
             {"id":"w1","type":"bar","title":"Top 20 Clients par Solde","x":0,"y":0,"w":12,"h":8,"config":{"dataSourceCode":"DS_CPT_TOP_CLIENTS","category_field":"Client","value_fields":["Solde"],"colors":["#3b82f6"]}},
             {"id":"w2","type":"table","title":"Detail Top 20 Clients","x":0,"y":8,"w":12,"h":8,"config":{"dataSourceCode":"DS_CPT_TOP_CLIENTS","columns":["Compte","Client","Total Debit","Total Credit","Solde"]}}
         ])),
        (44, 'Top 20 Fournisseurs Comptable', 'DB_top_fournisseurs_comptable', 'Top 20 fournisseurs par solde crediteur',
         json.dumps([
             {"id":"w1","type":"bar","title":"Top 20 Fournisseurs par Solde","x":0,"y":0,"w":12,"h":8,"config":{"dataSourceCode":"DS_CPT_TOP_FOURNISSEURS","category_field":"Fournisseur","value_fields":["Solde"],"colors":["#ef4444"]}},
             {"id":"w2","type":"table","title":"Detail Top 20 Fournisseurs","x":0,"y":8,"w":12,"h":8,"config":{"dataSourceCode":"DS_CPT_TOP_FOURNISSEURS","columns":["Compte","Fournisseur","Total Debit","Total Credit","Solde"]}}
         ])),
        (45, 'Repartition par Type Journal', 'DB_repartition_type_journal', 'Volume et montants par type de journal',
         json.dumps([
             {"id":"w1","type":"pie","title":"Volume par Type Journal","x":0,"y":0,"w":6,"h":8,"config":{"dataSourceCode":"DS_CPT_REPARTITION_JOURNAL","category_field":"Type Journal","value_field":"Nb Ecritures"}},
             {"id":"w2","type":"bar","title":"Montants par Type Journal","x":6,"y":0,"w":6,"h":8,"config":{"dataSourceCode":"DS_CPT_REPARTITION_JOURNAL","category_field":"Type Journal","value_fields":["Total Debit","Total Credit"],"colors":["#3b82f6","#10b981"]}}
         ])),
        (46, 'Synthese Annuelle Comptable', 'DB_synthese_annuelle_comptable', 'Synthese Debit/Credit par exercice',
         json.dumps([
             {"id":"w1","type":"bar","title":"Debit / Credit par Exercice","x":0,"y":0,"w":8,"h":8,"config":{"dataSourceCode":"DS_CPT_SYNTHESE_ANNUELLE","category_field":"Exercice","value_fields":["Total Debit","Total Credit"],"colors":["#3b82f6","#10b981"]}},
             {"id":"w2","type":"table","title":"Tableau Synthese Annuelle","x":8,"y":0,"w":4,"h":8,"config":{"dataSourceCode":"DS_CPT_SYNTHESE_ANNUELLE","columns":["Exercice","Total Debit","Total Credit","Solde Net","Nb Ecritures"]}}
         ])),
    ]
    cursor.execute("SET IDENTITY_INSERT APP_Dashboards ON")
    for d in dashboards:
        try:
            cursor.execute("""
                INSERT INTO APP_Dashboards (id, nom, code, description, widgets, is_public, is_custom, actif)
                VALUES (?, ?, ?, ?, ?, 1, 0, 1)
            """, d)
            print(f"  Inserted Dashboard id={d[0]}: {d[1]}")
        except Exception as e:
            print(f"  ERROR Dashboard id={d[0]}: {e}")
    cursor.execute("SET IDENTITY_INSERT APP_Dashboards OFF")
    conn.commit()

# VERIFICATION
print("\n=== VERIFICATION ===")
cursor.execute("SELECT id, nom, data_source_code FROM APP_GridViews WHERE id BETWEEN 170 AND 179 ORDER BY id")
print("GridViews 170-179:")
for r in cursor.fetchall():
    print(f"  id={r[0]}, nom={r[1]}, ds={r[2]}")

cursor.execute("SELECT id, nom, data_source_code FROM APP_Pivots_V2 ORDER BY id")
print("Pivots V2:")
for r in cursor.fetchall():
    print(f"  id={r[0]}, nom={r[1]}, ds={r[2]}")

cursor.execute("SELECT id, nom, code FROM APP_Dashboards ORDER BY id")
print("Dashboards:")
for r in cursor.fetchall():
    print(f"  id={r[0]}, nom={r[1]}, code={r[2]}")

conn.close()
print("\n=== ALL DONE ===")
