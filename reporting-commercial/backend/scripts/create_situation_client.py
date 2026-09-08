# -*- coding: utf-8 -*-
"""
Cree la datasource DS_VTE_SITUATION_CLIENT + le GridView "Situation Client"
(grand livre client : documents de vente + reglements + solde cumule), puis
ajoute l'entree de menu pour un tenant donne (defaut : ALEAFOOD).

Equivalent OptiBoard de l'etat Sage "Situation client".

Idempotent : relancable sans creer de doublon.

    python scripts/create_situation_client.py                 # tenant ALEAFOOD
    python scripts/create_situation_client.py --dwh PORCELAMED
    python scripts/create_situation_client.py --no-menu       # DS + GridView seulement

Regles metier
-------------
* Colonne documents : agregation de [Lignes_des_ventes] par (societe, type, N piece).
  On n'utilise PAS [Entete_des_ventes] : sur certaines instances cette table n'est
  synchronisee que partiellement par l'agent ETL (ex. ALEAFOOD = 546 lignes contre
  573 373 dans Lignes_des_ventes).
* Anti double-comptage BL -> facture : une facture n'est retenue que si elle n'est
  pas issue d'un BL (ISNULL([N Piece BL], '') = ''). Les BL / BR / avoirs financiers
  sont toujours retenus.
* Les retours et avoirs portent deja un [Montant TTC Net] negatif dans
  Lignes_des_ventes (contrairement a Entete_des_ventes) : aucune inversion de signe.
* HAVING SUM(...) <> 0 ecarte les pieces a valeur nulle (bons de depot BD*).
* Solde = SUM([Montant TTC] - [Reglement]) OVER (PARTITION BY client
  ORDER BY date, ordre, piece). Les reglements d'une meme date sont ordonnes avant
  les documents (Ordre 0 / 1), comme dans l'etat Sage.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import central_cursor, client_cursor

DS_CODE = "DS_VTE_SITUATION_CLIENT"
GV_NOM = u"Situation Client"
GV_CODE = "GV_SITUATION_CLIENT"
MENU_PARENT_FALLBACK = 15  # dossier "Suivi des Creances"

QUERY_TEMPLATE = u"""SELECT
    m.[Date],
    m.[Code Client],
    m.[Client],
    m.[Nature],
    m.[N Piece],
    m.[Mode Reglement],
    m.[Reference],
    m.[Montant TTC],
    m.[Reglement],
    SUM(m.[Montant TTC] - m.[Reglement]) OVER (
        PARTITION BY m.[Code Client]
        ORDER BY m.[Date], m.[Ordre], m.[N Piece]
        ROWS UNBOUNDED PRECEDING
    ) AS [Solde],
    m.[Societe],
    CAST(m.[Code Client] AS NVARCHAR(50)) + N'|'
        + CONVERT(CHAR(8), m.[Date], 112) + N'|'
        + CAST(m.[Ordre] AS CHAR(1)) + N'|'
        + ISNULL(m.[N Piece], N'')                 AS [Ordre Ligne]
FROM (
    SELECT
        MIN(li.[Date])                              AS [Date],
        li.[Code client]                            AS [Code Client],
        MIN(li.[Intitulé client])                    AS [Client],
        li.[Type Document]                          AS [Nature],
        li.[N° Pièce]                                AS [N Piece],
        CAST(NULL AS NVARCHAR(255))                 AS [Mode Reglement],
        MIN(li.[Référence])                          AS [Reference],
        SUM(li.[Montant TTC Net])                   AS [Montant TTC],
        CAST(0 AS DECIMAL(19,4))                    AS [Reglement],
        1                                           AS [Ordre],
        li.societe                                  AS [Societe]
    FROM [Lignes_des_ventes] li
    WHERE li.[Date] <= @dateFin
      AND (@societe IS NULL OR li.societe = @societe)
      AND (@client  IS NULL OR li.[Code client] = @client)
      AND (
            li.[Type Document] IN (N'Bon de livraison', N'Bon de retour', N'Bon avoir financier')
         OR (li.[Type Document] LIKE N'%acture%' AND ISNULL(li.[N° Pièce BL], '') = '')
          )
    GROUP BY li.societe, li.[Code client], li.[Type Document], li.[N° Pièce]
    HAVING SUM(li.[Montant TTC Net]) <> 0

    UNION ALL

    SELECT
        rc.[Date]                                   AS [Date],
        rc.[Code client]                            AS [Code Client],
        rc.[Intitulé]                                AS [Client],
        N'Règlement'                                AS [Nature],
        rc.[N° piéce]                                AS [N Piece],
        rc.[Mode de règlement]                       AS [Mode Reglement],
        rc.[Référence]                              AS [Reference],
        CAST(0 AS DECIMAL(19,4))                    AS [Montant TTC],
        rc.[Montant]                                AS [Reglement],
        0                                           AS [Ordre],
        rc.societe                                  AS [Societe]
    FROM [Règlements_Clients] rc
    WHERE rc.[Date] <= @dateFin
      AND (@societe IS NULL OR rc.societe = @societe)
      AND (@client  IS NULL OR rc.[Code client] = @client)
      AND rc.[Montant] <> 0
) m"""
# NB 1 : pas d'ORDER BY final. Le endpoint /grids/{id}/data encapsule la requete
# dans des sous-requetes (COUNT + OFFSET/FETCH) ou SQL Server interdit ORDER BY ;
# l'ordre d'affichage est porte par la colonne [Ordre Ligne] via default_sort.
# NB 2 : [Ordre Ligne] est une CONCATENATION, surtout pas un ROW_NUMBER(). Le
# wrapper de pagination fait "SELECT * FROM (requete) ORDER BY [colonne de tri]" :
# trier sur une colonne issue d'une fonction de fenetrage fait re-executer la
# requete interne (mesure : 152,7 s contre 1,2 s pour 400 lignes). Ne jamais
# pointer default_sort sur une colonne calculee par OVER().
# La cle reproduit l'ordre exact du grand livre : client, date, reglements avant
# documents du meme jour (Ordre 0/1), puis numero de piece.

PARAMETERS = [
    {"name": "dateFin", "type": "date", "label": u"Situation au", "required": True,
     "source": "global", "global_key": "dateFin", "default": "TODAY"},
    {"name": "client", "type": "string", "label": u"Code client", "required": False},
    {"name": "societe", "type": "select", "label": u"Société", "required": False,
     "source": "query",
     "query": "SELECT code as value, nom + ' (' + code + ')' as label "
              "FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": u"(Toutes)"},
]

COLUMNS = [
    {"field": "Date",           "header": u"Date",                  "width": 100, "sortable": True, "filterable": True,  "format": "date",     "align": "center", "visible": True,  "pinned": None},
    {"field": "Code Client",    "header": u"Code client",           "width": 110, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": "left"},
    {"field": "Client",         "header": u"Client",                "width": 240, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": "left"},
    {"field": "Nature",         "header": u"Nature",                "width": 150, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "N Piece",        "header": u"N° pièce",              "width": 150, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Mode Reglement", "header": u"Mode de règlement",      "width": 180, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Reference",      "header": u"Référence",             "width": 140, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Montant TTC",    "header": u"Montant TTC",           "width": 140, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Reglement",      "header": u"Règlement",              "width": 140, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Solde",          "header": u"Solde",                 "width": 150, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Societe",        "header": u"Société",               "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Ordre Ligne",    "header": u"Ordre",                 "width":  80, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": False, "pinned": None},
]

FEATURES = {
    "show_search": True, "show_column_filters": True, "show_grouping": True,
    "show_column_toggle": True, "show_export": True, "show_pagination": True,
    "show_page_size": True, "allow_sorting": True, "display_full_height": True,
}

DESCRIPTION = (u"Grand livre client : documents de vente et règlements classés par date, "
               u"avec solde cumulé par client. Équivalent de l'état Sage "
               u"« Situation client ».")


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
    sort = json.dumps({"field": "Ordre Ligne", "direction": "asc"})
    totals = json.dumps(["Montant TTC", "Reglement"])
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
               VALUES (?, ?, 'FileText', ?, ?, 'gridview', ?, 1, 0, 0, GETDATE())""",
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
