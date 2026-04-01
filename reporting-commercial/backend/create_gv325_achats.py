"""
Crée DS_ACH_DETAIL_COMPLET + GridView 325 "Achats - Détail Complet"
Équivalent achat de DS_VTE_CA_CLIENT / GridView 324
"""
import json
from app.database_unified import central_cursor

new_query = """SELECT
    li.[Code fournisseur]              AS [Code Fournisseur],
    li.[Intitulé fournisseur]          AS [Fournisseur],
    li.[societe]                       AS [Societe],
    en.[Catégorie Comptable]           AS [Categorie Comptable],
    en.[Intitulé tiers payeur]         AS [Tiers Payeur],
    li.[Code article]                  AS [Code Article],
    li.[Désignation]                   AS [Article],
    li.[Catalogue 1]                   AS [Famille],
    li.[Catalogue 2]                   AS [Sous-Famille],
    li.[Code dépôt]                    AS [Code Depot],
    li.[Intitulé dépôt]                AS [Depot],
    li.[Code d'affaire]                AS [Code Affaire],
    li.[Intitulé affaire]              AS [Affaire],
    li.[Type Document]                 AS [Type Document],
    li.[N° Pièce]                      AS [N Piece],
    li.[Date]                          AS [Date],
    YEAR(li.[Date])                    AS [Annee],
    MONTH(li.[Date])                   AS [Mois],
    FORMAT(li.[Date], 'yyyy-MM')       AS [Periode],
    li.[Quantité]                      AS [Quantite],
    li.[Prix unitaire]                 AS [Prix Unitaire],
    li.[Remise 1]                      AS [Remise],
    li.[Montant HT Net]                AS [Montant HT],
    li.[Montant TTC Net]               AS [Montant TTC],
    li.[Prix de revient]               AS [Prix Revient],
    li.[Frais d'approche]              AS [Frais Approche],
    li.CMUP                            AS [CMUP],
    li.[Poids net]                     AS [Poids Net],
    en.Souche                          AS [Souche],
    en.Statut                          AS [Statut]
FROM [Lignes_des_achats] li
INNER JOIN [Entête_des_achats] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR li.[societe] = @societe)
ORDER BY li.[Date] DESC"""

columns_config = json.dumps([
    {"field": "Date",            "header": "Date",              "width": 100, "sortable": True, "filterable": True, "format": "date",     "align": "center", "visible": True,  "pinned": None},
    {"field": "N Piece",         "header": "N° Pièce",          "width": 130, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Type Document",   "header": "Type Doc.",          "width": 120, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Code Fournisseur","header": "Code Fourn.",        "width": 110, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Fournisseur",     "header": "Fournisseur",        "width": 220, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": "left"},
    {"field": "Categorie Comptable","header": "Catégorie",       "width": 130, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Tiers Payeur",    "header": "Tiers Payeur",       "width": 160, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Code Article",    "header": "Code Article",       "width": 120, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Article",         "header": "Article",            "width": 220, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Famille",         "header": "Famille",            "width": 140, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Sous-Famille",    "header": "Sous-Famille",       "width": 130, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Code Depot",      "header": "Code Dépôt",         "width":  90, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Depot",           "header": "Dépôt",              "width": 140, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Affaire",         "header": "Affaire",            "width": 150, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Societe",         "header": "Société",            "width": 120, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Periode",         "header": "Période",            "width":  90, "sortable": True, "filterable": True, "format": None,       "align": "center", "visible": False, "pinned": None},
    {"field": "Annee",           "header": "Année",              "width":  70, "sortable": True, "filterable": True, "format": None,       "align": "center", "visible": False, "pinned": None},
    {"field": "Mois",            "header": "Mois",               "width":  60, "sortable": True, "filterable": True, "format": None,       "align": "center", "visible": False, "pinned": None},
    {"field": "Quantite",        "header": "Qté",                "width":  80, "sortable": True, "filterable": True, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "Prix Unitaire",   "header": "PU HT",              "width": 110, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Remise",          "header": "Remise %",           "width":  80, "sortable": True, "filterable": True, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "Montant HT",      "header": "Montant HT",         "width": 140, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Montant TTC",     "header": "Montant TTC",        "width": 140, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": False, "pinned": None},
    {"field": "Prix Revient",    "header": "Prix Revient",       "width": 120, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": False, "pinned": None},
    {"field": "Frais Approche",  "header": "Frais Approche",     "width": 120, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": False, "pinned": None},
    {"field": "CMUP",            "header": "CMUP",               "width": 110, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": False, "pinned": None},
    {"field": "Poids Net",       "header": "Poids Net",          "width":  90, "sortable": True, "filterable": True, "format": None,       "align": "right",  "visible": False, "pinned": None},
    {"field": "Souche",          "header": "Souche",             "width":  90, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Statut",          "header": "Statut",             "width":  90, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
])

with central_cursor() as cur:
    # 1. Créer (ou mettre à jour) la datasource DS_ACH_DETAIL_COMPLET
    cur.execute("SELECT id FROM APP_DataSources_Templates WHERE code = 'DS_ACH_DETAIL_COMPLET'")
    existing_ds = cur.fetchone()
    if existing_ds:
        cur.execute(
            "UPDATE APP_DataSources_Templates SET query_template=?, description=? WHERE code='DS_ACH_DETAIL_COMPLET'",
            (new_query, "Détail complet des achats : fournisseur, article, famille, dépôt, montants, remise, CMUP")
        )
        print("DS updated:", cur.rowcount)
    else:
        cur.execute(
            """INSERT INTO APP_DataSources_Templates
               (code, nom, type, category, description, query_template, parameters, is_system, actif, date_creation)
               VALUES (?, ?, 'query', 'achats', ?, ?, ?, 0, 1, GETDATE())""",
            (
                'DS_ACH_DETAIL_COMPLET',
                'Achats - Détail Complet',
                "Détail complet des achats : fournisseur, article, famille, dépôt, montants, remise, CMUP",
                new_query,
                json.dumps([
                    {"name": "dateDebut", "type": "date",   "label": "Date début", "required": True},
                    {"name": "dateFin",   "type": "date",   "label": "Date fin",   "required": True},
                    {"name": "societe",   "type": "string", "label": "Société",    "required": False},
                ])
            )
        )
        print("DS inserted")

    # 2. Créer GridView 325
    cur.execute("SELECT id FROM APP_GridViews WHERE id = 325")
    existing_gv = cur.fetchone()
    if existing_gv:
        cur.execute(
            """UPDATE APP_GridViews SET
                nom=?, description=?, data_source_code=?, columns_config=?,
                show_totals=1, total_columns=?, default_sort=?, page_size=100
               WHERE id=325""",
            (
                "Achats - Détail Complet",
                "Détail lignes achats : fournisseur, article, famille, dépôt, montant HT, TTC, remise, CMUP",
                "DS_ACH_DETAIL_COMPLET",
                columns_config,
                json.dumps(["Montant HT", "Montant TTC", "Quantite"]),
                json.dumps([{"field": "Date", "direction": "desc"}]),
            )
        )
        print("GridView 325 updated:", cur.rowcount)
    else:
        cur.execute(
            """INSERT INTO APP_GridViews
               (nom, description, data_source_code, columns_config, show_totals,
                total_columns, default_sort, page_size, is_public, actif)
               VALUES (?, ?, ?, ?, 1, ?, ?, 100, 1, 1)""",
            (
                "Achats - Détail Complet",
                "Détail lignes achats : fournisseur, article, famille, dépôt, montant HT, TTC, remise, CMUP",
                "DS_ACH_DETAIL_COMPLET",
                columns_config,
                json.dumps(["Montant HT", "Montant TTC", "Quantite"]),
                json.dumps([{"field": "Date", "direction": "desc"}]),
            )
        )
        cur.execute("SELECT MAX(id) FROM APP_GridViews")
        new_id = cur.fetchone()[0]
        print(f"GridView inserted with id={new_id}")

print("Done.")
