"""Applique la requête complète BC avec tous les champs Sage."""
import sys, json, pyodbc
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONN = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(CONN, autocommit=True)
cur = conn.cursor()

QUERY = """SELECT
    li.[societe]                    AS [Societe],
    li.[N° Pièce BC]      AS [Num BC],
    li.[Date BC],
    li.[N° Pièce]         AS [Num Piece Origine],
    li.[Type Document],
    li.[Code client]                AS [Code Client],
    li.[Intitulé client]      AS [Client],
    en.[Nom représentant]     AS [Commercial],
    li.[Code article]               AS [Code Article],
    li.[Désignation ligne]    AS [Designation],
    li.[N° Série/Lot]     AS [Lot Serie],
    li.[Quantité BC]           AS [Quantite BC],
    li.[Prix unitaire]              AS [PU HT],
    li.[PU Devise]                  AS [PU Devise],
    li.[Remise 1]                   AS [Remise1],
    li.[Taxe1],
    li.[Type taux taxe 1]           AS [Type Taux Taxe],
    li.[Montant HT Net]             AS [Montant HT],
    li.[Montant TTC Net]            AS [Montant TTC],
    li.[Poids net]                  AS [Poids Net],
    li.[Référence]        AS [Reference],
    li.[Code d'affaire]             AS [Code Affaire],
    li.[Intitulé affaire]     AS [Affaire],
    li.[Catalogue 1]                AS [Famille],
    li.[Catalogue 2]                AS [Catalogue2],
    en.[Dépôt]            AS [Depot],
    en.[Souche],
    en.[Statut],
    en.[Entête 1]              AS [Entete1],
    en.[Entête 2]              AS [Entete2],
    en.[Entête 3]              AS [Entete3],
    en.[Entête 4]              AS [Entete4],
    en.[Intitulé tiers payeur]  AS [Tiers Payeur],
    en.[Devise],
    en.[Cours]
FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe]        = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce]      = en.[N° pièce]
WHERE li.[N° Pièce BC] <> ''
  AND TRY_CAST(li.[Date BC] AS DATE) BETWEEN CAST(@dateDebut AS DATE) AND CAST(@dateFin AS DATE)
  AND (@societe IS NULL OR li.[societe] = @societe)
  AND (@commercial IS NULL OR en.[Nom représentant] = @commercial)
ORDER BY li.[Date BC] DESC"""

COLUMNS = [
    {"field": "Societe",           "header": "Societe",         "width": 80},
    {"field": "Num BC",            "header": "N° BC",           "width": 120},
    {"field": "Date BC",           "header": "Date BC",         "width": 110, "type": "date"},
    {"field": "Num Piece Origine", "header": "N° Piece Orig.",  "width": 120, "visible": False},
    {"field": "Type Document",     "header": "Type",            "width": 130},
    {"field": "Code Client",       "header": "Code Client",     "width": 100},
    {"field": "Client",            "header": "Client",          "width": 190},
    {"field": "Commercial",        "header": "Commercial",      "width": 130},
    {"field": "Code Article",      "header": "Code Article",    "width": 110},
    {"field": "Designation",       "header": "Designation",     "width": 200},
    {"field": "Lot Serie",         "header": "N° Lot/Série",    "width": 120},
    {"field": "Quantite BC",       "header": "Qté BC",          "width": 80,  "type": "number"},
    {"field": "PU HT",             "header": "PU HT",           "width": 110, "type": "number", "format": "#,##0.00"},
    {"field": "PU Devise",         "header": "PU Devise",       "width": 100, "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "Remise1",           "header": "Remise 1",        "width": 80,  "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "Taxe1",             "header": "Taxe",            "width": 80,  "visible": False},
    {"field": "Type Taux Taxe",    "header": "Type Taux Taxe",  "width": 120, "visible": False},
    {"field": "Montant HT",        "header": "Montant HT",      "width": 120, "type": "number", "format": "#,##0.00"},
    {"field": "Montant TTC",       "header": "Montant TTC",     "width": 120, "type": "number", "format": "#,##0.00"},
    {"field": "Poids Net",         "header": "Poids Net",       "width": 90,  "type": "number", "visible": False},
    {"field": "Reference",         "header": "Référence",       "width": 110, "visible": False},
    {"field": "Code Affaire",      "header": "Code Affaire",    "width": 100, "visible": False},
    {"field": "Affaire",           "header": "Affaire",         "width": 160, "visible": False},
    {"field": "Famille",           "header": "Famille",         "width": 120},
    {"field": "Catalogue2",        "header": "Catalogue 2",     "width": 110, "visible": False},
    {"field": "Depot",             "header": "Dépôt",           "width": 130},
    {"field": "Souche",            "header": "Souche",          "width": 80,  "visible": False},
    {"field": "Statut",            "header": "Statut",          "width": 100},
    {"field": "Tiers Payeur",      "header": "Tiers Payeur",    "width": 140, "visible": False},
    {"field": "Devise",            "header": "Devise",          "width": 70,  "visible": False},
    {"field": "Cours",             "header": "Cours",           "width": 70,  "type": "number", "visible": False},
    {"field": "Entete1",           "header": "Entête 1",        "width": 120, "visible": False},
    {"field": "Entete2",           "header": "Entête 2",        "width": 120, "visible": False},
    {"field": "Entete3",           "header": "Entête 3",        "width": 120, "visible": False},
    {"field": "Entete4",           "header": "Entête 4",        "width": 120, "visible": False},
]

TOTAL = json.dumps(["Quantite BC", "Montant HT", "Montant TTC"], ensure_ascii=False)
COLS  = json.dumps(COLUMNS, ensure_ascii=False)

cur.execute(
    "UPDATE APP_DataSources_Templates SET query_template=?, type='SQL', actif=1 WHERE code='DS_VTE_BC'",
    (QUERY,)
)
print(f"[1/3] Template  -> {cur.rowcount} ligne(s)")

cur.execute(
    "UPDATE APP_GridViews SET columns_config=?, total_columns=?, show_totals=1 WHERE data_source_code='DS_VTE_BC'",
    (COLS, TOTAL)
)
print(f"[2/3] GridView  -> {cur.rowcount} ligne(s)")

cur.execute(
    "DELETE p FROM APP_GridView_User_Prefs p "
    "INNER JOIN APP_GridViews g ON p.grid_id = g.id "
    "WHERE g.data_source_code = 'DS_VTE_BC'"
)
print(f"[3/3] Prefs     -> {cur.rowcount} supprimée(s)")

conn.close()
print("Done — Ctrl+Shift+R")
