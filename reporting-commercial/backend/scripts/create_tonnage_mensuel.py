# -*- coding: utf-8 -*-
"""
Cree la datasource DS_VTE_TONNAGE_MENSUEL + le GridView "Tonnage par Mois"
(tonnage vendu par mois x representant x article), puis ajoute l'entree de menu
pour un tenant donne (defaut : ALEAFOOD).

Portage OptiBoard de la procedure Sage [ALEA_FOOD].[dbo].[_PS_TONNAGE], qui filtre
la sortie de [_PS_ChiffreAffaires] sur :
    catalogue = 'Cafe'
    [DATE bl] entre @dateMin et @dateMax
    souche = 'VENTE'
    DL_Remise01REM_Valeur = 0
    ISNULL([Géré en Tonnage], 'Non') = @GereTonnage

Idempotent : relancable sans creer de doublon.

    python scripts/create_tonnage_mensuel.py                 # tenant ALEAFOOD
    python scripts/create_tonnage_mensuel.py --dwh PORCELAMED
    python scripts/create_tonnage_mensuel.py --no-menu

Portage des filtres de la procedure
-----------------------------------
* [Géré en Tonnage] : information libre article, table [IL_Articles], jointe via
  entity_key = cbMarq de l'article = [Articles].[Code interne].
  60 articles marques 'Oui' sur ALEAFOOD, dont 10 presents dans [Articles].
* Mesure du tonnage : [Lignes_des_ventes].[Quantité]. Les articles geres en tonnage
  ont [Unité Poids] = 'Kilogramme' et un [Poids net] a 0 : la quantite EST le poids
  en kg. Ordre de grandeur verifie : 60 a 105 tonnes / mois en 2025.
* DL_Remise01REM_Valeur = 0 -> [Remise 1] = '0,00 %'. Attention, cette colonne est
  du texte formate dans le DWH (et non un numerique) : toute comparaison a 0 leve
  une erreur de conversion.
* catalogue = 'Cafe' -> [Catalogue 1] = 'CAFE' (parametrable).
* [DATE bl] -> [Lignes_des_ventes].[Date] sur les 'Bon de livraison'.
* /!\\ souche = 'VENTE' n'est PAS porte : la souche n'existe que dans
  [Entête_des_ventes], table incomplete sur ALEAFOOD (546 lignes). Impact mesure
  comme negligeable : sur les documents disponibles, 553 sont en souche 'Ventes'
  contre 1 en 'Consignation'. A rebrancher une fois l'ETL de l'entete repare.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import central_cursor, client_cursor

DS_CODE = "DS_VTE_TONNAGE_MENSUEL"
GV_NOM = u"Tonnage par Mois"
GV_CODE = "GV_TONNAGE_MENSUEL"
MENU_PARENT_FALLBACK = 2  # dossier "Chiffre d'Affaires"

QUERY_TEMPLATE = u"""SELECT
    FORMAT(li.[Date], 'yyyy-MM')                       AS [Periode],
    YEAR(li.[Date])                                    AS [Annee],
    MONTH(li.[Date])                                   AS [Mois],
    LTRIM(RTRIM(cl.[Représentant]))                    AS [Representant],
    li.[Code article]                                  AS [Code Article],
    MIN(li.[Désignation ligne])                        AS [Designation],
    li.[Catalogue 1]                                   AS [Catalogue],
    SUM(li.[Quantité])                                 AS [Tonnage Kg],
    CAST(SUM(li.[Quantité]) / 1000.0 AS DECIMAL(19,3)) AS [Tonnage T],
    SUM(li.[Montant HT Net])                           AS [Montant HT],
    COUNT(DISTINCT li.[N° Pièce])                      AS [Nb BL],
    li.societe                                         AS [Societe],
    ROW_NUMBER() OVER (
        ORDER BY FORMAT(li.[Date], 'yyyy-MM') DESC,
                 LTRIM(RTRIM(cl.[Représentant])), li.[Code article]
    )                                                  AS [Ordre Ligne]
FROM [Lignes_des_ventes] li
JOIN [Articles] ar
      ON ar.[Code Article] = li.[Code article]
     AND ar.societe = li.societe
JOIN [IL_Articles] il
      ON il.entity_key = CAST(ar.[Code interne] AS NVARCHAR(50))
     AND il.societe = li.societe
LEFT JOIN [Clients] cl
      ON cl.[Code client] = li.[Code client]
     AND cl.societe = li.societe
WHERE li.[Date] BETWEEN @dateDebut AND @dateFin
  AND ISNULL(il.[Géré en Tonnage], N'Non') = ISNULL(@gereTonnage, N'Oui')
  AND li.[Catalogue 1]    = ISNULL(@catalogue, N'CAFE')
  AND li.[Type Document]  = ISNULL(@typeDocument, N'Bon de livraison')
  AND li.[Remise 1]       = N'0,00 %'
  AND (@societe      IS NULL OR li.societe = @societe)
  AND (@representant IS NULL OR LTRIM(RTRIM(cl.[Représentant])) = @representant)
GROUP BY
    FORMAT(li.[Date], 'yyyy-MM'), YEAR(li.[Date]), MONTH(li.[Date]),
    LTRIM(RTRIM(cl.[Représentant])), li.[Code article], li.[Catalogue 1], li.societe"""
# NB : pas d'ORDER BY final. Le endpoint /grids/{id}/data encapsule la requete dans
# des sous-requetes (COUNT + OFFSET/FETCH) ou SQL Server interdit ORDER BY ; l'ordre
# d'affichage est porte par default_sort.
# ATTENTION : default_sort doit viser une colonne de BASE, jamais [Ordre Ligne] qui
# est calculee par ROW_NUMBER(). Le wrapper de pagination fait
# "SELECT * FROM (requete) ORDER BY [colonne de tri]" : trier sur une colonne issue
# d'une fonction de fenetrage fait re-executer la requete interne
# (mesure : 152,7 s contre 1,2 s pour 400 lignes).

PARAMETERS = [
    {"name": "dateDebut", "type": "date", "label": u"Date début", "required": True,
     "source": "global", "global_key": "dateDebut", "default": "FIRST_DAY_YEAR"},
    {"name": "dateFin", "type": "date", "label": u"Date fin", "required": True,
     "source": "global", "global_key": "dateFin", "default": "TODAY"},
    {"name": "gereTonnage", "type": "select", "label": u"Géré en tonnage", "required": False,
     "options": [{"value": "Oui", "label": u"Oui"}, {"value": "Non", "label": u"Non"}],
     "default": "Oui"},
    {"name": "catalogue", "type": "string", "label": u"Catalogue", "required": False,
     "default": "CAFE"},
    {"name": "typeDocument", "type": "string", "label": u"Type de document", "required": False,
     "default": "Bon de livraison"},
    {"name": "representant", "type": "string", "label": u"Représentant", "required": False},
    {"name": "societe", "type": "select", "label": u"Société", "required": False,
     "source": "query",
     "query": "SELECT code as value, nom + ' (' + code + ')' as label "
              "FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": u"(Toutes)"},
]

COLUMNS = [
    {"field": "Periode",      "header": u"Période",      "width": 100, "sortable": True, "filterable": True,  "format": None,       "align": "center", "visible": True,  "pinned": "left"},
    {"field": "Annee",        "header": u"Année",        "width":  80, "sortable": True, "filterable": True,  "format": None,       "align": "center", "visible": False, "pinned": None},
    {"field": "Mois",         "header": u"Mois",         "width":  70, "sortable": True, "filterable": True,  "format": None,       "align": "center", "visible": False, "pinned": None},
    {"field": "Representant", "header": u"Représentant", "width": 180, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Code Article", "header": u"Code article", "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Designation",  "header": u"Désignation",  "width": 260, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Catalogue",    "header": u"Catalogue",    "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Tonnage Kg",   "header": u"Tonnage (kg)", "width": 130, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "Tonnage T",    "header": u"Tonnage (T)",  "width": 120, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "Montant HT",   "header": u"Montant HT",   "width": 150, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Nb BL",        "header": u"Nb BL",        "width":  90, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "Societe",      "header": u"Société",      "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Ordre Ligne",  "header": u"Ordre",        "width":  80, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": False, "pinned": None},
]

FEATURES = {
    "show_search": True, "show_column_filters": True, "show_grouping": True,
    "show_column_toggle": True, "show_export": True, "show_pagination": True,
    "show_page_size": True, "allow_sorting": True, "display_full_height": True,
}

DESCRIPTION = (u"Tonnage vendu par mois, représentant et article, sur les articles "
               u"gérés en tonnage et sans remise. Portage de la procédure Sage "
               u"« _PS_TONNAGE ».")


def upsert_datasource(cur):
    cur.execute("SELECT id FROM APP_DataSources_Templates WHERE code = ?", (DS_CODE,))
    row = cur.fetchone()
    params = json.dumps(PARAMETERS, ensure_ascii=False)
    if row:
        cur.execute(
            """UPDATE APP_DataSources_Templates
               SET nom = ?, description = ?, query_template = ?, parameters = ?,
                   category = 'ventes', actif = 1
               WHERE code = ?""",
            (GV_NOM, DESCRIPTION, QUERY_TEMPLATE, params, DS_CODE))
        print("DataSource %s : mise a jour" % DS_CODE)
    else:
        cur.execute(
            """INSERT INTO APP_DataSources_Templates
               (code, nom, type, category, description, query_template, parameters,
                is_system, actif, date_creation)
               VALUES (?, ?, 'query', 'ventes', ?, ?, ?, 0, 1, GETDATE())""",
            (DS_CODE, GV_NOM, DESCRIPTION, QUERY_TEMPLATE, params))
        print("DataSource %s : creee" % DS_CODE)


def upsert_gridview(cur):
    cur.execute("SELECT id FROM APP_GridViews WHERE code = ?", (GV_CODE,))
    row = cur.fetchone()
    cols = json.dumps(COLUMNS, ensure_ascii=False)
    feats = json.dumps(FEATURES, ensure_ascii=False)
    sort = json.dumps({"field": "Periode", "direction": "desc"})
    totals = json.dumps(["Tonnage Kg", "Tonnage T", "Montant HT", "Nb BL"])
    if row:
        gv_id = row[0]
        cur.execute(
            """UPDATE APP_GridViews
               SET nom = ?, description = ?, data_source_code = ?, columns_config = ?,
                   features = ?, default_sort = ?, total_columns = ?, show_totals = 1,
                   page_size = 100, actif = 1, date_modification = GETDATE()
               WHERE id = ?""",
            (GV_NOM, DESCRIPTION, DS_CODE, cols, feats, sort, totals, gv_id))
        print("GridView %s (id=%s) : mis a jour" % (GV_CODE, gv_id))
    else:
        cur.execute(
            """INSERT INTO APP_GridViews
               (nom, code, description, data_source_code, columns_config, features,
                default_sort, total_columns, show_totals, page_size, is_custom,
                is_customized, actif, date_creation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 100, 0, 0, 1, GETDATE())""",
            (GV_NOM, GV_CODE, DESCRIPTION, DS_CODE, cols, feats, sort, totals))
        cur.execute("SELECT id FROM APP_GridViews WHERE code = ?", (GV_CODE,))
        gv_id = cur.fetchone()[0]
        print("GridView %s : cree (id=%s)" % (GV_CODE, gv_id))
    return gv_id


def upsert_menu(dwh_code, gv_id):
    """Entree de menu dans la base du tenant : visibilite limitee a ce client."""
    with client_cursor(dwh_code) as cur:
        cur.execute(
            "SELECT id FROM APP_Menus WHERE type = 'gridview' AND target_id = ?", (gv_id,))
        row = cur.fetchone()
        if row:
            print("Menu %s : deja present (id=%s)" % (dwh_code, row[0]))
            return

        cur.execute(
            u"SELECT TOP 1 id FROM APP_Menus "
            u"WHERE type = 'folder' AND nom LIKE N'%Chiffre%Affaires%' ORDER BY id")
        parent = cur.fetchone()
        parent_id = parent[0] if parent else MENU_PARENT_FALLBACK

        cur.execute("SELECT ISNULL(MAX(ordre), 0) + 1 FROM APP_Menus WHERE parent_id = ?",
                    (parent_id,))
        ordre = cur.fetchone()[0]

        cur.execute(
            """INSERT INTO APP_Menus (nom, code, icon, parent_id, ordre, type,
                                      target_id, actif, is_custom, is_customized, date_creation)
               VALUES (?, ?, 'Package', ?, ?, 'gridview', ?, 1, 0, 0, GETDATE())""",
            (GV_NOM, GV_CODE, parent_id, ordre, gv_id))
        cur.execute("SELECT id FROM APP_Menus WHERE type = 'gridview' AND target_id = ?", (gv_id,))
        new_id = cur.fetchone()[0]
        print("Menu %s : cree (id=%s, parent=%s, ordre=%s)" % (dwh_code, new_id, parent_id, ordre))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dwh", default="ALEAFOOD", help="code DWH du tenant (defaut: ALEAFOOD)")
    ap.add_argument("--no-menu", action="store_true", help="ne pas creer l'entree de menu")
    args = ap.parse_args()

    with central_cursor() as cur:
        upsert_datasource(cur)
        gv_id = upsert_gridview(cur)

    if not args.no_menu:
        upsert_menu(args.dwh, gv_id)

    print("Termine.")


if __name__ == "__main__":
    main()
