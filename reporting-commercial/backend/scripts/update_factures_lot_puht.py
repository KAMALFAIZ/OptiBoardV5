"""
=============================================================================
  UPDATE DS_VTE_FACTURES — Fix date + colonnes maximales + reset prefs

  1. Filtre date : TRY_CAST([Date document] AS DATE)  — fin de l'erreur 241
  2. SELECT étendu : toutes les colonnes utiles de Lignes_des_ventes
  3. GridView mis à jour (columns_config) avec colonnes max
  4. APP_GridView_User_Prefs vidée pour grid_id=139 (sinon les vieilles prefs
     écrasent la nouvelle config à l'affichage)

  Idempotent. Exécution : python scripts/update_factures_lot_puht.py
=============================================================================
"""
import sys
import json
import pyodbc

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;PWD=SQL@2019"
)
conn = pyodbc.connect(CONN_STR, autocommit=True)
cur = conn.cursor()

# =============================================================================
#  REQUÊTE ÉTENDUE — toutes les colonnes utiles
# =============================================================================
QUERY = """SELECT
    li.[societe]            AS [Societe],
    li.[Type Document],
    li.[N° Pièce]           AS [Num Piece],
    li.[Date document]      AS [Date Document],
    li.[N° Pièce BL]        AS [Num BL],
    li.[Date BL]            AS [Date BL],
    li.[Code client]        AS [Code Client],
    li.[Intitulé client]    AS [Client],
    en.[Nom représentant]   AS [Commercial],
    li.[Code article]       AS [Code Article],
    li.[Désignation ligne]  AS [Designation],
    li.[N° Série/Lot]       AS [Lot Serie],
    li.[Référence]          AS [Reference],
    li.[Code d'affaire]     AS [Code Affaire],
    li.[Intitulé affaire]   AS [Affaire],
    li.[Catalogue 1]        AS [Famille],
    li.[Catalogue 2]        AS [Sous Famille],
    li.[Gamme 1]            AS [Gamme],
    li.[Quantité]           AS [Quantite],
    li.[Colisage]           AS [Colisage],
    li.[Prix unitaire]      AS [PU HT],
    li.[CMUP]    AS [Prix Revient],
    li.[Remise 1]           AS [Remise1],
    li.[Remise 2]           AS [Remise2],
    li.[Montant HT Net]     AS [Montant HT],
    li.[Montant TTC Net]    AS [Montant TTC],
    li.[Poids net]          AS [Poids Net],
    li.[Code dépôt]         AS [Code Depot],
    li.[Intitulé dépôt]     AS [Depot],
    en.[Statut],
    en.[Statut validé]      AS [Statut Valide],
    en.Souche,
    en.[Valorise CA]        AS [Valorise CA]
FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe]       = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce]     = en.[N° pièce]
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND TRY_CAST(li.[Date document] AS DATE) BETWEEN CAST(@dateDebut AS DATE) AND CAST(@dateFin AS DATE)
  AND (@societe IS NULL OR li.[societe] = @societe)
  AND (@commercial IS NULL OR en.[Nom représentant] = @commercial)
ORDER BY li.[Date document] DESC, li.[N° Pièce]"""

# =============================================================================
#  COLONNES GRIDVIEW — visible=True (defaut) / False (masquée, dispo via toggle)
# =============================================================================
COLUMNS = [
    {"field": "Societe",        "header": "Societe",       "width": 80},
    {"field": "Type Document",  "header": "Type",          "width": 130},
    {"field": "Num Piece",      "header": "N° Piece",      "width": 120},
    {"field": "Date Document",  "header": "Date Facture",  "width": 110, "type": "date"},
    {"field": "Num BL",         "header": "N° BL",         "width": 110, "visible": False},
    {"field": "Date BL",        "header": "Date BL",       "width": 100, "type": "date", "visible": False},
    {"field": "Code Client",    "header": "Code Client",   "width": 100},
    {"field": "Client",         "header": "Client",        "width": 190},
    {"field": "Commercial",     "header": "Commercial",    "width": 130},
    {"field": "Code Article",   "header": "Code Article",  "width": 110},
    {"field": "Designation",    "header": "Designation",   "width": 200},
    {"field": "Lot Serie",      "header": "N° Lot/Série",  "width": 120},
    {"field": "Reference",      "header": "Référence",     "width": 110, "visible": False},
    {"field": "Code Affaire",   "header": "Code Affaire",  "width": 100, "visible": False},
    {"field": "Affaire",        "header": "Affaire",       "width": 160, "visible": False},
    {"field": "Famille",        "header": "Famille",       "width": 120},
    {"field": "Sous Famille",   "header": "Sous Famille",  "width": 120, "visible": False},
    {"field": "Gamme",          "header": "Gamme",         "width": 110, "visible": False},
    {"field": "Quantite",       "header": "Qté",           "width": 80,  "type": "number"},
    {"field": "Colisage",       "header": "Colisage",      "width": 80,  "type": "number", "visible": False},
    {"field": "PU HT",          "header": "PU HT",         "width": 110, "type": "number", "format": "#,##0.00"},
    {"field": "Prix Revient",   "header": "Prix Revient",  "width": 110, "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "Remise1",        "header": "Remise 1",      "width": 80,  "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "Remise2",        "header": "Remise 2",      "width": 80,  "type": "number", "format": "#,##0.00", "visible": False},
    {"field": "Montant HT",     "header": "Montant HT",    "width": 120, "type": "number", "format": "#,##0.00"},
    {"field": "Montant TTC",    "header": "Montant TTC",   "width": 120, "type": "number", "format": "#,##0.00"},
    {"field": "Poids Net",      "header": "Poids Net",     "width": 90,  "type": "number", "visible": False},
    {"field": "Code Depot",     "header": "Code Dépôt",    "width": 90,  "visible": False},
    {"field": "Depot",          "header": "Dépôt",         "width": 130},
    {"field": "Statut",         "header": "Statut",        "width": 100},
    {"field": "Statut Valide",  "header": "Statut Validé", "width": 110, "visible": False},
    {"field": "Souche",         "header": "Souche",        "width": 80,  "visible": False},
    {"field": "Valorise CA",    "header": "Valorisé CA",   "width": 90,  "visible": False},
]
COLUMNS_JSON = json.dumps(COLUMNS, ensure_ascii=False)

# =============================================================================
#  DIAGNOSTIC
# =============================================================================
print("=" * 70)
print("  UPDATE DS_VTE_FACTURES — colonnes max + fix date + reset prefs")
print("=" * 70)
print("\n--- DIAGNOSTIC ---")

cur.execute("SELECT id, code, nom FROM APP_DataSources_Templates WHERE code = 'DS_VTE_FACTURES'")
tmpl = cur.fetchone()
if tmpl:
    print(f"  Template  : id={tmpl[0]}  code={tmpl[1]}")
else:
    print("  [WARN] Template DS_VTE_FACTURES INTROUVABLE")

cur.execute(
    "SELECT id, nom, data_source_code FROM APP_GridViews "
    "WHERE data_source_code = 'DS_VTE_FACTURES' OR nom = 'Factures de Ventes'"
)
gvs = cur.fetchall()
gv_ids = []
for gv in gvs:
    print(f"  GridView  : id={gv[0]}  nom={gv[1]}  ds_code={gv[2]}")
    gv_ids.append(gv[0])

# =============================================================================
#  1. UPDATE query_template
# =============================================================================
print("\n--- MISES À JOUR ---")

cur.execute(
    "UPDATE APP_DataSources_Templates SET query_template = ?, type = 'SQL', actif = 1 "
    "WHERE code = 'DS_VTE_FACTURES'",
    (QUERY,),
)
print(f"  [1/3] DataSources_Templates  -> {cur.rowcount} ligne(s)")

# =============================================================================
#  2. UPDATE columns_config GridView
# =============================================================================
cur.execute(
    "UPDATE APP_GridViews SET columns_config = ? "
    "WHERE data_source_code = 'DS_VTE_FACTURES'",
    (COLUMNS_JSON,),
)
rows = cur.rowcount
if rows == 0:
    cur.execute(
        "UPDATE APP_GridViews SET columns_config = ?, data_source_code = 'DS_VTE_FACTURES' "
        "WHERE nom = 'Factures de Ventes'",
        (COLUMNS_JSON,),
    )
    rows = cur.rowcount
print(f"  [2/3] GridViews columns_config -> {rows} ligne(s)")

# =============================================================================
#  3. SUPPRIMER les prefs utilisateur sauvegardées (elles écrasaient la config)
# =============================================================================
deleted = 0
for gv_id in gv_ids:
    cur.execute("DELETE FROM APP_GridView_User_Prefs WHERE grid_id = ?", (gv_id,))
    deleted += cur.rowcount

# Essai aussi par les IDs courants si gv_ids vide
if not gv_ids:
    cur.execute(
        "DELETE p FROM APP_GridView_User_Prefs p "
        "INNER JOIN APP_GridViews g ON p.grid_id = g.id "
        "WHERE g.data_source_code = 'DS_VTE_FACTURES' OR g.nom = 'Factures de Ventes'"
    )
    deleted = cur.rowcount

print(f"  [3/3] User_Prefs supprimées   -> {deleted} ligne(s)")

# =============================================================================
#  4. VÉRIFICATION — affiche ce qui est réellement stocké en DB
# =============================================================================
print("\n--- VÉRIFICATION ---")

cur.execute("SELECT columns_config FROM APP_GridViews WHERE data_source_code = 'DS_VTE_FACTURES'")
row = cur.fetchone()
if row and row[0]:
    stored_cols = json.loads(row[0])
    print(f"  Colonnes stockées ({len(stored_cols)}) :")
    for c in stored_cols:
        vis = "" if c.get("visible", True) else " [masqué]"
        print(f"    {c['field']:<20} -> {c['header']}{vis}")
    puttc = [c for c in stored_cols if "ttc" in c.get("field","").lower() or "ttc" in c.get("header","").lower()]
    if puttc:
        print(f"  [WARN] PU TTC trouvé dans config : {puttc}")
    else:
        print("  [OK] PU TTC absent de la config GridView")

cur.close()
conn.close()
print("\nDone.")
print("Etape suivante : ouvrir les DevTools (F12) -> Application -> Local Storage")
print("  -> supprimer les clés 'ag-grid-*' ou 'grid-*' pour ce domaine")
print("  -> puis Ctrl+Shift+R (hard refresh)")
