"""
=============================================================================
  UPDATE DES 7 DOCUMENTS VENTES
  - Corriger orthographe des headers
  - Ajouter les champs masqués demandés dans les requêtes SQL et gridviews

  Champs à ajouter (masqués) :
    en.Souche, en.Statut, en.[Entête 1], en.[Entête 2], en.[Entête 3], en.[Entête 4],
    li.[Catalogue 1], li.[Catalogue 2], li.[Catalogue 3], li.[Catalogue 4],
    li.[Gamme 1], li.[Gamme 2], li.[Poids brut], li.[Poids net],
    li.[Intitulé affaire], li.[Code d'affaire],
    li.Taxe1, li.[Type taux taxe 1], li.[Type taxe 1],
    li.[Remise 1]

  Exécution: python scripts/update_ventes_columns.py
=============================================================================
"""
import pyodbc
import json
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

# ============================================================================
#  COLONNES MASQUÉES À AJOUTER (communes à tous les 7 documents ventes)
# ============================================================================
HIDDEN_COLUMNS_SQL = """
    en.[Souche],
    en.[Statut],
    en.[Entête 1] AS [Entete 1],
    en.[Entête 2] AS [Entete 2],
    en.[Entête 3] AS [Entete 3],
    en.[Entête 4] AS [Entete 4],
    li.[Catalogue 1],
    li.[Catalogue 2],
    li.[Catalogue 3],
    li.[Catalogue 4],
    li.[Gamme 1],
    li.[Gamme 2],
    li.[Poids brut],
    li.[Poids net],
    li.[Intitulé affaire] AS [Intitule Affaire],
    li.[Code d'affaire] AS [Code Affaire],
    li.[Taxe1] AS [Taxe 1],
    li.[Type taux taxe 1],
    li.[Type taxe 1],
    li.[Remise 1]"""

HIDDEN_GRIDVIEW_COLS = [
    {"field": "Souche", "header": "Souche", "width": 100, "visible": False},
    {"field": "Statut", "header": "Statut", "width": 100, "visible": False},
    {"field": "Entete 1", "header": "Entête 1", "width": 120, "visible": False},
    {"field": "Entete 2", "header": "Entête 2", "width": 120, "visible": False},
    {"field": "Entete 3", "header": "Entête 3", "width": 120, "visible": False},
    {"field": "Entete 4", "header": "Entête 4", "width": 120, "visible": False},
    {"field": "Catalogue 1", "header": "Catalogue 1", "width": 120, "visible": False},
    {"field": "Catalogue 2", "header": "Catalogue 2", "width": 120, "visible": False},
    {"field": "Catalogue 3", "header": "Catalogue 3", "width": 120, "visible": False},
    {"field": "Catalogue 4", "header": "Catalogue 4", "width": 120, "visible": False},
    {"field": "Gamme 1", "header": "Gamme 1", "width": 120, "visible": False},
    {"field": "Gamme 2", "header": "Gamme 2", "width": 120, "visible": False},
    {"field": "Poids brut", "header": "Poids Brut", "width": 100, "type": "number", "visible": False},
    {"field": "Poids net", "header": "Poids Net", "width": 100, "type": "number", "visible": False},
    {"field": "Intitule Affaire", "header": "Intitulé Affaire", "width": 150, "visible": False},
    {"field": "Code Affaire", "header": "Code Affaire", "width": 120, "visible": False},
    {"field": "Taxe 1", "header": "Taxe 1", "width": 100, "type": "number", "visible": False},
    {"field": "Type taux taxe 1", "header": "Type Taux Taxe 1", "width": 120, "visible": False},
    {"field": "Type taxe 1", "header": "Type Taxe 1", "width": 120, "visible": False},
    {"field": "Remise 1", "header": "Remise 1", "width": 100, "type": "number", "visible": False},
]

# ============================================================================
#  COMMON SQL FRAGMENTS
# ============================================================================
BASE_JOIN = """FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce] = en.[N° pièce]"""

CA_FILTER = "li.[Valorise CA] = 'Oui'"
DATE_FILTER = "li.[Date BL] BETWEEN @dateDebut AND @dateFin"
SOCIETE_FILTER = "(@societe IS NULL OR li.[societe] = @societe)"

# ============================================================================
#  7 DOCUMENTS VENTES - Définitions mises à jour
# ============================================================================
DOCUMENTS = [
    {
        "code": "DS_VTE_FACTURES",
        "nom": "Factures de Ventes",
        "total_columns": ["Quantité", "Montant HT", "Montant TTC"],
        "query": f"""SELECT
    li.[societe] AS [Societe],
    li.[Type Document],
    li.[N° Pièce] AS [N° Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Désignation],
    li.[Quantité] AS [Quantité],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Catalogue 1] AS [Famille],
    li.[Code dépôt] AS [Code Dépôt],
    li.[Intitulé dépôt] AS [Dépôt],{HIDDEN_COLUMNS_SQL}
{BASE_JOIN}
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND {DATE_FILTER} AND {SOCIETE_FILTER}
ORDER BY li.[Date document] DESC, li.[N° Pièce]""",
        "columns": [
            {"field": "Societe", "header": "Société", "width": 90},
            {"field": "Type Document", "header": "Type Document", "width": 150, "visible": False},
            {"field": "N° Piece", "header": "N° Pièce", "width": 120},
            {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
            {"field": "Code Client", "header": "Code Client", "width": 100, "visible": False},
            {"field": "Client", "header": "Client", "width": 200},
            {"field": "Commercial", "header": "Commercial", "width": 140},
            {"field": "Code Article", "header": "Code Article", "width": 110, "visible": False},
            {"field": "Désignation", "header": "Désignation", "width": 200},
            {"field": "Quantité", "header": "Quantité", "width": 90, "type": "number"},
            {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Famille", "header": "Famille", "width": 120},
            {"field": "Dépôt", "header": "Dépôt", "width": 140},
        ]
    },
    {
        "code": "DS_VTE_BL",
        "nom": "Bons de Livraison",
        "total_columns": ["Quantité BL", "Montant HT", "Montant TTC"],
        "query": f"""SELECT
    li.[societe] AS [Societe],
    li.[N° Pièce BL] AS [N° BL],
    li.[Date BL] AS [Date BL],
    li.[N° Pièce] AS [N° Pièce Origine],
    li.[Type Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Désignation],
    li.[Quantité BL] AS [Quantité BL],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Code dépôt] AS [Code Dépôt],
    li.[Intitulé dépôt] AS [Dépôt],{HIDDEN_COLUMNS_SQL}
{BASE_JOIN}
WHERE li.[N° Pièce BL] <> ''
  AND {DATE_FILTER} AND {SOCIETE_FILTER}
ORDER BY li.[Date BL] DESC""",
        "columns": [
            {"field": "Societe", "header": "Société", "width": 90},
            {"field": "N° BL", "header": "N° BL", "width": 120},
            {"field": "Date BL", "header": "Date BL", "width": 110, "type": "date"},
            {"field": "Type Document", "header": "Type Document", "width": 140, "visible": False},
            {"field": "Code Client", "header": "Code Client", "width": 100, "visible": False},
            {"field": "Client", "header": "Client", "width": 200},
            {"field": "Commercial", "header": "Commercial", "width": 140},
            {"field": "Code Article", "header": "Code Article", "width": 110, "visible": False},
            {"field": "Désignation", "header": "Désignation", "width": 200},
            {"field": "Quantité BL", "header": "Qté BL", "width": 90, "type": "number"},
            {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Dépôt", "header": "Dépôt", "width": 140},
        ]
    },
    {
        "code": "DS_VTE_BC",
        "nom": "Bons de Commande",
        "total_columns": ["Quantité BC", "Montant HT", "Montant TTC"],
        "query": f"""SELECT
    li.[societe] AS [Societe],
    li.[N° Pièce BC] AS [N° BC],
    li.[Date BC] AS [Date BC],
    li.[N° Pièce] AS [N° Pièce Origine],
    li.[Type Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Désignation],
    li.[Quantité BC] AS [Quantité BC],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],{HIDDEN_COLUMNS_SQL}
{BASE_JOIN}
WHERE li.[N° Pièce BC] <> ''
  AND {DATE_FILTER} AND {SOCIETE_FILTER}
ORDER BY li.[Date BC] DESC""",
        "columns": [
            {"field": "Societe", "header": "Société", "width": 90},
            {"field": "N° BC", "header": "N° BC", "width": 120},
            {"field": "Date BC", "header": "Date BC", "width": 110, "type": "date"},
            {"field": "Type Document", "header": "Type Document", "width": 140, "visible": False},
            {"field": "Code Client", "header": "Code Client", "width": 100, "visible": False},
            {"field": "Client", "header": "Client", "width": 200},
            {"field": "Commercial", "header": "Commercial", "width": 140},
            {"field": "Code Article", "header": "Code Article", "width": 110, "visible": False},
            {"field": "Désignation", "header": "Désignation", "width": 200},
            {"field": "Quantité BC", "header": "Qté BC", "width": 90, "type": "number"},
            {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        ]
    },
    {
        "code": "DS_VTE_DEVIS",
        "nom": "Devis",
        "total_columns": ["Quantité", "Montant HT", "Montant TTC"],
        "query": f"""SELECT
    li.[societe] AS [Societe],
    li.[N° Pièce] AS [N° Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Désignation],
    li.[Quantité devis] AS [Quantité],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],{HIDDEN_COLUMNS_SQL}
{BASE_JOIN}
WHERE li.[Type Document] = 'Devis'
  AND {DATE_FILTER} AND {SOCIETE_FILTER}
ORDER BY li.[Date document] DESC""",
        "columns": [
            {"field": "Societe", "header": "Société", "width": 90},
            {"field": "N° Piece", "header": "N° Pièce", "width": 120},
            {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
            {"field": "Code Client", "header": "Code Client", "width": 100, "visible": False},
            {"field": "Client", "header": "Client", "width": 200},
            {"field": "Commercial", "header": "Commercial", "width": 140},
            {"field": "Code Article", "header": "Code Article", "width": 110, "visible": False},
            {"field": "Désignation", "header": "Désignation", "width": 200},
            {"field": "Quantité", "header": "Quantité", "width": 90, "type": "number"},
            {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        ]
    },
    {
        "code": "DS_VTE_AVOIRS",
        "nom": "Avoirs",
        "total_columns": ["Quantité", "Montant HT", "Montant TTC"],
        "query": f"""SELECT
    li.[societe] AS [Societe],
    li.[Type Document],
    li.[N° Pièce] AS [N° Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Désignation],
    li.[Quantité] AS [Quantité],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Catalogue 1] AS [Famille],{HIDDEN_COLUMNS_SQL}
{BASE_JOIN}
WHERE li.[Type Document] IN ('Bon avoir financier', 'Facture avoir', 'Facture avoir comptabilisée')
  AND {DATE_FILTER} AND {SOCIETE_FILTER}
ORDER BY li.[Date document] DESC""",
        "columns": [
            {"field": "Societe", "header": "Société", "width": 90},
            {"field": "Type Document", "header": "Type Document", "width": 160, "visible": False},
            {"field": "N° Piece", "header": "N° Pièce", "width": 120},
            {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
            {"field": "Code Client", "header": "Code Client", "width": 100, "visible": False},
            {"field": "Client", "header": "Client", "width": 200},
            {"field": "Commercial", "header": "Commercial", "width": 140},
            {"field": "Code Article", "header": "Code Article", "width": 110, "visible": False},
            {"field": "Désignation", "header": "Désignation", "width": 200},
            {"field": "Quantité", "header": "Quantité", "width": 90, "type": "number"},
            {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Famille", "header": "Famille", "width": 120},
        ]
    },
    {
        "code": "DS_VTE_RETOURS",
        "nom": "Bons de Retour",
        "total_columns": ["Quantité", "Montant HT", "Montant TTC"],
        "query": f"""SELECT
    li.[societe] AS [Societe],
    li.[Type Document],
    li.[N° Pièce] AS [N° Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Désignation],
    li.[Quantité] AS [Quantité],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Code dépôt] AS [Code Dépôt],
    li.[Intitulé dépôt] AS [Dépôt],{HIDDEN_COLUMNS_SQL}
{BASE_JOIN}
WHERE li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilisée')
  AND {DATE_FILTER} AND {SOCIETE_FILTER}
ORDER BY li.[Date document] DESC""",
        "columns": [
            {"field": "Societe", "header": "Société", "width": 90},
            {"field": "Type Document", "header": "Type Document", "width": 160, "visible": False},
            {"field": "N° Piece", "header": "N° Pièce", "width": 120},
            {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
            {"field": "Code Client", "header": "Code Client", "width": 100, "visible": False},
            {"field": "Client", "header": "Client", "width": 200},
            {"field": "Commercial", "header": "Commercial", "width": 140},
            {"field": "Code Article", "header": "Code Article", "width": 110, "visible": False},
            {"field": "Désignation", "header": "Désignation", "width": 200},
            {"field": "Quantité", "header": "Quantité", "width": 90, "type": "number"},
            {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Dépôt", "header": "Dépôt", "width": 140},
        ]
    },
    {
        "code": "DS_VTE_PL",
        "nom": "Préparations de Livraison",
        "total_columns": ["Quantité PL", "Montant HT"],
        "query": f"""SELECT
    li.[societe] AS [Societe],
    li.[N° pièce PL] AS [N° PL],
    li.[Date PL] AS [Date PL],
    li.[N° Pièce] AS [N° Pièce Origine],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Désignation],
    li.[Quantité PL] AS [Quantité PL],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Code dépôt] AS [Code Dépôt],
    li.[Intitulé dépôt] AS [Dépôt],{HIDDEN_COLUMNS_SQL}
{BASE_JOIN}
WHERE li.[Type Document] = 'Préparation de livraison'
  AND {DATE_FILTER} AND {SOCIETE_FILTER}
ORDER BY li.[Date PL] DESC""",
        "columns": [
            {"field": "Societe", "header": "Société", "width": 90},
            {"field": "N° PL", "header": "N° PL", "width": 120},
            {"field": "Date PL", "header": "Date PL", "width": 110, "type": "date"},
            {"field": "Code Client", "header": "Code Client", "width": 100, "visible": False},
            {"field": "Client", "header": "Client", "width": 200},
            {"field": "Commercial", "header": "Commercial", "width": 140},
            {"field": "Code Article", "header": "Code Article", "width": 110, "visible": False},
            {"field": "Désignation", "header": "Désignation", "width": 200},
            {"field": "Quantité PL", "header": "Qté PL", "width": 90, "type": "number"},
            {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Dépôt", "header": "Dépôt", "width": 140},
        ]
    },
]


def main():
    print("=" * 70)
    print("  MISE À JOUR DES 7 DOCUMENTS VENTES")
    print("  - Correction orthographe headers (accents français)")
    print("  - Ajout 20 champs masqués (Souche, Statut, Entête 1-4, etc.)")
    print("=" * 70)

    updated_ds = 0
    updated_gv = 0

    for doc in DOCUMENTS:
        code = doc["code"]
        print(f"\n--- {doc['nom']} ({code}) ---")

        # 1. Mettre à jour la requête SQL du datasource template
        cursor.execute(
            "UPDATE APP_DataSources_Templates SET query_template = ? WHERE code = ?",
            (doc["query"], code)
        )
        if cursor.rowcount > 0:
            updated_ds += 1
            print(f"  [OK] Requête SQL mise à jour")
        else:
            print(f"  [SKIP] Template {code} non trouvé")

        # 2. Mettre à jour les colonnes du gridview
        # D'abord, trouver le gridview associé
        cursor.execute(
            "SELECT id, columns_config FROM APP_GridViews WHERE data_source_code = ?",
            (code,)
        )
        row = cursor.fetchone()
        if row:
            gv_id = row[0]
            # Construire la nouvelle config de colonnes : visibles + masquées
            all_columns = doc["columns"] + HIDDEN_COLUMNS_COLS(doc)

            tc = doc.get("total_columns", [])
            cursor.execute(
                "UPDATE APP_GridViews SET columns_config = ?, show_totals = 1, total_columns = ? WHERE id = ?",
                (json.dumps(all_columns, ensure_ascii=False), json.dumps(tc, ensure_ascii=False), gv_id)
            )
            updated_gv += 1
            print(f"  [OK] GridView ID={gv_id} colonnes mises à jour ({len(doc['columns'])} visibles + {len(HIDDEN_GRIDVIEW_COLS)} masquées, totaux: {tc})")
        else:
            print(f"  [SKIP] GridView pour {code} non trouvé")

    # 3. Aussi mettre à jour le rapport "Commandes en Cours" (DS_VTE_CMD_EN_COURS) pour corriger l'orthographe
    print(f"\n--- Commandes en Cours (DS_VTE_CMD_EN_COURS) ---")
    cmd_query = f"""SELECT
    li.[societe] AS [Societe],
    li.[N° Pièce] AS [N° Piece],
    li.[Date document] AS [Date Commande],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Désignation],
    li.[Quantité] AS [Qté Commandée],
    li.[Quantité BL] AS [Qté Livrée],
    li.[Quantité] - ISNULL(li.[Quantité BL], 0) AS [Reste à Livrer],
    li.[Montant HT Net] AS [Montant HT],
    en.[Statut],
    DATEDIFF(DAY, li.[Date document], GETDATE()) AS [Ancienneté (j)],{HIDDEN_COLUMNS_SQL}
{BASE_JOIN}
WHERE li.[Type Document] = 'Bon de commande'
  AND li.[Quantité] > ISNULL(li.[Quantité BL], 0)
  AND {SOCIETE_FILTER}
ORDER BY [Ancienneté (j)] DESC"""

    cursor.execute(
        "UPDATE APP_DataSources_Templates SET query_template = ? WHERE code = ?",
        (cmd_query, "DS_VTE_CMD_EN_COURS")
    )
    if cursor.rowcount > 0:
        updated_ds += 1
        print(f"  [OK] Requête SQL mise à jour")

    # Mettre à jour les colonnes du gridview Commandes en Cours
    cursor.execute(
        "SELECT id FROM APP_GridViews WHERE data_source_code = ?",
        ("DS_VTE_CMD_EN_COURS",)
    )
    row = cursor.fetchone()
    if row:
        gv_id = row[0]
        cmd_cols = [
            {"field": "Societe", "header": "Société", "width": 90},
            {"field": "N° Piece", "header": "N° Pièce", "width": 120},
            {"field": "Date Commande", "header": "Date Commande", "width": 110, "type": "date"},
            {"field": "Code Client", "header": "Code Client", "width": 100, "visible": False},
            {"field": "Client", "header": "Client", "width": 200},
            {"field": "Commercial", "header": "Commercial", "width": 140},
            {"field": "Code Article", "header": "Code Article", "width": 110, "visible": False},
            {"field": "Désignation", "header": "Désignation", "width": 200},
            {"field": "Qté Commandée", "header": "Qté Commandée", "width": 100, "type": "number"},
            {"field": "Qté Livrée", "header": "Qté Livrée", "width": 90, "type": "number"},
            {"field": "Reste à Livrer", "header": "Reste à Livrer", "width": 100, "type": "number"},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
            {"field": "Statut", "header": "Statut", "width": 100},
            {"field": "Ancienneté (j)", "header": "Ancienneté (j)", "width": 100, "type": "number"},
        ] + HIDDEN_GRIDVIEW_COLS
        cmd_tc = ["Qté Commandée", "Qté Livrée", "Qté Restante", "Montant HT"]
        cursor.execute(
            "UPDATE APP_GridViews SET columns_config = ?, show_totals = 1, total_columns = ? WHERE id = ?",
            (json.dumps(cmd_cols, ensure_ascii=False), json.dumps(cmd_tc, ensure_ascii=False), gv_id)
        )
        updated_gv += 1
        print(f"  [OK] GridView ID={gv_id} colonnes mises à jour (totaux: {cmd_tc})")

    print()
    print("=" * 70)
    print(f"  Résultat: {updated_ds} templates SQL, {updated_gv} gridviews mis à jour")
    print("=" * 70)


def HIDDEN_COLUMNS_COLS(doc):
    """Retourne les colonnes masquées en évitant les doublons avec les colonnes visibles"""
    visible_fields = {c["field"] for c in doc["columns"]}
    return [c for c in HIDDEN_GRIDVIEW_COLS if c["field"] not in visible_fields]


if __name__ == "__main__":
    main()
