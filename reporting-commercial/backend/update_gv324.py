from app.database_unified import central_cursor
import json

new_query = """SELECT
    li.[Code client]               AS [Code Client],
    li.[Intitulé client]           AS [Client],
    li.[societe]                   AS [Societe],
    en.[Code représentant]         AS [Code Representant],
    en.[Nom représentant]          AS [Representant],
    en.[Catégorie Comptable]       AS [Categorie Comptable],
    en.[Intitulé tiers payeur]     AS [Tiers Payeur],
    li.[Code article]              AS [Code Article],
    li.[Désignation ligne]         AS [Article],
    li.[Catalogue 1]               AS [Famille],
    li.[Catalogue 2]               AS [Sous-Famille],
    li.[Code dépôt]                AS [Code Depot],
    li.[Intitulé dépôt]            AS [Depot],
    li.[Code d'affaire]            AS [Code Affaire],
    li.[Intitulé affaire]          AS [Affaire],
    li.[Type Document]             AS [Type Document],
    li.[N° Pièce]                  AS [N Piece],
    li.[Date BL]                   AS [Date],
    YEAR(li.[Date BL])             AS [Annee],
    MONTH(li.[Date BL])            AS [Mois],
    FORMAT(li.[Date BL], 'yyyy-MM') AS [Periode],
    li.Quantité                    AS [Quantite],
    li.[Prix unitaire]             AS [Prix Unitaire],
    li.[Remise 1]                  AS [Remise],
    li.[Montant HT Net]            AS [CA HT],
    li.[Montant TTC Net]           AS [CA TTC],
    li.[Prix de revient]           AS [Prix Revient],
    li.Quantité * li.[Prix de revient]                              AS [Cout Revient],
    li.[Montant HT Net] - li.Quantité * li.[Prix de revient]        AS [Marge Brute],
    CASE WHEN li.[Montant HT Net] <> 0
        THEN ROUND(100.0 * (li.[Montant HT Net] - li.Quantité * li.[Prix de revient]) / li.[Montant HT Net], 2)
        ELSE 0 END                 AS [Taux Marge],
    li.[Poids net]                 AS [Poids Net],
    en.Expédition                  AS [Expedition]
FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Valorise CA] = 'Oui'
  AND li.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR li.[societe] = @societe)
ORDER BY li.[Date BL] DESC"""

columns_config = json.dumps([
    {"field": "Date",              "header": "Date",            "width": 100, "sortable": True, "filterable": True, "format": "date",     "align": "center", "visible": True,  "pinned": None},
    {"field": "N Piece",           "header": "N° Pièce",        "width": 130, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Type Document",     "header": "Type Doc.",        "width": 120, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Code Client",       "header": "Code Client",     "width": 110, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Client",            "header": "Client",          "width": 220, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": "left"},
    {"field": "Categorie Comptable","header": "Catégorie",      "width": 130, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Tiers Payeur",      "header": "Tiers Payeur",    "width": 160, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Code Representant", "header": "Code Repr.",      "width":  90, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Representant",      "header": "Représentant",    "width": 160, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Code Article",      "header": "Code Article",    "width": 120, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Article",           "header": "Article",         "width": 220, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Famille",           "header": "Famille",         "width": 140, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Sous-Famille",      "header": "Sous-Famille",    "width": 130, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Code Depot",        "header": "Code Dépôt",      "width":  90, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Depot",             "header": "Dépôt",           "width": 140, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Affaire",           "header": "Affaire",         "width": 150, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Societe",           "header": "Société",         "width": 120, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Periode",           "header": "Période",         "width":  90, "sortable": True, "filterable": True, "format": None,       "align": "center", "visible": False, "pinned": None},
    {"field": "Annee",             "header": "Année",           "width":  70, "sortable": True, "filterable": True, "format": None,       "align": "center", "visible": False, "pinned": None},
    {"field": "Mois",              "header": "Mois",            "width":  60, "sortable": True, "filterable": True, "format": None,       "align": "center", "visible": False, "pinned": None},
    {"field": "Quantite",          "header": "Qté",             "width":  80, "sortable": True, "filterable": True, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "Prix Unitaire",     "header": "PU HT",           "width": 110, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Remise",            "header": "Remise %",        "width":  80, "sortable": True, "filterable": True, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "CA HT",             "header": "CA HT",           "width": 140, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "CA TTC",            "header": "CA TTC",          "width": 140, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": False, "pinned": None},
    {"field": "Cout Revient",      "header": "Coût Revient",    "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": False, "pinned": None},
    {"field": "Marge Brute",       "header": "Marge Brute",     "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Taux Marge",        "header": "Taux Marge %",    "width": 100, "sortable": True, "filterable": True, "format": "percent",  "align": "right",  "visible": True,  "pinned": None},
    {"field": "Poids Net",         "header": "Poids Net",       "width":  90, "sortable": True, "filterable": True, "format": None,       "align": "right",  "visible": False, "pinned": None},
    {"field": "Expedition",        "header": "Expédition",      "width": 120, "sortable": True, "filterable": True, "format": None,       "align": "left",   "visible": False, "pinned": None},
])

with central_cursor() as cur:
    # Update datasource query
    cur.execute(
        "UPDATE APP_DataSources_Templates SET query_template = ? WHERE code = 'DS_VTE_CA_CLIENT'",
        (new_query,)
    )
    print("DS updated:", cur.rowcount)

    # Update GridView 324
    cur.execute(
        """UPDATE APP_GridViews SET
            nom = ?,
            description = ?,
            columns_config = ?,
            show_totals = 1,
            total_columns = ?,
            default_sort = ?,
            page_size = 100
           WHERE id = 324""",
        (
            "Chiffre d'Affaires - Détail Complet",
            "Détail lignes ventes : client, article, représentant, famille, dépôt, CA, marge, remise",
            columns_config,
            json.dumps(["CA HT", "CA TTC", "Marge Brute", "Quantite"]),
            json.dumps([{"field": "Date", "direction": "desc"}]),
        )
    )
    print("GridView 324 updated:", cur.rowcount)

print("Done.")
