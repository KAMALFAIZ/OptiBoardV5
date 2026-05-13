"""Applique la requête complète Factures avec tous les champs Sage."""
import sys, json, pyodbc
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONN = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(CONN, autocommit=True)
cur = conn.cursor()

QUERY = """SELECT
    li.[societe]                     AS [Societe],
    li.[Type Document],
    li.[N° Pièce]         AS [Num Piece],
    li.[Date document]               AS [Date Document],
    li.[N° Pièce BL]      AS [Num BL],
    li.[Date BL],
    li.[Code client]                 AS [Code Client],
    li.[Intitulé client]       AS [Client],
    en.[Nom représentant]      AS [Commercial],
    li.[Code article]                AS [Code Article],
    li.[Désignation ligne]     AS [Designation],
    li.[N° Série/Lot]     AS [Lot Serie],
    li.[Référence]        AS [Reference],
    li.[Code d'affaire]              AS [Code Affaire],
    li.[Intitulé affaire]      AS [Affaire],
    li.[Catalogue 1]                 AS [Famille],
    li.[Catalogue 2]                 AS [Sous Famille],
    li.[Gamme 1]                     AS [Gamme1],
    li.[Gamme 2]                     AS [Gamme2],
    li.[Quantité]              AS [Quantite],
    li.[Colisage],
    li.[Prix unitaire]               AS [PU HT],
    li.[CMUP]             AS [Prix Revient],
    li.[PU Devise]                   AS [PU Devise],
    li.[Remise 1]                    AS [Remise1],
    li.[Remise 2]                    AS [Remise2],
    li.[Taxe1],
    li.[Type taux taxe 1]            AS [Type Taux Taxe],
    li.[Type taxe 1]                 AS [Type Taxe],
    li.[Montant HT Net]              AS [Montant HT],
    li.[Montant TTC Net]             AS [Montant TTC],
    li.[Poids net]                   AS [Poids Net],
    li.[Code dépôt]       AS [Code Depot],
    li.[Intitulé dépôt]  AS [Depot],
    li.[N° Pièce BC]      AS [Num BC],
    li.[Date BC],
    en.[Statut],
    en.[Statut validé]          AS [Statut Valide],
    en.[Souche],
    en.[Valorise CA],
    en.[Encours],
    en.[Entête 1]              AS [Entete1],
    en.[Entête 2]              AS [Entete2],
    en.[Entête 3]              AS [Entete3],
    en.[Entête 4]              AS [Entete4],
    en.[Intitulé tiers payeur]  AS [Tiers Payeur],
    en.[Devise],
    en.[Catégorie Comptable]   AS [Categorie Comptable],
    en.[Cours]
FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe]        = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce]      = en.[N° pièce]
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND TRY_CAST(li.[Date document] AS DATE) BETWEEN CAST(@dateDebut AS DATE) AND CAST(@dateFin AS DATE)
  AND (@societe IS NULL OR li.[societe] = @societe)
  AND (@commercial IS NULL OR en.[Nom représentant] = @commercial)
ORDER BY li.[Date document] DESC, li.[N° Pièce]"""

COLUMNS = [
    {"field": "Societe",            "header": "Societe",           "width": 80},
    {"field": "Type Document",      "header": "Type",              "width": 130},
    {"field": "Num Piece",          "header": "N° Piece",          "width": 120},
    {"field": "Date Document",      "header": "Date Facture",      "width": 110, "type": "date"},
    {"field": "Num BL",             "header": "N° BL",             "width": 110, "visible": False},
    {"field": "Date BL",            "header": "Date BL",           "width": 100, "type": "date", "visible": False},
    {"field": "Num BC",             "header": "N° BC",             "width": 110, "visible": False},
    {"field": "Date BC",            "header": "Date BC",           "width": 100, "type": "date", "visible": False},
    {"field": "Code Client",        "header": "Code Client",       "width": 100},
    {"field": "Client",             "header": "Client",            "width": 190},
    {"field": "Tiers Payeur",       "header": "Tiers Payeur",      "width": 140, "visible": False},
    {"field": "Commercial",         "header": "Commercial",        "width": 130},
    {"field": "Code Article",       "header": "Code Article",      "width": 110},
    {"field": "Designation",        "header": "Designation",       "width": 200},
    {"field": "Lot Serie",          "header": "N° Lot/Série",      "width": 120},
    {"field": "Reference",          "header": "Référence",         "width": 110, "visible": False},
    {"field": "Code Affaire",       "header": "Code Affaire",      "width": 100, "visible": False},
    {"field": "Affaire",            "header": "Affaire",           "width": 160, "visible": False},
    {"field": "Famille",            "header": "Famille",           "width": 120},
    {"field": "Sous Famille",       "header": "Sous Famille",      "width": 120, "visible": False},
    {"field": "Gamme1",             "header": "Gamme 1",           "width": 110, "visible": False},
    {"field": "Gamme2",             "header": "Gamme 2",           "width": 110, "visible": False},
    {"field": "Quantite",           "header": "Qté",               "width": 80,  "type": "number"},
    {"field": "Colisage",           "header": "Colisage",          "width": 80,  "type": "number", "visible": False},
    {"field": "PU HT",              "header": "PU HT",             "width": 110, "type": "number", "format": "#,##0.00"},
    {"field": "Prix Revient",       "header": "Prix Revient",      "width": 110, "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "PU Devise",          "header": "PU Devise",         "width": 100, "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "Remise1",            "header": "Remise 1",          "width": 80,  "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "Remise2",            "header": "Remise 2",          "width": 80,  "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "Taxe1",              "header": "Taxe",              "width": 80,  "visible": False},
    {"field": "Type Taux Taxe",     "header": "Type Taux Taxe",    "width": 120, "visible": False},
    {"field": "Type Taxe",          "header": "Type Taxe",         "width": 100, "visible": False},
    {"field": "Montant HT",         "header": "Montant HT",        "width": 120, "type": "number", "format": "#,##0.00"},
    {"field": "Montant TTC",        "header": "Montant TTC",       "width": 120, "type": "number", "format": "#,##0.00"},
    {"field": "Poids Net",          "header": "Poids Net",         "width": 90,  "type": "number", "visible": False},
    {"field": "Code Depot",         "header": "Code Dépôt",        "width": 90,  "visible": False},
    {"field": "Depot",              "header": "Dépôt",             "width": 130},
    {"field": "Statut",             "header": "Statut",            "width": 100},
    {"field": "Statut Valide",      "header": "Statut Validé",     "width": 110, "visible": False},
    {"field": "Souche",             "header": "Souche",            "width": 80,  "visible": False},
    {"field": "Valorise CA",        "header": "Valorisé CA",       "width": 90,  "visible": False},
    {"field": "Encours",            "header": "Encours",           "width": 90,  "visible": False},
    {"field": "Devise",             "header": "Devise",            "width": 70,  "visible": False},
    {"field": "Cours",              "header": "Cours",             "width": 70,  "type": "number", "visible": False},
    {"field": "Categorie Comptable","header": "Cat. Comptable",    "width": 120, "visible": False},
    {"field": "Entete1",            "header": "Entête 1",          "width": 120, "visible": False},
    {"field": "Entete2",            "header": "Entête 2",          "width": 120, "visible": False},
    {"field": "Entete3",            "header": "Entête 3",          "width": 120, "visible": False},
    {"field": "Entete4",            "header": "Entête 4",          "width": 120, "visible": False},
]

TOTAL = json.dumps(["Quantite", "Montant HT", "Montant TTC"], ensure_ascii=False)
COLS  = json.dumps(COLUMNS, ensure_ascii=False)

cur.execute(
    "UPDATE APP_DataSources_Templates SET query_template=?, type='SQL', actif=1 WHERE code='DS_VTE_FACTURES'",
    (QUERY,)
)
print(f"[1/3] Template  -> {cur.rowcount} ligne(s)")

cur.execute(
    "UPDATE APP_GridViews SET columns_config=?, total_columns=?, show_totals=1 WHERE data_source_code='DS_VTE_FACTURES'",
    (COLS, TOTAL)
)
print(f"[2/3] GridView  -> {cur.rowcount} ligne(s)")

cur.execute(
    "DELETE p FROM APP_GridView_User_Prefs p "
    "INNER JOIN APP_GridViews g ON p.grid_id = g.id "
    "WHERE g.data_source_code = 'DS_VTE_FACTURES'",
)
print(f"[3/3] Prefs     -> {cur.rowcount} supprimée(s)")

conn.close()
print("Done — Ctrl+Shift+R")
