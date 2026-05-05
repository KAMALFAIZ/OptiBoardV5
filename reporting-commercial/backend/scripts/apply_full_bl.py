"""Applique la requête complète BL avec tous les champs Sage."""
import sys, json, pyodbc
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONN = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(CONN, autocommit=True)
cur = conn.cursor()

QUERY = """SELECT
    li.[societe]                    AS [Societe],
    li.[N° Pièce BL]     AS [Num BL],
    li.[Date BL],
    li.[N° Pièce]         AS [Num Piece Origine],
    li.[Type Document],
    li.[Code client]                AS [Code Client],
    li.[Intitulé client]      AS [Client],
    en.[Nom représentant]     AS [Commercial],
    li.[Code article]               AS [Code Article],
    li.[Désignation ligne]    AS [Designation],
    li.[N° Série/Lot]     AS [Lot Serie],
    li.[Quantité BL]           AS [Quantite BL],
    li.[Prix unitaire]              AS [PU HT],
    li.[PU Devise]                  AS [PU Devise],
    li.[Remise 1]                   AS [Remise1],
    li.[Taxe1]                      AS [Taxe1],
    li.[Type taux taxe 1]           AS [Type Taux Taxe],
    li.[Type taxe 1]                AS [Type Taxe],
    li.[Montant HT Net]             AS [Montant HT],
    li.[Montant TTC Net]            AS [Montant TTC],
    li.[Poids brut]                 AS [Poids Brut],
    li.[Poids net]                  AS [Poids Net],
    li.[Code dépôt]       AS [Code Depot],
    li.[Intitulé dépôt]  AS [Depot],
    Articles.[Intitulé famille]    AS [Famille],
    li.[Catalogue 2]                AS [Catalogue2],
    li.[Catalogue 3]                AS [Catalogue3],
    li.[Catalogue 4]                AS [Catalogue4],
    li.[Gamme 1]                    AS [Gamme1],
    li.[Gamme 2]                    AS [Gamme2],
    li.[Code d'affaire]             AS [Code Affaire],
    li.[Intitulé affaire]     AS [Affaire],
    li.[N° Pièce BC]      AS [Num BC],
    li.[Date BC],
    li.[N° pièce PL]      AS [Num PL],
    li.[Date PL],
    en.[Souche],
    en.[Statut],
    en.[Entête 1]              AS [Entete1],
    en.[Entête 2]              AS [Entete2],
    en.[Entête 3]              AS [Entete3],
    en.[Entête 4]              AS [Entete4]
FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe]        = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce]      = en.[N° pièce]
INNER JOIN [Articles]
    ON li.[societe]        = Articles.[societe]
    AND li.[Code article]  = Articles.[Code Article]
WHERE li.[N° Pièce BL] <> ''
  AND TRY_CAST(li.[Date BL] AS DATE) BETWEEN CAST(@dateDebut AS DATE) AND CAST(@dateFin AS DATE)
  AND (@societe IS NULL OR li.[societe] = @societe)
  AND (@commercial IS NULL OR en.[Nom représentant] = @commercial)
ORDER BY li.[Date BL] DESC"""

COLUMNS = [
    {"field": "Societe",          "header": "Societe",         "width": 80},
    {"field": "Num BL",           "header": "N° BL",           "width": 120},
    {"field": "Date BL",          "header": "Date BL",         "width": 110, "type": "date"},
    {"field": "Num Piece Origine","header": "N° Piece Orig.",  "width": 120, "visible": False},
    {"field": "Type Document",    "header": "Type",            "width": 130},
    {"field": "Code Client",      "header": "Code Client",     "width": 100},
    {"field": "Client",           "header": "Client",          "width": 190},
    {"field": "Commercial",       "header": "Commercial",      "width": 130},
    {"field": "Code Article",     "header": "Code Article",    "width": 110},
    {"field": "Designation",      "header": "Designation",     "width": 200},
    {"field": "Lot Serie",        "header": "N° Lot/Série",    "width": 120},
    {"field": "Quantite BL",      "header": "Qté BL",          "width": 80,  "type": "number"},
    {"field": "PU HT",            "header": "PU HT",           "width": 110, "type": "number", "format": "#,##0.00"},
    {"field": "PU Devise",        "header": "PU Devise",       "width": 100, "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "Remise1",          "header": "Remise 1",        "width": 80,  "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "Taxe1",            "header": "Taxe",            "width": 80,  "visible": False},
    {"field": "Type Taux Taxe",   "header": "Type Taux Taxe",  "width": 120, "visible": False},
    {"field": "Type Taxe",        "header": "Type Taxe",       "width": 100, "visible": False},
    {"field": "Montant HT",       "header": "Montant HT",      "width": 120, "type": "number", "format": "#,##0.00"},
    {"field": "Montant TTC",      "header": "Montant TTC",     "width": 120, "type": "number", "format": "#,##0.00"},
    {"field": "Poids Brut",       "header": "Poids Brut",      "width": 90,  "type": "number", "visible": False},
    {"field": "Poids Net",        "header": "Poids Net",       "width": 90,  "type": "number", "visible": False},
    {"field": "Code Depot",       "header": "Code Dépôt",      "width": 90,  "visible": False},
    {"field": "Depot",            "header": "Dépôt",           "width": 130},
    {"field": "Famille",          "header": "Famille",         "width": 120},
    {"field": "Catalogue2",       "header": "Catalogue 2",     "width": 110, "visible": False},
    {"field": "Catalogue3",       "header": "Catalogue 3",     "width": 110, "visible": False},
    {"field": "Catalogue4",       "header": "Catalogue 4",     "width": 110, "visible": False},
    {"field": "Gamme1",           "header": "Gamme 1",         "width": 110, "visible": False},
    {"field": "Gamme2",           "header": "Gamme 2",         "width": 110, "visible": False},
    {"field": "Code Affaire",     "header": "Code Affaire",    "width": 100, "visible": False},
    {"field": "Affaire",          "header": "Affaire",         "width": 160, "visible": False},
    {"field": "Num BC",           "header": "N° BC",           "width": 110, "visible": False},
    {"field": "Date BC",          "header": "Date BC",         "width": 100, "type": "date", "visible": False},
    {"field": "Num PL",           "header": "N° PL",           "width": 110, "visible": False},
    {"field": "Date PL",          "header": "Date PL",         "width": 100, "type": "date", "visible": False},
    {"field": "Souche",           "header": "Souche",          "width": 80,  "visible": False},
    {"field": "Statut",           "header": "Statut",          "width": 100},
    {"field": "Entete1",          "header": "Entête 1",        "width": 120, "visible": False},
    {"field": "Entete2",          "header": "Entête 2",        "width": 120, "visible": False},
    {"field": "Entete3",          "header": "Entête 3",        "width": 120, "visible": False},
    {"field": "Entete4",          "header": "Entête 4",        "width": 120, "visible": False},
]

TOTAL = json.dumps(["Quantite BL", "Montant HT", "Montant TTC"], ensure_ascii=False)
COLS  = json.dumps(COLUMNS, ensure_ascii=False)

cur.execute(
    "UPDATE APP_DataSources_Templates SET query_template=?, type='SQL', actif=1 WHERE code='DS_VTE_BL'",
    (QUERY,)
)
print(f"[1/3] Template  -> {cur.rowcount} ligne(s)")

cur.execute(
    "UPDATE APP_GridViews SET columns_config=?, total_columns=?, show_totals=1 WHERE data_source_code='DS_VTE_BL'",
    (COLS, TOTAL)
)
print(f"[2/3] GridView  -> {cur.rowcount} ligne(s)")

cur.execute(
    "DELETE p FROM APP_GridView_User_Prefs p "
    "INNER JOIN APP_GridViews g ON p.grid_id = g.id "
    "WHERE g.data_source_code = 'DS_VTE_BL'"
)
print(f"[3/3] Prefs     -> {cur.rowcount} supprimée(s)")

conn.close()
print("Done — Ctrl+Shift+R")
