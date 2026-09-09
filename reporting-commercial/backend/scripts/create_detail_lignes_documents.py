# -*- coding: utf-8 -*-
"""
Cree la datasource DS_VTE_DETAIL_LIGNES + le GridView "Detail Lignes Documents"
(detail ligne a ligne des documents de vente), puis ajoute l'entree de menu pour
un tenant donne (defaut : ALEAFOOD).

Equivalent OptiBoard de l'etat Sage "detail des lignes de documents".

Idempotent : relancable sans creer de doublon.

    python scripts/create_detail_lignes_documents.py                 # tenant ALEAFOOD
    python scripts/create_detail_lignes_documents.py --dwh PORCELAMED
    python scripts/create_detail_lignes_documents.py --no-menu

Origine des colonnes
--------------------
* Base            : [Lignes_des_ventes] (573 373 lignes sur ALEAFOOD, 2019 -> 2026).
* Representant    : [Clients].[Représentant] (representant rattache au client).
                    [Entête_des_ventes].[Nom représentant] serait plus fidele au
                    document mais cette table est incomplete sur ALEAFOOD.
* Categorie       : [Collaborateurs].[Fonction collaborateur] (Vendeur / Revendeur),
                    jointe sur le nom du representant.
* Utilisateur     : NON DISPONIBLE dans le DWH en l'etat. La vue Sage _VKS_Ventes
                    montre la source exacte : F_PROTECTIONCIAL.PROT_User, jointe sur
                    F_DOCLIGNE.cbCreationUser (donnee de LIGNE, pas d'en-tete).
                    Ni cbCreationUser ni PROT_User ne sont synchronises.
                    Ne pas confondre avec l'information libre d'en-tete
                    [IL_Entetes_Documents].[Utilisateur], qui existe bien dans le DWH
                    mais porte un tout autre contenu (un compte de domaine du type
                    "LAVARENNE\\F-Z TOUGAN", et non le login Sage "Halima" / "r.zineb"
                    affiche par l'etat).
                    Pour alimenter cette colonne : ajouter dans la requete ETL de
                    "Lignes des ventes" une jointure
                        left join F_PROTECTIONCIAL p on p.PROT_Guid = F_DOCLIGNE.cbCreationUser
                    et exposer p.PROT_User sous l'alias [Utilisateur]. La colonne du
                    GridView est deja en place et se remplira sans retoucher ce script.

Verifie contre l'etat Sage (BL25000062928 / BL25000062927 du 14/07/2026) :
quantites, prix unitaires, PU TTC, montants HT et TTC identiques.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import central_cursor, client_cursor

DS_CODE = "DS_VTE_DETAIL_LIGNES"
GV_NOM = u"Détail Lignes Documents"
GV_CODE = "GV_DETAIL_LIGNES_DOCUMENTS"
MENU_PARENT_FALLBACK = 3  # dossier "Documents Commerciaux"

QUERY_TEMPLATE = u"""SELECT
    li.[Type Document]                                     AS [Type Document],
    COALESCE(NULLIF(LTRIM(RTRIM(co.[nom])), N''), LTRIM(RTRIM(cl.[Représentant])))                        AS [Representant],
    li.[Intitulé client]                                   AS [Intitule],
    li.[N° Pièce]                                          AS [Piece Document],
    ISNULL(li.[Date document], li.[Date])                  AS [Date Document],
    CASE WHEN li.[Type Document] = N'Bon de livraison'
         THEN li.[N° Pièce] ELSE li.[N° Pièce BL] END      AS [N Piece],
    li.[Code article]                                      AS [Ref Article],
    li.[Désignation ligne]                                 AS [Designation],
    li.[Quantité]                                          AS [Quantite],
    li.[Prix unitaire]                                     AS [Prix Unitaire],
    li.[Prix unitaire TTC]                                 AS [PU TTC],
    li.[Montant HT Net]                                    AS [Montant HT],
    li.[Montant TTC Net]                                   AS [Montant TTC],
    CAST(NULL AS NVARCHAR(200))                            AS [Utilisateur],
    co.[fonction]                            AS [Categorie],
    li.[Code client]                                       AS [Code Client],
    li.societe                                             AS [Societe],
    ROW_NUMBER() OVER (
        ORDER BY ISNULL(li.[Date document], li.[Date]) DESC,
                 li.[N° Pièce] DESC, li.[Code article]
    )                                                      AS [Ordre Ligne]
FROM [Lignes_des_ventes] li
LEFT JOIN [Clients] cl
       ON cl.[Code client] = li.[Code client]
      AND cl.societe = li.societe
LEFT JOIN (
    SELECT TRY_CAST([Code collaborateur] AS INT) AS [code], societe,
           [Nom collaborateur] AS [nom], [Fonction collaborateur] AS [fonction]
    FROM [Collaborateurs]
) co ON co.[code] = cl.[Code représentant] AND co.societe = li.societe
WHERE ISNULL(li.[Date document], li.[Date]) BETWEEN @dateDebut AND @dateFin
  AND (@societe      IS NULL OR li.societe = @societe)
  AND (@client       IS NULL OR li.[Code client] = @client)
  AND (@typeDocument IS NULL OR li.[Type Document] = @typeDocument)"""
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
     "source": "global", "global_key": "dateDebut", "default": "FIRST_DAY_MONTH"},
    {"name": "dateFin", "type": "date", "label": u"Date fin", "required": True,
     "source": "global", "global_key": "dateFin", "default": "TODAY"},
    {"name": "client", "type": "string", "label": u"Code client", "required": False},
    {"name": "typeDocument", "type": "string", "label": u"Type de document", "required": False},
    {"name": "societe", "type": "select", "label": u"Société", "required": False,
     "source": "query",
     "query": "SELECT code as value, nom + ' (' + code + ')' as label "
              "FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": u"(Toutes)"},
]

COLUMNS = [
    {"field": "Type Document",  "header": u"Type Document",   "width": 150, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Representant",   "header": u"Représentant",    "width": 170, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Intitule",       "header": u"Intitulé",        "width": 220, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Piece Document", "header": u"Pièce document",  "width": 150, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Date Document",  "header": u"Date document",   "width": 115, "sortable": True, "filterable": True,  "format": "date",     "align": "center", "visible": True,  "pinned": None},
    {"field": "N Piece",        "header": u"N° pièce",        "width": 150, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Ref Article",    "header": u"Réf article",     "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Designation",    "header": u"Désignation",     "width": 240, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Quantite",       "header": u"Quantité",        "width":  90, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "Prix Unitaire",  "header": u"Prix unitaire",   "width": 120, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "PU TTC",         "header": u"PU TTC",          "width": 110, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Montant HT",     "header": u"Montant HT",      "width": 130, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Montant TTC",    "header": u"Montant TTC",     "width": 130, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Utilisateur",    "header": u"Utilisateur",     "width": 140, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Categorie",      "header": u"Catégorie",       "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Code Client",    "header": u"Code client",     "width": 110, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Societe",        "header": u"Société",         "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": False, "pinned": None},
    {"field": "Ordre Ligne",    "header": u"Ordre",           "width":  80, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": False, "pinned": None},
]

FEATURES = {
    "show_search": True, "show_column_filters": True, "show_grouping": True,
    "show_column_toggle": True, "show_export": True, "show_pagination": True,
    "show_page_size": True, "allow_sorting": True, "display_full_height": True,
}

DESCRIPTION = (u"Détail ligne à ligne des documents de vente : article, quantité, "
               u"prix unitaire HT et TTC, montants, représentant et utilisateur "
               u"créateur. Équivalent de l'état Sage « détail des lignes de documents ».")


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
    sort = json.dumps({"field": "Date Document", "direction": "desc"})
    totals = json.dumps(["Quantite", "Montant HT", "Montant TTC"])
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
            u"WHERE type = 'folder' AND nom LIKE N'%Documents Commerciaux%' ORDER BY id")
        parent = cur.fetchone()
        parent_id = parent[0] if parent else MENU_PARENT_FALLBACK

        cur.execute("SELECT ISNULL(MAX(ordre), 0) + 1 FROM APP_Menus WHERE parent_id = ?",
                    (parent_id,))
        ordre = cur.fetchone()[0]

        cur.execute(
            """INSERT INTO APP_Menus (nom, code, icon, parent_id, ordre, type,
                                      target_id, actif, is_custom, is_customized, date_creation)
               VALUES (?, ?, 'List', ?, ?, 'gridview', ?, 1, 0, 0, GETDATE())""",
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
