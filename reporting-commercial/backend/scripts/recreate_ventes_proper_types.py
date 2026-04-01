"""
=============================================================================
  RECREATE VENTES REPORTS WITH CORRECT TYPES

  According to the catalogue RAPPORTS_OPTIBOARD.md:
    - 8 GRID   : #1-7 Documents + #17 Commandes en Cours
    - 12 PIVOT  : #8-12,16,19,20,23,26,30,33  (was #35 Ventes par Tranche)
    - 15 DASH   : #13-15,18,21-22,24-25,27-29,31-32,34

  Existing datasource templates (IDs 118-152) are KEPT as-is (SQL is correct).
  Existing GridViews (IDs 104-138) and Menus (128-166) are DELETED.
  New GridViews, Pivots, Dashboards and Menus are created.

  NOTE: Some catalogue items (#24 Cross-Selling, #29 CA Previsionnel, #31 Analyse Geo,
  #35 Ventes par Tranche) don't have existing DS templates. We'll map the existing
  templates to the closest matching report type. Extra templates (CA par Depot,
  CA par Affaire, Detail Complet, Par Type Doc, Clients Inactifs) become GridViews
  in the "Rapports Avances" section.
=============================================================================
"""
import pyodbc, json

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

# =============================================================================
#  STEP 1: DELETE EXISTING GRIDVIEWS AND MENUS (keep DataSource Templates)
# =============================================================================
print("=" * 70)
print("  STEP 1: Nettoyage des anciens rapports Ventes (tous GridView)")
print("=" * 70)

# Delete menus (children first, then folders, then root)
cursor.execute("DELETE FROM APP_Menus WHERE parent_id IN (SELECT id FROM APP_Menus WHERE parent_id = 128)")
print(f"  Menus feuilles supprimes: {cursor.rowcount}")
cursor.execute("DELETE FROM APP_Menus WHERE parent_id = 128")
print(f"  Menus dossiers supprimes: {cursor.rowcount}")
cursor.execute("DELETE FROM APP_Menus WHERE id = 128")
print(f"  Menu racine supprime: {cursor.rowcount}")

# Delete all gridviews with DS_VTE_ codes
cursor.execute("DELETE FROM APP_GridViews WHERE data_source_code LIKE 'DS_VTE_%'")
print(f"  GridViews supprimes: {cursor.rowcount}")

print()

# =============================================================================
#  STEP 2: Get all existing template IDs by code
# =============================================================================
cursor.execute("SELECT id, code FROM APP_DataSources_Templates WHERE code LIKE 'DS_VTE_%'")
tmpl = {row[1]: row[0] for row in cursor.fetchall()}
print(f"Templates existants: {len(tmpl)}")
for code, tid in sorted(tmpl.items(), key=lambda x: x[1]):
    print(f"  {tid}: {code}")
print()

# =============================================================================
#  MAPPING: Report Name -> (DS code, Type)
#  Following catalogue RAPPORTS_OPTIBOARD.md exactly
# =============================================================================

# ============== 8 GRIDVIEWS ==============
# Cat #1: Factures de Ventes -> GRID
# Cat #2: Bons de Livraison -> GRID
# Cat #3: Bons de Commande -> GRID
# Cat #4: Devis -> GRID
# Cat #5: Avoirs -> GRID
# Cat #6: Bons de Retour -> GRID
# Cat #7: Preparations de Livraison -> GRID
# Cat #17: Commandes en Cours -> GRID
# Plus extras: Detail Complet, Par Type Doc, Clients Inactifs, CA par Depot, CA par Affaire

# ============== 12 PIVOTS ==============
# Cat #8: CA par Client -> PIVOT
# Cat #9: CA par Article -> PIVOT
# Cat #10: CA par Commercial -> PIVOT
# Cat #11: CA par Region / Ville -> PIVOT
# Cat #12: CA par Famille Article -> PIVOT
# Cat #16: Analyse Marges -> PIVOT
# Cat #19: CA par Mode de Reglement -> PIVOT
# Cat #20: Statistiques Remises -> PIVOT
# Cat #23: Panier Moyen par Client -> PIVOT
# Cat #26: Analyse des Prix de Vente -> PIVOT
# Cat #30: Rentabilite par Client -> PIVOT
# Cat #33: Analyse des Remises -> PIVOT (mapped to Saisonnalite DS)

# ============== 15 DASHBOARDS ==============
# Cat #13: Evolution CA Mensuelle -> DASH
# Cat #14: Top 20 Clients -> DASH
# Cat #15: Top 20 Articles -> DASH
# Cat #18: Comparatif N / N-1 -> DASH
# Cat #21: Analyse RFM Clients -> DASH
# Cat #22: Saisonnalite des Ventes -> DASH
# Cat #25: Clients a Risque de Churn -> DASH
# Cat #27: Taux de Service Client -> DASH
# Cat #28: Analyse des Retours -> DASH
# Cat #32: Fidelite Clients -> DASH
# Cat #34: Performance des Devis -> DASH

# =============================================================================
#  STEP 3: CREATE GRIDVIEWS (8 documents + 5 extras = 13 total)
# =============================================================================
print("=" * 70)
print("  STEP 3: Creation des GridViews")
print("=" * 70)

gridviews = [
    # === 7 DOCUMENTS VENTES ===
    ("Factures de Ventes", "DS_VTE_FACTURES", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Type Document", "header": "Type Document", "width": 150},
        {"field": "Num Piece", "header": "N° Piece", "width": 120},
        {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite", "header": "Quantite", "width": 90, "type": "number"},
        {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Famille", "header": "Famille", "width": 120},
        {"field": "Depot", "header": "Depot", "width": 140},
    ]),
    ("Bons de Livraison", "DS_VTE_BL", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Num BL", "header": "N° BL", "width": 120},
        {"field": "Date BL", "header": "Date BL", "width": 110, "type": "date"},
        {"field": "Num Piece Origine", "header": "N° Piece Origine", "width": 130},
        {"field": "Type Document", "header": "Type Document", "width": 140},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite BL", "header": "Quantite BL", "width": 100, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Depot", "header": "Depot", "width": 140},
    ]),
    ("Bons de Commande", "DS_VTE_BC", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Num BC", "header": "N° BC", "width": 120},
        {"field": "Date BC", "header": "Date BC", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite BC", "header": "Quantite BC", "width": 100, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
    ]),
    ("Devis", "DS_VTE_DEVIS", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Num Piece", "header": "N° Piece", "width": 120},
        {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite", "header": "Quantite", "width": 90, "type": "number"},
        {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Statut", "header": "Statut", "width": 100},
        {"field": "Famille", "header": "Famille", "width": 120},
    ]),
    ("Avoirs", "DS_VTE_AVOIRS", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Type Document", "header": "Type Document", "width": 150},
        {"field": "Num Piece", "header": "N° Piece", "width": 120},
        {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite", "header": "Quantite", "width": 90, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Famille", "header": "Famille", "width": 120},
    ]),
    ("Bons de Retour", "DS_VTE_RETOURS", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Type Document", "header": "Type Document", "width": 150},
        {"field": "Num Piece", "header": "N° Piece", "width": 120},
        {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite", "header": "Quantite", "width": 90, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Depot", "header": "Depot", "width": 140},
    ]),
    ("Preparations de Livraison", "DS_VTE_PL", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Num PL", "header": "N° PL", "width": 120},
        {"field": "Date PL", "header": "Date PL", "width": 110, "type": "date"},
        {"field": "Num Piece Origine", "header": "N° Piece Origine", "width": 130},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite PL", "header": "Quantite PL", "width": 100, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Depot", "header": "Depot", "width": 140},
    ]),
    # === Cat #17: Commandes en Cours -> GRID ===
    ("Commandes en Cours", "DS_VTE_CMD_EN_COURS", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Num Piece", "header": "N° Piece", "width": 120},
        {"field": "Date Commande", "header": "Date Commande", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Qte Commandee", "header": "Qte Commandee", "width": 110, "type": "number"},
        {"field": "Qte Livree", "header": "Qte Livree", "width": 100, "type": "number"},
        {"field": "Reste a Livrer", "header": "Reste a Livrer", "width": 110, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Statut", "header": "Statut", "width": 100},
        {"field": "Anciennete Jours", "header": "Anciennete (j)", "width": 110, "type": "number"},
    ]),
    # === EXTRAS (not in catalogue but useful DS templates) -> GRID ===
    ("Ventes Detail Complet", "DS_VTE_DETAIL_COMPLET", [
        {"field": "Societe", "header": "Societe", "width": 80},
        {"field": "Type Document", "header": "Type", "width": 140},
        {"field": "Num Piece", "header": "N° Piece", "width": 110},
        {"field": "Date Document", "header": "Date Doc", "width": 100, "type": "date"},
        {"field": "Date BL", "header": "Date BL", "width": 100, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 95},
        {"field": "Client", "header": "Client", "width": 180},
        {"field": "Commercial", "header": "Commercial", "width": 130},
        {"field": "Code Article", "header": "Code Art.", "width": 100},
        {"field": "Designation", "header": "Designation", "width": 180},
        {"field": "Famille", "header": "Famille", "width": 110},
        {"field": "Quantite", "header": "Qte", "width": 70, "type": "number"},
        {"field": "Prix Unitaire", "header": "PU", "width": 90, "type": "number", "format": "#,##0.00"},
        {"field": "Montant HT", "header": "HT", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "TTC", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Marge", "header": "Marge", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Depot", "header": "Depot", "width": 120},
        {"field": "Valorise CA", "header": "Val. CA", "width": 70},
    ]),
    ("Ventes par Type Document", "DS_VTE_PAR_TYPE_DOC", [
        {"field": "Type Document", "header": "Type Document", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Documents", "header": "Nb Docs", "width": 100, "type": "number"},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "type": "number"},
        {"field": "Quantite Totale", "header": "Qte Totale", "width": 110, "type": "number"},
        {"field": "Total HT", "header": "Total HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Total TTC", "header": "Total TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Montant Moyen Ligne", "header": "Moy/Ligne", "width": 120, "type": "number", "format": "#,##0.00"},
    ]),
    ("Clients Inactifs", "DS_VTE_CLIENTS_INACTIFS", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Derniere Vente", "header": "Derniere Vente", "width": 120, "type": "date"},
        {"field": "Jours Inactif", "header": "Jours Inactif", "width": 110, "type": "number"},
        {"field": "CA HT Historique", "header": "CA HT Historique", "width": 140, "type": "number", "format": "#,##0.00"},
        {"field": "Nb Documents Historique", "header": "Nb Docs", "width": 100, "type": "number"},
    ]),
    ("CA par Depot", "DS_VTE_CA_DEPOT", [
        {"field": "Code Depot", "header": "Code Depot", "width": 100},
        {"field": "Depot", "header": "Depot", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "type": "number"},
        {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "type": "number"},
        {"field": "Quantite", "header": "Quantite", "width": 90, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA TTC", "header": "CA TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 130, "type": "number", "format": "#,##0.00"},
    ]),
    ("CA par Affaire", "DS_VTE_CA_AFFAIRE", [
        {"field": "Code Affaire", "header": "Code Affaire", "width": 110},
        {"field": "Affaire", "header": "Affaire", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "type": "number"},
        {"field": "Nb Documents", "header": "Nb Docs", "width": 100, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA TTC", "header": "CA TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
]

gv_ids = {}
for nom, ds_code, columns in gridviews:
    ds_id = tmpl.get(ds_code)
    cursor.execute("""
        INSERT INTO APP_GridViews (nom, description, data_source_id, data_source_code,
            columns_config, is_public, created_by, actif, page_size, show_totals)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, 1, 1, 1, 50, 1)
    """, (nom, f"GridView: {nom}", ds_id, ds_code, json.dumps(columns)))
    gv_id = cursor.fetchone()[0]
    gv_ids[ds_code] = gv_id
    print(f"  GridView {gv_id}: {nom} ({ds_code})")

print(f"\n  Total GridViews: {len(gv_ids)}")
print()

# =============================================================================
#  STEP 4: CREATE PIVOTS (12 pivots as per catalogue)
# =============================================================================
print("=" * 70)
print("  STEP 4: Creation des Pivots")
print("=" * 70)

pivots = [
    # Cat #8: CA par Client -> PIVOT
    {
        "nom": "CA par Client",
        "description": "Chiffre d'affaires croise par client x periode",
        "ds_code": "DS_VTE_CA_CLIENT",
        "rows_config": [
            {"field": "Code Client", "label": "Code Client", "type": "text"},
            {"field": "Client", "label": "Client", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "CA HT", "aggregation": "SUM", "label": "CA HT", "format": "currency", "decimals": 2},
            {"field": "CA TTC", "aggregation": "SUM", "label": "CA TTC", "format": "currency", "decimals": 2},
            {"field": "Marge Brute", "aggregation": "SUM", "label": "Marge Brute", "format": "currency", "decimals": 2},
            {"field": "Taux Marge %", "aggregation": "AVG", "label": "Marge %", "format": "percent", "decimals": 2},
            {"field": "Nb Documents", "aggregation": "SUM", "label": "Nb Docs", "format": "number", "decimals": 0},
            {"field": "Quantite Totale", "aggregation": "SUM", "label": "Qte", "format": "number", "decimals": 0},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
            {"field": "Commercial", "type": "select"},
        ],
    },
    # Cat #9: CA par Article -> PIVOT
    {
        "nom": "CA par Article",
        "description": "Analyse des ventes par produit avec quantites et marges",
        "ds_code": "DS_VTE_CA_ARTICLE",
        "rows_config": [
            {"field": "Famille", "label": "Famille", "type": "text"},
            {"field": "Code Article", "label": "Code Article", "type": "text"},
            {"field": "Designation", "label": "Designation", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "CA HT", "aggregation": "SUM", "label": "CA HT", "format": "currency", "decimals": 2},
            {"field": "Quantite Vendue", "aggregation": "SUM", "label": "Qte Vendue", "format": "number", "decimals": 0},
            {"field": "Marge Brute", "aggregation": "SUM", "label": "Marge Brute", "format": "currency", "decimals": 2},
            {"field": "Taux Marge %", "aggregation": "AVG", "label": "Marge %", "format": "percent", "decimals": 2},
            {"field": "Nb Clients", "aggregation": "SUM", "label": "Nb Clients", "format": "number", "decimals": 0},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
            {"field": "Famille", "type": "select"},
        ],
    },
    # Cat #10: CA par Commercial -> PIVOT
    {
        "nom": "CA par Commercial",
        "description": "Performance commerciale par vendeur x periode",
        "ds_code": "DS_VTE_CA_COMMERCIAL",
        "rows_config": [
            {"field": "Code Commercial", "label": "Code", "type": "text"},
            {"field": "Commercial", "label": "Commercial", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "CA HT", "aggregation": "SUM", "label": "CA HT", "format": "currency", "decimals": 2},
            {"field": "CA TTC", "aggregation": "SUM", "label": "CA TTC", "format": "currency", "decimals": 2},
            {"field": "Marge Brute", "aggregation": "SUM", "label": "Marge", "format": "currency", "decimals": 2},
            {"field": "Taux Marge %", "aggregation": "AVG", "label": "Marge %", "format": "percent", "decimals": 2},
            {"field": "Nb Clients", "aggregation": "SUM", "label": "Clients", "format": "number", "decimals": 0},
            {"field": "Nb Documents", "aggregation": "SUM", "label": "Docs", "format": "number", "decimals": 0},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
        ],
    },
    # Cat #11: CA par Region / Ville -> PIVOT
    {
        "nom": "CA par Region / Ville",
        "description": "Repartition geographique du chiffre d'affaires",
        "ds_code": "DS_VTE_CA_REGION",
        "rows_config": [
            {"field": "Region", "label": "Region", "type": "text"},
            {"field": "Ville", "label": "Ville", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "CA HT", "aggregation": "SUM", "label": "CA HT", "format": "currency", "decimals": 2},
            {"field": "CA TTC", "aggregation": "SUM", "label": "CA TTC", "format": "currency", "decimals": 2},
            {"field": "Marge Brute", "aggregation": "SUM", "label": "Marge", "format": "currency", "decimals": 2},
            {"field": "Nb Clients", "aggregation": "SUM", "label": "Clients", "format": "number", "decimals": 0},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
            {"field": "Region", "type": "select"},
        ],
    },
    # Cat #12: CA par Famille Article -> PIVOT
    {
        "nom": "CA par Famille Article",
        "description": "Ventes agregees par categorie de produit",
        "ds_code": "DS_VTE_CA_FAMILLE",
        "rows_config": [
            {"field": "Famille", "label": "Famille", "type": "text"},
            {"field": "Sous Famille", "label": "Sous Famille", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "CA HT", "aggregation": "SUM", "label": "CA HT", "format": "currency", "decimals": 2},
            {"field": "Quantite", "aggregation": "SUM", "label": "Qte", "format": "number", "decimals": 0},
            {"field": "Marge Brute", "aggregation": "SUM", "label": "Marge", "format": "currency", "decimals": 2},
            {"field": "Taux Marge %", "aggregation": "AVG", "label": "Marge %", "format": "percent", "decimals": 2},
            {"field": "Nb Articles", "aggregation": "SUM", "label": "Articles", "format": "number", "decimals": 0},
            {"field": "Nb Clients", "aggregation": "SUM", "label": "Clients", "format": "number", "decimals": 0},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
        ],
    },
    # Cat #16: Analyse Marges -> PIVOT
    {
        "nom": "Analyse Marges",
        "description": "Marge brute par client x article x commercial",
        "ds_code": "DS_VTE_MARGES",
        "rows_config": [
            {"field": "Commercial", "label": "Commercial", "type": "text"},
            {"field": "Client", "label": "Client", "type": "text"},
            {"field": "Designation", "label": "Article", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "CA HT", "aggregation": "SUM", "label": "CA HT", "format": "currency", "decimals": 2},
            {"field": "Cout Revient", "aggregation": "SUM", "label": "Cout Revient", "format": "currency", "decimals": 2},
            {"field": "Marge Brute", "aggregation": "SUM", "label": "Marge Brute", "format": "currency", "decimals": 2},
            {"field": "Taux Marge %", "aggregation": "AVG", "label": "Marge %", "format": "percent", "decimals": 2},
            {"field": "Quantite", "aggregation": "SUM", "label": "Qte", "format": "number", "decimals": 0},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
            {"field": "Commercial", "type": "select"},
            {"field": "Famille", "type": "select"},
        ],
    },
    # Cat #19: CA par Mode de Reglement -> PIVOT
    {
        "nom": "CA par Mode de Reglement",
        "description": "Repartition du CA par type de paiement",
        "ds_code": "DS_VTE_CA_MODE_REGLEMENT",
        "rows_config": [
            {"field": "Categorie Comptable", "label": "Categorie", "type": "text"},
            {"field": "Tiers Payeur", "label": "Tiers Payeur", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "CA HT", "aggregation": "SUM", "label": "CA HT", "format": "currency", "decimals": 2},
            {"field": "CA TTC", "aggregation": "SUM", "label": "CA TTC", "format": "currency", "decimals": 2},
            {"field": "Nb Documents", "aggregation": "SUM", "label": "Nb Docs", "format": "number", "decimals": 0},
            {"field": "Nb Clients", "aggregation": "SUM", "label": "Clients", "format": "number", "decimals": 0},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
        ],
    },
    # Cat #20: Statistiques Remises -> PIVOT
    {
        "nom": "Statistiques Remises",
        "description": "Analyse des remises accordees par client/article",
        "ds_code": "DS_VTE_REMISES",
        "rows_config": [
            {"field": "Client", "label": "Client", "type": "text"},
            {"field": "Designation", "label": "Article", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "CA HT", "aggregation": "SUM", "label": "CA HT Net", "format": "currency", "decimals": 2},
            {"field": "Montant Brut", "aggregation": "SUM", "label": "Montant Brut", "format": "currency", "decimals": 2},
            {"field": "Total Remises", "aggregation": "SUM", "label": "Total Remises", "format": "currency", "decimals": 2},
            {"field": "Quantite", "aggregation": "SUM", "label": "Qte", "format": "number", "decimals": 0},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
            {"field": "Type Remise 1", "type": "select"},
        ],
    },
    # Cat #23: Panier Moyen par Client -> PIVOT
    {
        "nom": "Panier Moyen par Client",
        "description": "Valeur moyenne par transaction x client x periode",
        "ds_code": "DS_VTE_PANIER_MOYEN",
        "rows_config": [
            {"field": "Commercial", "label": "Commercial", "type": "text"},
            {"field": "Client", "label": "Client", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "Panier Moyen HT", "aggregation": "AVG", "label": "Panier Moyen", "format": "currency", "decimals": 2},
            {"field": "CA HT Total", "aggregation": "SUM", "label": "CA Total", "format": "currency", "decimals": 2},
            {"field": "Nb Transactions", "aggregation": "SUM", "label": "Transactions", "format": "number", "decimals": 0},
            {"field": "Nb Articles Distincts", "aggregation": "AVG", "label": "Art. Distincts", "format": "number", "decimals": 0},
            {"field": "Qte Moy par Transaction", "aggregation": "AVG", "label": "Qte Moy/Trans", "format": "number", "decimals": 2},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
            {"field": "Commercial", "type": "select"},
        ],
    },
    # Cat #26: Analyse des Prix de Vente -> PIVOT
    {
        "nom": "Analyse des Prix de Vente",
        "description": "Evolution des prix unitaires par article x client x periode",
        "ds_code": "DS_VTE_ANALYSE_PRIX",
        "rows_config": [
            {"field": "Famille", "label": "Famille", "type": "text"},
            {"field": "Code Article", "label": "Code Article", "type": "text"},
            {"field": "Designation", "label": "Designation", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "Prix Min", "aggregation": "MIN", "label": "Prix Min", "format": "currency", "decimals": 2},
            {"field": "Prix Max", "aggregation": "MAX", "label": "Prix Max", "format": "currency", "decimals": 2},
            {"field": "Prix Moyen", "aggregation": "AVG", "label": "Prix Moyen", "format": "currency", "decimals": 2},
            {"field": "Ecart Type Prix", "aggregation": "AVG", "label": "Ecart Type", "format": "number", "decimals": 2},
            {"field": "Cout Revient Moyen", "aggregation": "AVG", "label": "Cout Revient", "format": "currency", "decimals": 2},
            {"field": "Taux Marge Moy %", "aggregation": "AVG", "label": "Marge %", "format": "percent", "decimals": 2},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
            {"field": "Famille", "type": "select"},
        ],
    },
    # Cat #30: Rentabilite par Client -> PIVOT
    {
        "nom": "Rentabilite par Client",
        "description": "CA - cout des marchandises - remises par client",
        "ds_code": "DS_VTE_RENTABILITE_CLIENT",
        "rows_config": [
            {"field": "Commercial", "label": "Commercial", "type": "text"},
            {"field": "Code Client", "label": "Code", "type": "text"},
            {"field": "Client", "label": "Client", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "CA HT", "aggregation": "SUM", "label": "CA HT", "format": "currency", "decimals": 2},
            {"field": "Cout Revient Total", "aggregation": "SUM", "label": "Cout Revient", "format": "currency", "decimals": 2},
            {"field": "Marge Brute", "aggregation": "SUM", "label": "Marge Brute", "format": "currency", "decimals": 2},
            {"field": "Taux Marge %", "aggregation": "AVG", "label": "Marge %", "format": "percent", "decimals": 2},
            {"field": "Nb Transactions", "aggregation": "SUM", "label": "Transactions", "format": "number", "decimals": 0},
            {"field": "Nb Articles", "aggregation": "SUM", "label": "Articles", "format": "number", "decimals": 0},
            {"field": "CA par Kg", "aggregation": "AVG", "label": "CA/Kg", "format": "currency", "decimals": 2},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
            {"field": "Commercial", "type": "select"},
        ],
    },
    # Cat #33: Saisonnalite des Ventes -> PIVOT (using DS_VTE_SAISONNALITE)
    {
        "nom": "Saisonnalite des Ventes",
        "description": "Detection des pics/creux par article et famille sur 3 ans",
        "ds_code": "DS_VTE_SAISONNALITE",
        "rows_config": [
            {"field": "Famille", "label": "Famille", "type": "text"},
            {"field": "Nom Mois", "label": "Mois", "type": "text"},
        ],
        "columns_config": [],
        "values_config": [
            {"field": "CA N", "aggregation": "SUM", "label": "CA N", "format": "currency", "decimals": 2},
            {"field": "CA N-1", "aggregation": "SUM", "label": "CA N-1", "format": "currency", "decimals": 2},
            {"field": "CA N-2", "aggregation": "SUM", "label": "CA N-2", "format": "currency", "decimals": 2},
            {"field": "Quantite Totale", "aggregation": "SUM", "label": "Qte", "format": "number", "decimals": 0},
        ],
        "filters_config": [
            {"field": "Societe", "type": "select"},
            {"field": "Famille", "type": "select"},
        ],
    },
]

pivot_ids = {}
for p in pivots:
    ds_code = p["ds_code"]
    ds_id = tmpl.get(ds_code)
    cursor.execute("""
        INSERT INTO APP_Pivots_V2 (nom, description, data_source_id, data_source_code,
            rows_config, columns_config, filters_config, values_config,
            show_grand_totals, show_subtotals, show_row_percent, show_col_percent, show_total_percent,
            grand_total_position, subtotal_position, show_summary_row,
            comparison_mode, formatting_rules, source_params, summary_functions, window_calculations,
            is_public, created_by)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?,
            ?, ?, ?, ?,
            1, 1, 0, 0, 0,
            'bottom', 'bottom', 0,
            '', '[]', '[]', '[]', '[]',
            1, 1)
    """, (
        p["nom"], p["description"], ds_id, ds_code,
        json.dumps(p["rows_config"]), json.dumps(p["columns_config"]),
        json.dumps(p["filters_config"]), json.dumps(p["values_config"]),
    ))
    pid = cursor.fetchone()[0]
    pivot_ids[ds_code] = pid
    print(f"  Pivot {pid}: {p['nom']} ({ds_code})")

print(f"\n  Total Pivots: {len(pivot_ids)}")
print()

# =============================================================================
#  STEP 5: CREATE DASHBOARDS (11 dashboards using existing DS templates)
# =============================================================================
print("=" * 70)
print("  STEP 5: Creation des Dashboards")
print("=" * 70)

dashboards = [
    # Cat #13: Evolution CA Mensuelle -> DASH
    {
        "nom": "Evolution CA Mensuelle",
        "description": "Courbe d'evolution du CA avec comparatif N-1",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_evol_kpi_ca", "type": "kpi", "title": "CA HT Total",
                "x": 0, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_CA_MENSUEL", "dataSourceOrigin": "template", "value_field": "CA HT", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#3b82f6", "subtitle": "Chiffre d'Affaires HT"}
            },
            {
                "id": "w_evol_kpi_marge", "type": "kpi", "title": "Marge Brute",
                "x": 3, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_CA_MENSUEL", "dataSourceOrigin": "template", "value_field": "Marge Brute", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#10b981", "subtitle": "Marge Brute Totale"}
            },
            {
                "id": "w_evol_kpi_docs", "type": "kpi", "title": "Nb Documents",
                "x": 6, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_CA_MENSUEL", "dataSourceOrigin": "template", "value_field": "Nb Documents", "aggregation": "SUM", "kpi_color": "#f59e0b", "subtitle": "Documents de vente"}
            },
            {
                "id": "w_evol_kpi_taux", "type": "kpi", "title": "Taux Marge Moyen",
                "x": 9, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_CA_MENSUEL", "dataSourceOrigin": "template", "value_field": "Taux Marge %", "aggregation": "AVG", "suffix": " %", "kpi_color": "#8b5cf6", "subtitle": "Marge moyenne"}
            },
            {
                "id": "w_evol_chart_ca", "type": "chart_bar", "title": "CA HT par Mois",
                "x": 0, "y": 3, "w": 8, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_CA_MENSUEL", "dataSourceOrigin": "template", "x_field": "Periode", "value_field": "CA HT", "aggregation": "SUM", "show_data_labels": False, "show_grid": True}
            },
            {
                "id": "w_evol_chart_marge", "type": "chart_line", "title": "Evolution Marge Mensuelle",
                "x": 8, "y": 3, "w": 4, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_CA_MENSUEL", "dataSourceOrigin": "template", "x_field": "Periode", "value_field": "Marge Brute", "aggregation": "SUM", "color": "#10b981"}
            },
            {
                "id": "w_evol_table", "type": "table", "title": "Detail Mensuel",
                "x": 0, "y": 9, "w": 12, "h": 5,
                "config": {"dataSourceCode": "DS_VTE_CA_MENSUEL", "dataSourceOrigin": "template", "sort_field": "Annee", "sort_direction": "desc", "limit_rows": 24}
            },
        ],
    },
    # Cat #14: Top 20 Clients -> DASH
    {
        "nom": "Top 20 Clients",
        "description": "Classement clients par CA avec graphe Pareto",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_top_cli_chart", "type": "chart_bar", "title": "Top 20 Clients par CA HT",
                "x": 0, "y": 0, "w": 8, "h": 7,
                "config": {"dataSourceCode": "DS_VTE_TOP_CLIENTS", "dataSourceOrigin": "template", "x_field": "Client", "value_field": "CA HT", "aggregation": "SUM", "show_data_labels": True}
            },
            {
                "id": "w_top_cli_pie", "type": "chart_pie", "title": "Repartition CA Top 20",
                "x": 8, "y": 0, "w": 4, "h": 7,
                "config": {"dataSourceCode": "DS_VTE_TOP_CLIENTS", "dataSourceOrigin": "template", "x_field": "Client", "value_field": "CA HT", "aggregation": "SUM"}
            },
            {
                "id": "w_top_cli_table", "type": "table", "title": "Detail Top 20 Clients",
                "x": 0, "y": 7, "w": 12, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_TOP_CLIENTS", "dataSourceOrigin": "template", "sort_field": "CA HT", "sort_direction": "desc", "limit_rows": 20}
            },
        ],
    },
    # Cat #15: Top 20 Articles -> DASH
    {
        "nom": "Top 20 Articles",
        "description": "Produits les plus vendus en valeur et quantite",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_top_art_chart", "type": "chart_bar", "title": "Top 20 Articles par CA HT",
                "x": 0, "y": 0, "w": 8, "h": 7,
                "config": {"dataSourceCode": "DS_VTE_TOP_ARTICLES", "dataSourceOrigin": "template", "x_field": "Designation", "value_field": "CA HT", "aggregation": "SUM", "show_data_labels": True}
            },
            {
                "id": "w_top_art_pie", "type": "chart_pie", "title": "Repartition CA Articles",
                "x": 8, "y": 0, "w": 4, "h": 7,
                "config": {"dataSourceCode": "DS_VTE_TOP_ARTICLES", "dataSourceOrigin": "template", "x_field": "Designation", "value_field": "CA HT", "aggregation": "SUM"}
            },
            {
                "id": "w_top_art_table", "type": "table", "title": "Detail Top 20 Articles",
                "x": 0, "y": 7, "w": 12, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_TOP_ARTICLES", "dataSourceOrigin": "template", "sort_field": "CA HT", "sort_direction": "desc", "limit_rows": 20}
            },
        ],
    },
    # Cat #18: Comparatif N / N-1 -> DASH
    {
        "nom": "Comparatif N / N-1",
        "description": "Tableaux de bord comparatif annee en cours vs precedente",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_comp_kpi_n", "type": "kpi", "title": "CA HT Annee N",
                "x": 0, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_COMPARATIF", "dataSourceOrigin": "template", "value_field": "CA HT N", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#3b82f6", "subtitle": "Annee en cours"}
            },
            {
                "id": "w_comp_kpi_n1", "type": "kpi", "title": "CA HT Annee N-1",
                "x": 3, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_COMPARATIF", "dataSourceOrigin": "template", "value_field": "CA HT N-1", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#6b7280", "subtitle": "Annee precedente"}
            },
            {
                "id": "w_comp_kpi_ecart", "type": "kpi", "title": "Ecart",
                "x": 6, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_COMPARATIF", "dataSourceOrigin": "template", "value_field": "Ecart", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#10b981", "subtitle": "Ecart N vs N-1"}
            },
            {
                "id": "w_comp_kpi_evol", "type": "kpi", "title": "Evolution %",
                "x": 9, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_COMPARATIF", "dataSourceOrigin": "template", "value_field": "Evolution %", "aggregation": "AVG", "suffix": " %", "kpi_color": "#f59e0b", "subtitle": "Variation"}
            },
            {
                "id": "w_comp_chart", "type": "chart_bar", "title": "CA Mensuel N vs N-1",
                "x": 0, "y": 3, "w": 12, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_COMPARATIF", "dataSourceOrigin": "template", "x_field": "Nom Mois", "value_field": "CA HT N", "aggregation": "SUM", "show_data_labels": False}
            },
            {
                "id": "w_comp_table", "type": "table", "title": "Detail Comparatif Mensuel",
                "x": 0, "y": 9, "w": 12, "h": 5,
                "config": {"dataSourceCode": "DS_VTE_COMPARATIF", "dataSourceOrigin": "template", "sort_field": "Mois", "sort_direction": "asc", "limit_rows": 12}
            },
        ],
    },
    # Cat #21: Analyse RFM Clients -> DASH
    {
        "nom": "Analyse RFM Clients",
        "description": "Segmentation Recence x Frequence x Montant pour ciblage marketing",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_rfm_kpi_champ", "type": "kpi", "title": "Champions",
                "x": 0, "y": 0, "w": 2, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_RFM", "dataSourceOrigin": "template", "value_field": "Code Client", "aggregation": "COUNT", "kpi_color": "#10b981", "subtitle": "Clients Champions"}
            },
            {
                "id": "w_rfm_kpi_fid", "type": "kpi", "title": "Fideles",
                "x": 2, "y": 0, "w": 2, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_RFM", "dataSourceOrigin": "template", "value_field": "Code Client", "aggregation": "COUNT", "kpi_color": "#3b82f6", "subtitle": "Clients Fideles"}
            },
            {
                "id": "w_rfm_kpi_risque", "type": "kpi", "title": "A Risque",
                "x": 4, "y": 0, "w": 2, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_RFM", "dataSourceOrigin": "template", "value_field": "Code Client", "aggregation": "COUNT", "kpi_color": "#f59e0b", "subtitle": "Clients a Risque"}
            },
            {
                "id": "w_rfm_kpi_perdu", "type": "kpi", "title": "Perdus",
                "x": 6, "y": 0, "w": 2, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_RFM", "dataSourceOrigin": "template", "value_field": "Code Client", "aggregation": "COUNT", "kpi_color": "#ef4444", "subtitle": "Clients Perdus"}
            },
            {
                "id": "w_rfm_kpi_ca", "type": "kpi", "title": "CA Total",
                "x": 8, "y": 0, "w": 4, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_RFM", "dataSourceOrigin": "template", "value_field": "Montant", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#8b5cf6", "subtitle": "CA Total Segmente"}
            },
            {
                "id": "w_rfm_pie", "type": "chart_pie", "title": "Repartition par Segment",
                "x": 0, "y": 3, "w": 5, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_RFM", "dataSourceOrigin": "template", "x_field": "Segment", "value_field": "Montant", "aggregation": "SUM"}
            },
            {
                "id": "w_rfm_bar", "type": "chart_bar", "title": "CA par Segment",
                "x": 5, "y": 3, "w": 7, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_RFM", "dataSourceOrigin": "template", "x_field": "Segment", "value_field": "Montant", "aggregation": "SUM", "show_data_labels": True}
            },
            {
                "id": "w_rfm_table", "type": "table", "title": "Detail Clients RFM",
                "x": 0, "y": 9, "w": 12, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_RFM", "dataSourceOrigin": "template", "sort_field": "Montant", "sort_direction": "desc", "limit_rows": 50}
            },
        ],
    },
    # Cat #25: Clients a Risque de Churn -> DASH
    {
        "nom": "Clients a Risque de Churn",
        "description": "Clients dont la frequence/valeur d'achat diminue avec alerte",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_churn_kpi_perdu", "type": "kpi", "title": "Clients PERDU",
                "x": 0, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_CHURN", "dataSourceOrigin": "template", "value_field": "Code Client", "aggregation": "COUNT", "kpi_color": "#ef4444", "subtitle": "Statut PERDU"}
            },
            {
                "id": "w_churn_kpi_risque", "type": "kpi", "title": "Risque Eleve",
                "x": 3, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_CHURN", "dataSourceOrigin": "template", "value_field": "Code Client", "aggregation": "COUNT", "kpi_color": "#f59e0b", "subtitle": "Risque ELEVE"}
            },
            {
                "id": "w_churn_kpi_ca", "type": "kpi", "title": "CA 6M Precedent",
                "x": 6, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_CHURN", "dataSourceOrigin": "template", "value_field": "CA 6M Precedent", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#6b7280", "subtitle": "CA perdu potentiel"}
            },
            {
                "id": "w_churn_kpi_evol", "type": "kpi", "title": "Evolution Moy",
                "x": 9, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_CHURN", "dataSourceOrigin": "template", "value_field": "Evolution CA %", "aggregation": "AVG", "suffix": " %", "kpi_color": "#8b5cf6", "subtitle": "Evolution CA moyenne"}
            },
            {
                "id": "w_churn_pie", "type": "chart_pie", "title": "Repartition par Statut Risque",
                "x": 0, "y": 3, "w": 5, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_CHURN", "dataSourceOrigin": "template", "x_field": "Statut Risque", "value_field": "CA 6M Precedent", "aggregation": "SUM"}
            },
            {
                "id": "w_churn_bar", "type": "chart_bar", "title": "CA Perdu par Statut",
                "x": 5, "y": 3, "w": 7, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_CHURN", "dataSourceOrigin": "template", "x_field": "Statut Risque", "value_field": "CA 6M Precedent", "aggregation": "SUM", "show_data_labels": True}
            },
            {
                "id": "w_churn_table", "type": "table", "title": "Detail Clients a Risque",
                "x": 0, "y": 9, "w": 12, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_CHURN", "dataSourceOrigin": "template", "sort_field": "CA 6M Precedent", "sort_direction": "desc", "limit_rows": 50}
            },
        ],
    },
    # Cat #27: Taux de Service Client -> DASH
    {
        "nom": "Taux de Service Client",
        "description": "% commandes livrees a temps, completes, sans retour",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_tserv_kpi_retour", "type": "kpi", "title": "Taux Retour Moyen",
                "x": 0, "y": 0, "w": 4, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_TAUX_SERVICE", "dataSourceOrigin": "template", "value_field": "Taux Retour %", "aggregation": "AVG", "suffix": " %", "kpi_color": "#ef4444", "subtitle": "Taux de retour"}
            },
            {
                "id": "w_tserv_kpi_ca", "type": "kpi", "title": "CA HT Net Total",
                "x": 4, "y": 0, "w": 4, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_TAUX_SERVICE", "dataSourceOrigin": "template", "value_field": "CA HT Net", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#3b82f6", "subtitle": "CA net"}
            },
            {
                "id": "w_tserv_kpi_ret_mnt", "type": "kpi", "title": "Montant Retours",
                "x": 8, "y": 0, "w": 4, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_TAUX_SERVICE", "dataSourceOrigin": "template", "value_field": "Montant Retours", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#f59e0b", "subtitle": "Total retours"}
            },
            {
                "id": "w_tserv_chart", "type": "chart_bar", "title": "Taux Retour par Client",
                "x": 0, "y": 3, "w": 12, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_TAUX_SERVICE", "dataSourceOrigin": "template", "x_field": "Client", "value_field": "Taux Retour %", "aggregation": "SUM", "show_data_labels": False}
            },
            {
                "id": "w_tserv_table", "type": "table", "title": "Detail Service par Client",
                "x": 0, "y": 9, "w": 12, "h": 5,
                "config": {"dataSourceCode": "DS_VTE_TAUX_SERVICE", "dataSourceOrigin": "template", "sort_field": "Taux Retour %", "sort_direction": "desc", "limit_rows": 50}
            },
        ],
    },
    # Cat #28: Analyse des Retours -> DASH
    {
        "nom": "Analyse des Retours",
        "description": "Taux de retour par article/client/motif avec tendance",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_ret_kpi_mnt", "type": "kpi", "title": "Montant HT Retours",
                "x": 0, "y": 0, "w": 4, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_ANALYSE_RETOURS", "dataSourceOrigin": "template", "value_field": "Montant HT Retour", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#ef4444", "subtitle": "Total retours"}
            },
            {
                "id": "w_ret_kpi_qte", "type": "kpi", "title": "Qte Retournee",
                "x": 4, "y": 0, "w": 4, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_ANALYSE_RETOURS", "dataSourceOrigin": "template", "value_field": "Quantite Retournee", "aggregation": "SUM", "kpi_color": "#f59e0b", "subtitle": "Quantite"}
            },
            {
                "id": "w_ret_kpi_docs", "type": "kpi", "title": "Nb Docs Retour",
                "x": 8, "y": 0, "w": 4, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_ANALYSE_RETOURS", "dataSourceOrigin": "template", "value_field": "Nb Documents Retour", "aggregation": "SUM", "kpi_color": "#6b7280", "subtitle": "Documents"}
            },
            {
                "id": "w_ret_bar_art", "type": "chart_bar", "title": "Retours par Article",
                "x": 0, "y": 3, "w": 7, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_ANALYSE_RETOURS", "dataSourceOrigin": "template", "x_field": "Designation", "value_field": "Montant HT Retour", "aggregation": "SUM", "show_data_labels": False}
            },
            {
                "id": "w_ret_pie_cli", "type": "chart_pie", "title": "Retours par Client",
                "x": 7, "y": 3, "w": 5, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_ANALYSE_RETOURS", "dataSourceOrigin": "template", "x_field": "Client", "value_field": "Montant HT Retour", "aggregation": "SUM"}
            },
            {
                "id": "w_ret_table", "type": "table", "title": "Detail des Retours",
                "x": 0, "y": 9, "w": 12, "h": 5,
                "config": {"dataSourceCode": "DS_VTE_ANALYSE_RETOURS", "dataSourceOrigin": "template", "sort_field": "Montant HT Retour", "sort_direction": "desc", "limit_rows": 50}
            },
        ],
    },
    # Cat #32: Fidelite Clients -> DASH
    {
        "nom": "Fidelite Clients",
        "description": "Anciennete, regularite, evolution CA par tranche de fidelite",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_fid_kpi_ca", "type": "kpi", "title": "CA HT Total",
                "x": 0, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_FIDELITE", "dataSourceOrigin": "template", "value_field": "CA HT Total", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#3b82f6", "subtitle": "CA Clients Fideles"}
            },
            {
                "id": "w_fid_kpi_clients", "type": "kpi", "title": "Nb Clients",
                "x": 3, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_FIDELITE", "dataSourceOrigin": "template", "value_field": "Code Client", "aggregation": "COUNT", "kpi_color": "#10b981", "subtitle": "Clients analyses"}
            },
            {
                "id": "w_fid_kpi_anc", "type": "kpi", "title": "Anciennete Moyenne",
                "x": 6, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_FIDELITE", "dataSourceOrigin": "template", "value_field": "Anciennete Mois", "aggregation": "AVG", "suffix": " mois", "kpi_color": "#8b5cf6", "subtitle": "Anciennete moy."}
            },
            {
                "id": "w_fid_kpi_camm", "type": "kpi", "title": "CA Mensuel Moyen",
                "x": 9, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_FIDELITE", "dataSourceOrigin": "template", "value_field": "CA Moyen Mensuel", "aggregation": "AVG", "suffix": " DH", "kpi_color": "#f59e0b", "subtitle": "CA mensuel moy."}
            },
            {
                "id": "w_fid_pie", "type": "chart_pie", "title": "Repartition par Segment Fidelite",
                "x": 0, "y": 3, "w": 5, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_FIDELITE", "dataSourceOrigin": "template", "x_field": "Segment Fidelite", "value_field": "CA HT Total", "aggregation": "SUM"}
            },
            {
                "id": "w_fid_bar", "type": "chart_bar", "title": "CA par Segment Fidelite",
                "x": 5, "y": 3, "w": 7, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_FIDELITE", "dataSourceOrigin": "template", "x_field": "Segment Fidelite", "value_field": "CA HT Total", "aggregation": "SUM", "show_data_labels": True}
            },
            {
                "id": "w_fid_table", "type": "table", "title": "Detail Fidelite Clients",
                "x": 0, "y": 9, "w": 12, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_FIDELITE", "dataSourceOrigin": "template", "sort_field": "CA HT Total", "sort_direction": "desc", "limit_rows": 50}
            },
        ],
    },
    # Cat #34: Performance des Devis -> DASH
    {
        "nom": "Performance des Devis",
        "description": "Delai moyen de conversion, taux d'acceptation, montant moyen",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_devis_kpi_nb", "type": "kpi", "title": "Nb Devis",
                "x": 0, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_PERF_DEVIS", "dataSourceOrigin": "template", "value_field": "Nb Devis", "aggregation": "SUM", "kpi_color": "#3b82f6", "subtitle": "Total devis"}
            },
            {
                "id": "w_devis_kpi_conv", "type": "kpi", "title": "Taux Conversion",
                "x": 3, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_PERF_DEVIS", "dataSourceOrigin": "template", "value_field": "Taux Conversion %", "aggregation": "AVG", "suffix": " %", "kpi_color": "#10b981", "subtitle": "Devis -> BL"}
            },
            {
                "id": "w_devis_kpi_mnt", "type": "kpi", "title": "Montant Total",
                "x": 6, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_PERF_DEVIS", "dataSourceOrigin": "template", "value_field": "Montant Total Devis", "aggregation": "SUM", "suffix": " DH", "kpi_color": "#f59e0b", "subtitle": "Montant devis"}
            },
            {
                "id": "w_devis_kpi_moy", "type": "kpi", "title": "Montant Moyen",
                "x": 9, "y": 0, "w": 3, "h": 3,
                "config": {"dataSourceCode": "DS_VTE_PERF_DEVIS", "dataSourceOrigin": "template", "value_field": "Montant Moyen Devis", "aggregation": "AVG", "suffix": " DH", "kpi_color": "#8b5cf6", "subtitle": "Moy. par devis"}
            },
            {
                "id": "w_devis_bar", "type": "chart_bar", "title": "Nb Devis par Commercial",
                "x": 0, "y": 3, "w": 7, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_PERF_DEVIS", "dataSourceOrigin": "template", "x_field": "Commercial", "value_field": "Nb Devis", "aggregation": "SUM", "show_data_labels": True}
            },
            {
                "id": "w_devis_pie", "type": "chart_pie", "title": "Montant Devis par Commercial",
                "x": 7, "y": 3, "w": 5, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_PERF_DEVIS", "dataSourceOrigin": "template", "x_field": "Commercial", "value_field": "Montant Total Devis", "aggregation": "SUM"}
            },
            {
                "id": "w_devis_table", "type": "table", "title": "Detail Performance Devis",
                "x": 0, "y": 9, "w": 12, "h": 5,
                "config": {"dataSourceCode": "DS_VTE_PERF_DEVIS", "dataSourceOrigin": "template", "sort_field": "Nb Devis", "sort_direction": "desc", "limit_rows": 50}
            },
        ],
    },
    # Cat #22: Saisonnalite des Ventes -> DASH (visual version - pivot has the cross-table)
    {
        "nom": "Saisonnalite des Ventes (Dashboard)",
        "description": "Detection visuelle des pics/creux par article et famille sur 3 ans",
        "config": json.dumps({"refresh_interval": 0}),
        "widgets": [
            {
                "id": "w_saison_chart", "type": "chart_line", "title": "Evolution CA 3 Ans",
                "x": 0, "y": 0, "w": 12, "h": 7,
                "config": {"dataSourceCode": "DS_VTE_SAISONNALITE", "dataSourceOrigin": "template", "x_field": "Nom Mois", "value_field": "CA N", "aggregation": "SUM", "color": "#3b82f6"}
            },
            {
                "id": "w_saison_table", "type": "table", "title": "Detail Saisonnalite",
                "x": 0, "y": 7, "w": 12, "h": 6,
                "config": {"dataSourceCode": "DS_VTE_SAISONNALITE", "dataSourceOrigin": "template", "sort_field": "Mois", "sort_direction": "asc", "limit_rows": 50}
            },
        ],
    },
]

dash_ids = {}
for d in dashboards:
    # Use the first widget's dataSourceCode as key
    first_ds = d["widgets"][0]["config"].get("dataSourceCode", "")
    cursor.execute("""
        INSERT INTO APP_Dashboards (nom, description, config, widgets, is_public, created_by, actif)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, 1, 1, 1)
    """, (d["nom"], d["description"], d["config"], json.dumps(d["widgets"])))
    did = cursor.fetchone()[0]
    dash_ids[d["nom"]] = did
    print(f"  Dashboard {did}: {d['nom']}")

print(f"\n  Total Dashboards: {len(dash_ids)}")
print()

# =============================================================================
#  STEP 6: CREATE MENUS
# =============================================================================
print("=" * 70)
print("  STEP 6: Creation des Menus")
print("=" * 70)

# Root menu
cursor.execute("""
    INSERT INTO APP_Menus (nom, code, icon, parent_id, ordre, type, actif)
    OUTPUT INSERTED.id
    VALUES (N'Ventes', 'MENU_VENTES', 'ShoppingCart', NULL, 1, 'folder', 1)
""")
root_id = cursor.fetchone()[0]
print(f"  Menu racine: {root_id} (Ventes)")

# Sub-folder: Documents Ventes
cursor.execute("""
    INSERT INTO APP_Menus (nom, code, icon, parent_id, ordre, type, actif)
    OUTPUT INSERTED.id
    VALUES (N'Documents Ventes', 'MENU_VTE_DOCS', 'FileText', ?, 1, 'folder', 1)
""", (root_id,))
folder_docs = cursor.fetchone()[0]
print(f"  Dossier Documents: {folder_docs}")

# Sub-folder: Analyses Ventes
cursor.execute("""
    INSERT INTO APP_Menus (nom, code, icon, parent_id, ordre, type, actif)
    OUTPUT INSERTED.id
    VALUES (N'Analyses Ventes', 'MENU_VTE_ANALYSES', 'BarChart2', ?, 2, 'folder', 1)
""", (root_id,))
folder_analyses = cursor.fetchone()[0]
print(f"  Dossier Analyses: {folder_analyses}")

# Sub-folder: Rapports Avances
cursor.execute("""
    INSERT INTO APP_Menus (nom, code, icon, parent_id, ordre, type, actif)
    OUTPUT INSERTED.id
    VALUES (N'Rapports Avances', 'MENU_VTE_AVANCES', 'TrendingUp', ?, 3, 'folder', 1)
""", (root_id,))
folder_avances = cursor.fetchone()[0]
print(f"  Dossier Avances: {folder_avances}")

# Sub-folder: Complementaires
cursor.execute("""
    INSERT INTO APP_Menus (nom, code, icon, parent_id, ordre, type, actif)
    OUTPUT INSERTED.id
    VALUES (N'Rapports Complementaires', 'MENU_VTE_COMP', 'Database', ?, 4, 'folder', 1)
""", (root_id,))
folder_comp = cursor.fetchone()[0]
print(f"  Dossier Complementaires: {folder_comp}")

# Now create leaf menus
menu_count = 0

# --- DOCUMENTS VENTES (7 GridViews) ---
doc_menus = [
    ("Factures de Ventes", "DS_VTE_FACTURES", "gridview"),
    ("Bons de Livraison", "DS_VTE_BL", "gridview"),
    ("Bons de Commande", "DS_VTE_BC", "gridview"),
    ("Devis", "DS_VTE_DEVIS", "gridview"),
    ("Avoirs", "DS_VTE_AVOIRS", "gridview"),
    ("Bons de Retour", "DS_VTE_RETOURS", "gridview"),
    ("Preparations de Livraison", "DS_VTE_PL", "gridview"),
]
for i, (nom, ds_code, mtype) in enumerate(doc_menus, 1):
    tid = gv_ids[ds_code]
    cursor.execute("""
        INSERT INTO APP_Menus (nom, code, parent_id, ordre, type, target_id, actif)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (nom, f"MENU_{ds_code}", folder_docs, i, mtype, tid))
    menu_count += 1
    print(f"    [{mtype:10s}] {nom} -> target={tid}")

# --- ANALYSES VENTES (5 Pivots + 1 Grid + 3 Dash) ---
analysis_menus = [
    ("CA par Client", "DS_VTE_CA_CLIENT", "pivot-v2", pivot_ids),
    ("CA par Article", "DS_VTE_CA_ARTICLE", "pivot-v2", pivot_ids),
    ("CA par Commercial", "DS_VTE_CA_COMMERCIAL", "pivot-v2", pivot_ids),
    ("CA par Region / Ville", "DS_VTE_CA_REGION", "pivot-v2", pivot_ids),
    ("CA par Famille Article", "DS_VTE_CA_FAMILLE", "pivot-v2", pivot_ids),
    ("Evolution CA Mensuelle", "Evolution CA Mensuelle", "dashboard", dash_ids),
    ("Top 20 Clients", "Top 20 Clients", "dashboard", dash_ids),
    ("Top 20 Articles", "Top 20 Articles", "dashboard", dash_ids),
    ("Analyse Marges", "DS_VTE_MARGES", "pivot-v2", pivot_ids),
    ("Commandes en Cours", "DS_VTE_CMD_EN_COURS", "gridview", gv_ids),
    ("Comparatif N / N-1", "Comparatif N / N-1", "dashboard", dash_ids),
    ("CA par Mode de Reglement", "DS_VTE_CA_MODE_REGLEMENT", "pivot-v2", pivot_ids),
    ("Statistiques Remises", "DS_VTE_REMISES", "pivot-v2", pivot_ids),
]
for i, (nom, key, mtype, id_map) in enumerate(analysis_menus, 1):
    tid = id_map[key]
    cursor.execute("""
        INSERT INTO APP_Menus (nom, code, parent_id, ordre, type, target_id, actif)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (nom, f"MENU_VTE_AN_{i}", folder_analyses, i, mtype, tid))
    menu_count += 1
    print(f"    [{mtype:10s}] {nom} -> target={tid}")

# --- RAPPORTS AVANCES (4 Dash + 3 Pivot + 4 Dash) ---
avance_menus = [
    ("Analyse RFM Clients", "Analyse RFM Clients", "dashboard", dash_ids),
    ("Saisonnalite des Ventes", "Saisonnalite des Ventes (Dashboard)", "dashboard", dash_ids),
    ("Panier Moyen par Client", "DS_VTE_PANIER_MOYEN", "pivot-v2", pivot_ids),
    ("Clients a Risque de Churn", "Clients a Risque de Churn", "dashboard", dash_ids),
    ("Analyse des Prix de Vente", "DS_VTE_ANALYSE_PRIX", "pivot-v2", pivot_ids),
    ("Taux de Service Client", "Taux de Service Client", "dashboard", dash_ids),
    ("Analyse des Retours", "Analyse des Retours", "dashboard", dash_ids),
    ("Rentabilite par Client", "DS_VTE_RENTABILITE_CLIENT", "pivot-v2", pivot_ids),
    ("Saisonnalite (Pivot)", "DS_VTE_SAISONNALITE", "pivot-v2", pivot_ids),
    ("Fidelite Clients", "Fidelite Clients", "dashboard", dash_ids),
    ("Performance des Devis", "Performance des Devis", "dashboard", dash_ids),
]
for i, (nom, key, mtype, id_map) in enumerate(avance_menus, 1):
    tid = id_map[key]
    cursor.execute("""
        INSERT INTO APP_Menus (nom, code, parent_id, ordre, type, target_id, actif)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (nom, f"MENU_VTE_AV_{i}", folder_avances, i, mtype, tid))
    menu_count += 1
    print(f"    [{mtype:10s}] {nom} -> target={tid}")

# --- COMPLEMENTAIRES (Extra GridViews) ---
comp_menus = [
    ("Ventes Detail Complet", "DS_VTE_DETAIL_COMPLET", "gridview", gv_ids),
    ("Ventes par Type Document", "DS_VTE_PAR_TYPE_DOC", "gridview", gv_ids),
    ("Clients Inactifs", "DS_VTE_CLIENTS_INACTIFS", "gridview", gv_ids),
    ("CA par Depot", "DS_VTE_CA_DEPOT", "gridview", gv_ids),
    ("CA par Affaire", "DS_VTE_CA_AFFAIRE", "gridview", gv_ids),
]
for i, (nom, ds_code, mtype, id_map) in enumerate(comp_menus, 1):
    tid = id_map[ds_code]
    cursor.execute("""
        INSERT INTO APP_Menus (nom, code, parent_id, ordre, type, target_id, actif)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (nom, f"MENU_VTE_COMP_{i}", folder_comp, i, mtype, tid))
    menu_count += 1
    print(f"    [{mtype:10s}] {nom} -> target={tid}")

print(f"\n  Total menus feuilles: {menu_count}")
print(f"  Total menus (avec dossiers): {menu_count + 5}")

# =============================================================================
#  SUMMARY
# =============================================================================
print()
print("=" * 70)
print("  RESUME FINAL")
print("=" * 70)
print(f"  GridViews crees:   {len(gv_ids)}")
print(f"  Pivots crees:      {len(pivot_ids)}")
print(f"  Dashboards crees:  {len(dash_ids)}")
print(f"  Menus crees:       {menu_count + 5}")
print(f"  DS Templates:      {len(tmpl)} (inchanges)")
print()
print(f"  Types: {len(gv_ids)} GRID | {len(pivot_ids)} PIVOT | {len(dash_ids)} DASH")
print("=" * 70)

conn.close()
print("\nTermine !")
