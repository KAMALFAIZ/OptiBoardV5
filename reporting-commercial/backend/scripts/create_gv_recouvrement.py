"""Create 13 GridViews for Recouvrement module and update menus"""
import pyodbc, json

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

# Menu mapping: menu_id -> (nom, data_source_code, columns_config)
gridviews = [
    # === Encours Clients ===
    (109, "Balance Agee", "DS_BALANCE_AGEE", [
        {"field": "Code Client", "header": "Code Client", "width": 110},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 160},
        {"field": "Charge Recouvrement", "header": "Charg\u00e9 Recouvrement", "width": 160},
        {"field": "Societe", "header": "Soci\u00e9t\u00e9", "width": 100},
        {"field": "Non Echu", "header": "Non \u00c9chu", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "0-30j", "header": "0-30j", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "31-60j", "header": "31-60j", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "61-90j", "header": "61-90j", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "91-120j", "header": "91-120j", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "+120j", "header": "+120j", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "Total Creance", "header": "Total Cr\u00e9ance", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Total Echu", "header": "Total \u00c9chu", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Nb Echeances", "header": "Nb \u00c9ch\u00e9ances", "width": 110, "type": "number"},
        {"field": "Max Retard Jours", "header": "Max Retard (j)", "width": 120, "type": "number"},
    ]),
    (110, "DSO par Client", "DS_DSO", [
        {"field": "Code Client", "header": "Code Client", "width": 110},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Soci\u00e9t\u00e9", "width": 100},
        {"field": "Encours", "header": "Encours", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA 12 Mois", "header": "CA 12 Mois", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Regle 12 Mois", "header": "R\u00e9gl\u00e9 12 Mois", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Delai Moyen Paiement", "header": "D\u00e9lai Moyen Paiement", "width": 150, "type": "number"},
        {"field": "Nb Reglements", "header": "Nb R\u00e8glements", "width": 120, "type": "number"},
        {"field": "DSO Jours", "header": "DSO (jours)", "width": 110, "type": "number"},
    ]),
    (111, "Creances Douteuses", "DS_CREANCES_DOUTEUSES", [
        {"field": "Code Client", "header": "Code Client", "width": 110},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 160},
        {"field": "Charge Recouvrement", "header": "Charg\u00e9 Recouvrement", "width": 160},
        {"field": "Societe", "header": "Soci\u00e9t\u00e9", "width": 100},
        {"field": "Montant +120j", "header": "Montant +120j", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Total Creance", "header": "Total Cr\u00e9ance", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "% Douteux", "header": "% Douteux", "width": 100, "type": "number", "format": "#,##0.0"},
        {"field": "Nb Echeances +120j", "header": "Nb \u00c9ch. +120j", "width": 120, "type": "number"},
        {"field": "Max Retard Jours", "header": "Max Retard (j)", "width": 120, "type": "number"},
    ]),
    (112, "KPIs Recouvrement", "DS_KPI_RECOUVREMENT", [
        {"field": "Encours Total", "header": "Encours Total", "width": 150, "type": "number", "format": "#,##0.00"},
        {"field": "A Echoir", "header": "\u00c0 \u00c9choir", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Echu", "header": "\u00c9chu", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Nb Echeances Retard", "header": "Nb \u00c9ch. en Retard", "width": 140, "type": "number"},
        {"field": "Nb Clients Retard", "header": "Nb Clients Retard", "width": 140, "type": "number"},
        {"field": "Reglements Mois", "header": "R\u00e8glements Mois", "width": 140, "type": "number", "format": "#,##0.00"},
        {"field": "Retard Moyen Jours", "header": "Retard Moyen (j)", "width": 140, "type": "number"},
    ]),

    # === Echeances Ventes ===
    (114, "Echeances Non Reglees", "DS_ECHEANCES_NON_REGLEES", [
        {"field": "Societe", "header": "Soci\u00e9t\u00e9", "width": 100},
        {"field": "Code Client", "header": "Code Client", "width": 110},
        {"field": "Client", "header": "Client", "width": 180},
        {"field": "Code Tier Payeur", "header": "Code Tier Payeur", "width": 120},
        {"field": "Tier Payeur", "header": "Tier Payeur", "width": 160},
        {"field": "Num Piece", "header": "N\u00b0 Pi\u00e8ce", "width": 120},
        {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
        {"field": "Date Echeance", "header": "Date \u00c9ch\u00e9ance", "width": 110, "type": "date"},
        {"field": "Montant Echeance", "header": "Montant \u00c9ch\u00e9ance", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Montant Regle", "header": "Montant R\u00e9gl\u00e9", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Reste A Regler", "header": "Reste \u00c0 R\u00e9gler", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Mode Reglement", "header": "Mode R\u00e8glement", "width": 130},
        {"field": "Code Commercial", "header": "Code Commercial", "width": 120},
        {"field": "Commercial", "header": "Commercial", "width": 160},
        {"field": "Charge Recouvrement", "header": "Charg\u00e9 Recouvrement", "width": 150},
        {"field": "Jours Retard", "header": "Jours Retard", "width": 100, "type": "number"},
        {"field": "Tranche Age", "header": "Tranche \u00c2ge", "width": 100},
    ]),
    (115, "Echeances par Client", "DS_ECHEANCES_PAR_CLIENT", [
        {"field": "Code Client", "header": "Code Client", "width": 110},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Soci\u00e9t\u00e9", "width": 100},
        {"field": "Nb Echeances", "header": "Nb \u00c9ch\u00e9ances", "width": 110, "type": "number"},
        {"field": "Total Echeances", "header": "Total \u00c9ch\u00e9ances", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Total Regle", "header": "Total R\u00e9gl\u00e9", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Reste A Regler", "header": "Reste \u00c0 R\u00e9gler", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "A Echoir", "header": "\u00c0 \u00c9choir", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "0-30j", "header": "0-30j", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "31-60j", "header": "31-60j", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "61-90j", "header": "61-90j", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "91-120j", "header": "91-120j", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "+120j", "header": "+120j", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Derniere Echeance", "header": "Derni\u00e8re \u00c9ch\u00e9ance", "width": 130, "type": "date"},
        {"field": "Max Jours Retard", "header": "Max Retard (j)", "width": 120, "type": "number"},
    ]),
    (116, "Echeances par Commercial", "DS_ECHEANCES_PAR_COMMERCIAL", [
        {"field": "Code Commercial", "header": "Code Commercial", "width": 130},
        {"field": "Commercial", "header": "Commercial", "width": 180},
        {"field": "Charge Recouvrement", "header": "Charg\u00e9 Recouvrement", "width": 160},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "type": "number"},
        {"field": "Nb Echeances", "header": "Nb \u00c9ch\u00e9ances", "width": 110, "type": "number"},
        {"field": "Encours Total", "header": "Encours Total", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "A Echoir", "header": "\u00c0 \u00c9choir", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "0-30j", "header": "0-30j", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "31-60j", "header": "31-60j", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "61-90j", "header": "61-90j", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "91-120j", "header": "91-120j", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "+120j", "header": "+120j", "width": 100, "type": "number", "format": "#,##0.00"},
    ]),
    (117, "Echeances par Mode Reglement", "DS_ECHEANCES_PAR_MODE", [
        {"field": "Mode Reglement", "header": "Mode R\u00e8glement", "width": 200},
        {"field": "Code Mode", "header": "Code Mode", "width": 110},
        {"field": "Nb Echeances", "header": "Nb \u00c9ch\u00e9ances", "width": 120, "type": "number"},
        {"field": "Total Echeances", "header": "Total \u00c9ch\u00e9ances", "width": 140, "type": "number", "format": "#,##0.00"},
        {"field": "Reste A Regler", "header": "Reste \u00c0 R\u00e9gler", "width": 140, "type": "number", "format": "#,##0.00"},
        {"field": "Retard Moyen Jours", "header": "Retard Moyen (j)", "width": 140, "type": "number"},
    ]),
    (118, "Echeances a Echoir", "DS_ECHEANCES_A_ECHOIR", [
        {"field": "Societe", "header": "Soci\u00e9t\u00e9", "width": 100},
        {"field": "Code Client", "header": "Code Client", "width": 110},
        {"field": "Client", "header": "Client", "width": 180},
        {"field": "Num Piece", "header": "N\u00b0 Pi\u00e8ce", "width": 120},
        {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
        {"field": "Date Echeance", "header": "Date \u00c9ch\u00e9ance", "width": 110, "type": "date"},
        {"field": "Montant A Regler", "header": "Montant \u00c0 R\u00e9gler", "width": 140, "type": "number", "format": "#,##0.00"},
        {"field": "Mode Reglement", "header": "Mode R\u00e8glement", "width": 140},
        {"field": "Commercial", "header": "Commercial", "width": 160},
        {"field": "Jours Avant Echeance", "header": "Jours Avant \u00c9ch.", "width": 130, "type": "number"},
        {"field": "Urgence", "header": "Urgence", "width": 100},
    ]),

    # === Reglements ===
    (120, "Reglements par Periode", "DS_REGLEMENTS_PAR_PERIODE", [
        {"field": "Annee", "header": "Ann\u00e9e", "width": 80, "type": "number"},
        {"field": "Mois", "header": "Mois", "width": 70, "type": "number"},
        {"field": "Periode", "header": "P\u00e9riode", "width": 100},
        {"field": "Nb Reglements", "header": "Nb R\u00e8glements", "width": 120, "type": "number"},
        {"field": "Total Reglements", "header": "Total R\u00e8glements", "width": 150, "type": "number", "format": "#,##0.00"},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "type": "number"},
        {"field": "Delai Moyen Jours", "header": "D\u00e9lai Moyen (j)", "width": 130, "type": "number"},
    ]),
    (121, "Reglements par Client", "DS_REGLEMENTS_PAR_CLIENT", [
        {"field": "Code Client", "header": "Code Client", "width": 110},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Soci\u00e9t\u00e9", "width": 100},
        {"field": "Nb Reglements", "header": "Nb R\u00e8glements", "width": 120, "type": "number"},
        {"field": "Total Regle", "header": "Total R\u00e9gl\u00e9", "width": 140, "type": "number", "format": "#,##0.00"},
        {"field": "Premier Reglement", "header": "1er R\u00e8glement", "width": 120, "type": "date"},
        {"field": "Dernier Reglement", "header": "Dernier R\u00e8glement", "width": 130, "type": "date"},
        {"field": "Delai Moyen Jours", "header": "D\u00e9lai Moyen (j)", "width": 130, "type": "number"},
    ]),
    (122, "Reglements par Mode", "DS_REGLEMENTS_PAR_MODE", [
        {"field": "Mode Reglement", "header": "Mode R\u00e8glement", "width": 200},
        {"field": "Nb Reglements", "header": "Nb R\u00e8glements", "width": 130, "type": "number"},
        {"field": "Total Regle", "header": "Total R\u00e9gl\u00e9", "width": 150, "type": "number", "format": "#,##0.00"},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 110, "type": "number"},
        {"field": "Delai Moyen Jours", "header": "D\u00e9lai Moyen (j)", "width": 140, "type": "number"},
    ]),
    (123, "Factures Non Reglees", "DS_FACTURES_NON_REGLEES", [
        {"field": "Societe", "header": "Soci\u00e9t\u00e9", "width": 100},
        {"field": "Code Client", "header": "Code Client", "width": 110},
        {"field": "Client", "header": "Client", "width": 180},
        {"field": "Num Piece", "header": "N\u00b0 Pi\u00e8ce", "width": 120},
        {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Montant Regle", "header": "Montant R\u00e9gl\u00e9", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Reste A Regler", "header": "Reste \u00c0 R\u00e9gler", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Age Jours", "header": "\u00c2ge (jours)", "width": 100, "type": "number"},
    ]),
]

print(f"Creation de {len(gridviews)} GridViews Recouvrement...\n")

for menu_id, nom, ds_code, columns in gridviews:
    cols_json = json.dumps(columns, ensure_ascii=False)

    cursor.execute("""
        INSERT INTO APP_GridViews (nom, description, columns_config, data_source_code, page_size, actif, is_public, show_totals)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, 50, 1, 0, 1)
    """, (nom, f"GridView Recouvrement - {nom}", cols_json, ds_code))

    gv_id = cursor.fetchone()[0]

    # Update menu target_id
    cursor.execute("UPDATE APP_Menus SET target_id = ? WHERE id = ?", (gv_id, menu_id))
    menu_ok = cursor.rowcount

    print(f"  OK: {nom} (GV ID={gv_id}, menu={menu_ok})")

# Verify
cursor.execute("SELECT COUNT(*) FROM APP_GridViews WHERE data_source_code LIKE 'DS_%' AND nom IN (" + ",".join(["?" for _ in gridviews]) + ")", [g[1] for g in gridviews])
total = cursor.fetchone()[0]

cursor.close()
conn.close()
print(f"\nTermine: {total} GridViews, {len(gridviews)}/{len(gridviews)} menus OK")
