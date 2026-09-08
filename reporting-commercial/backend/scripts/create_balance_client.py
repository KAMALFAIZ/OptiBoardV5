# -*- coding: utf-8 -*-
"""
Cree la datasource DS_VTE_BALANCE_CLIENT + le GridView "Balance Client"
(une ligne par client : total CA, total reglement, solde, plafond, derniere date BL),
puis ajoute l'entree de menu pour un tenant donne (defaut : ALEAFOOD).

Equivalent OptiBoard de l'etat Sage "Balance client". C'est l'agregation par client
des mouvements de l'etat "Situation client" (voir create_situation_client.py) :
les deux etats partagent exactement la meme base de calcul.

Idempotent : relancable sans creer de doublon.

    python scripts/create_balance_client.py                 # tenant ALEAFOOD
    python scripts/create_balance_client.py --dwh PORCELAMED
    python scripts/create_balance_client.py --no-menu       # DS + GridView seulement

Regles metier
-------------
* Table pilote = [Clients] (LEFT JOIN sur les mouvements) : les clients sans aucun
  mouvement apparaissent avec un solde a 0, comme dans l'etat Sage.
* Total CA = SUM([Montant TTC Net]) de [Lignes_des_ventes] sur BL / BR /
  avoirs financiers + factures non issues d'un BL (meme regle anti double-comptage
  que la Situation client). Retours et avoirs sont deja negatifs dans cette table.
* Total Reglement = SUM([Montant]) de [Règlements_Clients]. Peut etre negatif
  (impayes / annulations), le solde devient alors positif.
* Solde = Total CA - Total Reglement.
* [Der Date BL] = date du dernier bon de livraison a la date d'arrete.
* Verifie contre l'etat Sage au 10/07/2026 (client 3421077) :
  CA 7 394 999 / reglements 7 200 084 / solde 194 915 / plafond 2 400 000.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import central_cursor, client_cursor

DS_CODE = "DS_VTE_BALANCE_CLIENT"
GV_NOM = u"Balance Client"
GV_CODE = "GV_BALANCE_CLIENT"
MENU_PARENT_FALLBACK = 15  # dossier "Suivi des Creances"

QUERY_TEMPLATE = u"""SELECT
    ISNULL(NULLIF(cl.[Code payeur], ''), cl.[Code client]) AS [Code Tiers Payeur],
    cl.[Code client]                                       AS [Code Client],
    cl.[Ville]                                             AS [Ville],
    COALESCE(NULLIF(LTRIM(RTRIM(co.[Nom collaborateur])), N''), LTRIM(RTRIM(cl.[Représentant]))) AS [Representant],
    cl.[Intitulé]                                          AS [Intitule],
    ISNULL(mv.[Total CA], 0)                               AS [Total CA],
    ISNULL(rg.[Total Reglement], 0)                        AS [Total Reglement],
    ISNULL(mv.[Total CA], 0) - ISNULL(rg.[Total Reglement], 0) AS [Solde],
    cl.[Risque client]                                     AS [Risque],
    cl.[Encours de l'autorisation]                         AS [Plafond],
    mv.[Der Date BL]                                       AS [Der Date BL],
    cl.societe                                             AS [Societe],
    ROW_NUMBER() OVER (ORDER BY cl.societe, cl.[Code client]) AS [Ordre Ligne]
FROM [Clients] cl
LEFT JOIN [Collaborateurs] co
      ON CAST(co.[Code collaborateur] AS INT) = cl.[Code représentant]
     AND co.societe = cl.societe
LEFT JOIN (
    SELECT
        li.societe                          AS societe,
        li.[Code client]                    AS cc,
        SUM(li.[Montant TTC Net])           AS [Total CA],
        MAX(CASE WHEN li.[Type Document] = N'Bon de livraison'
                 THEN li.[Date] END)        AS [Der Date BL]
    FROM [Lignes_des_ventes] li
    WHERE li.[Date] <= @dateFin
      AND (
            li.[Type Document] IN (N'Bon de livraison', N'Bon de retour', N'Bon avoir financier')
         OR (li.[Type Document] LIKE N'%acture%' AND ISNULL(li.[N° Pièce BL], '') = '')
          )
    GROUP BY li.societe, li.[Code client]
) mv ON mv.societe = cl.societe AND mv.cc = cl.[Code client]
LEFT JOIN (
    SELECT
        rc.societe                          AS societe,
        rc.[Code client]                    AS cc,
        SUM(rc.[Montant])                   AS [Total Reglement]
    FROM [Règlements_Clients] rc
    WHERE rc.[Date] <= @dateFin
    GROUP BY rc.societe, rc.[Code client]
) rg ON rg.societe = cl.societe AND rg.cc = cl.[Code client]
WHERE (@societe IS NULL OR cl.societe = @societe)
  AND (@client  IS NULL OR cl.[Code client] = @client)"""
# NB : pas d'ORDER BY final. Le endpoint /grids/{id}/data encapsule la requete dans
# des sous-requetes (COUNT + OFFSET/FETCH) ou SQL Server interdit ORDER BY ; l'ordre
# d'affichage est porte par default_sort.
# ATTENTION : default_sort doit viser une colonne de BASE, jamais [Ordre Ligne] qui
# est calculee par ROW_NUMBER(). Le wrapper de pagination fait
# "SELECT * FROM (requete) ORDER BY [colonne de tri]" : trier sur une colonne issue
# d'une fonction de fenetrage fait re-executer la requete interne
# (mesure : 152,7 s contre 1,2 s pour 400 lignes).

PARAMETERS = [
    {"name": "dateFin", "type": "date", "label": u"Arrêté au", "required": True,
     "source": "global", "global_key": "dateFin", "default": "TODAY"},
    {"name": "client", "type": "string", "label": u"Code client", "required": False},
    {"name": "societe", "type": "select", "label": u"Société", "required": False,
     "source": "query",
     "query": "SELECT code as value, nom + ' (' + code + ')' as label "
              "FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": u"(Toutes)"},
]

COLUMNS = [
    {"field": "Code Tiers Payeur", "header": u"Code tiers payeur", "width": 140, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": "left"},
    {"field": "Code Client",       "header": u"Code client",       "width": 110, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Ville",             "header": u"Ville",             "width": 140, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Representant",      "header": u"Représentant",      "width": 180, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Intitule",          "header": u"Intitulé",          "width": 240, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Total CA",          "header": u"Total CA",          "width": 150, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Total Reglement",   "header": u"Total règlement",   "width": 150, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Solde",             "header": u"Solde",             "width": 150, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Risque",            "header": u"Risque",            "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Plafond",           "header": u"Plafond",           "width": 140, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Der Date BL",       "header": u"Der. date BL",      "width": 120, "sortable": True, "filterable": True,  "format": "date",     "align": "center", "visible": True,  "pinned": None},
    {"field": "Societe",           "header": u"Société",           "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Ordre Ligne",       "header": u"Ordre",             "width":  80, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": False, "pinned": None},
]

FEATURES = {
    "show_search": True, "show_column_filters": True, "show_grouping": True,
    "show_column_toggle": True, "show_export": True, "show_pagination": True,
    "show_page_size": True, "allow_sorting": True, "display_full_height": True,
}

DESCRIPTION = (u"Balance client : total CA, total règlements et solde par client "
               u"à une date d'arrêté, avec plafond d'encours et date du dernier BL. "
               u"Équivalent de l'état Sage « Balance client ».")


def upsert_datasource(cur):
    cur.execute("SELECT id FROM APP_DataSources_Templates WHERE code = ?", (DS_CODE,))
    row = cur.fetchone()
    params = json.dumps(PARAMETERS, ensure_ascii=False)
    if row:
        cur.execute(
            """UPDATE APP_DataSources_Templates
               SET nom = ?, description = ?, query_template = ?, parameters = ?,
                   category = 'recouvrement', actif = 1
               WHERE code = ?""",
            (GV_NOM, DESCRIPTION, QUERY_TEMPLATE, params, DS_CODE))
        print("DataSource %s : mise a jour" % DS_CODE)
    else:
        cur.execute(
            """INSERT INTO APP_DataSources_Templates
               (code, nom, type, category, description, query_template, parameters,
                is_system, actif, date_creation)
               VALUES (?, ?, 'query', 'recouvrement', ?, ?, ?, 0, 1, GETDATE())""",
            (DS_CODE, GV_NOM, DESCRIPTION, QUERY_TEMPLATE, params))
        print("DataSource %s : creee" % DS_CODE)


def upsert_gridview(cur):
    cur.execute("SELECT id FROM APP_GridViews WHERE code = ?", (GV_CODE,))
    row = cur.fetchone()
    cols = json.dumps(COLUMNS, ensure_ascii=False)
    feats = json.dumps(FEATURES, ensure_ascii=False)
    sort = json.dumps({"field": "Code Tiers Payeur", "direction": "asc"})
    totals = json.dumps(["Total CA", "Total Reglement", "Solde"])
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
            u"WHERE type = 'folder' AND nom LIKE N'%Créances%' ORDER BY id")
        parent = cur.fetchone()
        parent_id = parent[0] if parent else MENU_PARENT_FALLBACK

        cur.execute("SELECT ISNULL(MAX(ordre), 0) + 1 FROM APP_Menus WHERE parent_id = ?",
                    (parent_id,))
        ordre = cur.fetchone()[0]

        cur.execute(
            """INSERT INTO APP_Menus (nom, code, icon, parent_id, ordre, type,
                                      target_id, actif, is_custom, is_customized, date_creation)
               VALUES (?, ?, 'Scale', ?, ?, 'gridview', ?, 1, 0, 0, GETDATE())""",
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
