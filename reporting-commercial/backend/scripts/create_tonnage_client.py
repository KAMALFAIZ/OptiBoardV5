# -*- coding: utf-8 -*-
"""
Cree la datasource DS_VTE_TONNAGE_CLIENT + le GridView "Tonnage par Client"
(tonnage vendu par mois x representant x client), puis ajoute l'entree de menu
pour un tenant donne (defaut : ALEAFOOD).

Portage OptiBoard de la procedure Sage
[ALEA_FOOD].[dbo].[_PS_ChiffreAffaires_Tonnage].

Idempotent : relancable sans creer de doublon.

    python scripts/create_tonnage_client.py                 # tenant ALEAFOOD
    python scripts/create_tonnage_client.py --dwh PORCELAMED
    python scripts/create_tonnage_client.py --no-menu

Portage des filtres de la procedure
-----------------------------------
* DL_DateBL between @dateMin and @dateMax -> [Lignes_des_ventes].[Date BL].
  Colonne renseignee a 100 % sur ALEAFOOD (569 117 lignes, aucun NULL), donc
  utilisable telle quelle. C'est la date de la procedure, pas DO_Date.
* F_DOCLIGNE.DO_Type >= 3 : exclut Devis (0), Bon de commande (1) et Preparation
  de livraison (2). Exprime en NOT IN pour rester robuste aux libelles.
* DL_Remise01REM_Valeur = 0 -> [Remise 1] = '0,00 %'. Colonne stockee en texte
  formate dans le DWH : une comparaison a 0 leve une erreur de conversion.
* isnull([Géré en Tonnage], '') = @GereTonnage : information libre article
  ([IL_Articles]), jointe en LEFT JOIN via entity_key = [Articles].[Code interne].
  Noter le ISNULL a '' (et non a 'Non') : c'est bien la semantique de la procedure,
  les articles sans valeur tombent dans le groupe ''.
  Releve 2025 sur ALEAFOOD, filtres de la procedure appliques :
      'Oui' -> 47 956 lignes / 967 190 kg
      ''    -> 32 794 lignes / 1 213 901 kg
      'Non' -> aucune ligne
  Le defaut 'Non' de la procedure ne renverrait donc rien : le parametre est
  expose avec 'Oui' par defaut, et 'Non' / '' restent selectionnables.
* PAS de filtre catalogue, contrairement a _PS_TONNAGE : la procedure porte sur
  tous les catalogues. Un parametre @catalogue optionnel est expose (vide = tous).
* PAS de filtre de souche dans cette procedure : contrairement aux etats
  DS_VTE_TONNAGE_MENSUEL et DS_VTE_TONNAGE_VRAC, il n'y a donc ici aucun ecart
  du a l'absence de DO_Souche dans le DWH. Le portage est complet sur ce volet.
* Signes : la procedure force le negatif sur les types 4-5 et les provenances
  d'avoir. [Lignes_des_ventes] applique deja ces signes dans le DWH.
* Representant = F_COLLABORATEUR.CO_Nom via F_COMPTET.CO_No, soit le representant
  rattache au CLIENT -> [Clients].[Représentant].

Volet non porte : UNION ALL sur _Situation_Vendeur
-------------------------------------------------
La procedure ajoute une seconde branche "Valeur depot mobile", lue dans
[_Situation_Vendeur] : une ligne par representant portant une quantite et une
valeur de stock detenue, datee a @dateMax. Elle n'est pas reprise ici, pour deux
raisons distinctes :
1. Cette branche n'a PAS de dimension client (la procedure recopie le nom du
   representant dans [Intitulé]). Elle n'a donc pas sa place dans un etat dont le
   grain est mois x representant x CLIENT : elle y creerait de faux clients.
2. [_Situation_Vendeur] n'est pas synchronise dans le DWH. Les depots mobiles y
   existent bien, dans [Etat_Stock] ([DE_Intitule] = 'DEPOT MOBILE - <nom>',
   avec [Quantité en stock] et [Valeur du stock (montant)]), mais [Etat_Stock] est
   une PHOTO INSTANTANEE sans historique : le "where [Date] <= @dateMax" de la
   procedure n'y est pas reproductible.
Si la valeur des depots mobiles est utile, elle merite un etat separe, base sur
[Etat_Stock] filtre sur [DE_Intitule] LIKE 'DEPOT MOBILE%', en assumant qu'il
s'agit de la situation du jour et non d'un arrete a date.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import central_cursor, client_cursor

DS_CODE = "DS_VTE_TONNAGE_CLIENT"
GV_NOM = u"Tonnage par Client"
GV_CODE = "GV_TONNAGE_CLIENT"
MENU_PARENT_FALLBACK = 2  # dossier "Chiffre d'Affaires"

QUERY_TEMPLATE = u"""SELECT
    FORMAT(li.[Date BL], 'yyyy-MM')                    AS [Periode],
    YEAR(li.[Date BL])                                 AS [Annee],
    MONTH(li.[Date BL])                                AS [Mois],
    COALESCE(NULLIF(LTRIM(RTRIM(co.[Nom collaborateur])), N''), LTRIM(RTRIM(cl.[Représentant])))                    AS [Representant],
    ISNULL(co.[Fonction collaborateur], N'(non renseignée)')     AS [Fonction],
    li.[Code client]                                   AS [Code Client],
    MIN(li.[Intitulé client])                          AS [Client],
    MIN(cl.[Ville])                                    AS [Ville],
    SUM(li.[Quantité])                                 AS [Tonnage Kg],
    CAST(SUM(li.[Quantité]) / 1000.0 AS DECIMAL(19,3)) AS [Tonnage T],
    SUM(li.[Montant HT Net])                           AS [Montant HT],
    SUM(li.[Montant TTC Net])                          AS [Montant TTC],
    COUNT(DISTINCT li.[N° Pièce])                      AS [Nb Documents],
    li.societe                                         AS [Societe]
FROM [Lignes_des_ventes] li
JOIN [Articles] ar
      ON ar.[Code Article] = li.[Code article]
     AND ar.societe = li.societe
LEFT JOIN [IL_Articles] il
      ON il.entity_key = CAST(ar.[Code interne] AS NVARCHAR(50))
     AND il.societe = li.societe
LEFT JOIN [Clients] cl
      ON cl.[Code client] = li.[Code client]
     AND cl.societe = li.societe
LEFT JOIN [Collaborateurs] co
      ON CAST(co.[Code collaborateur] AS INT) = cl.[Code représentant]
     AND co.societe = li.societe
WHERE li.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND ISNULL(il.[Géré en Tonnage], N'') = ISNULL(@gereTonnage, N'Oui')
  AND li.[Type Document] NOT IN (N'Devis', N'Bon de commande', N'Préparation de livraison')
  AND li.[Remise 1] = N'0,00 %'
  AND (@catalogue    IS NULL OR li.[Catalogue 3] = @catalogue)
  AND (
        @fonction IS NULL OR @fonction = N'TOUTES'
     OR (@fonction = N'COMMERCIAUX'
         AND co.[Fonction collaborateur] IN (N'Vendeur', N'V-Traditionnel', N'V-traditionnel'))
     OR (@fonction NOT IN (N'TOUTES', N'COMMERCIAUX')
         AND co.[Fonction collaborateur] = @fonction)
      )
  AND (@societe      IS NULL OR li.societe = @societe)
  AND (@client       IS NULL OR li.[Code client] = @client)
  AND (@representant IS NULL OR COALESCE(NULLIF(LTRIM(RTRIM(co.[Nom collaborateur])), N''), LTRIM(RTRIM(cl.[Représentant]))) = @representant)
GROUP BY
    FORMAT(li.[Date BL], 'yyyy-MM'), YEAR(li.[Date BL]), MONTH(li.[Date BL]),
    COALESCE(NULLIF(LTRIM(RTRIM(co.[Nom collaborateur])), N''), LTRIM(RTRIM(cl.[Représentant]))),
    ISNULL(co.[Fonction collaborateur], N'(non renseignée)'), li.[Code client], li.societe"""
# NB : pas d'ORDER BY final. Le endpoint /grids/{id}/data encapsule la requete dans
# des sous-requetes (COUNT + OFFSET/FETCH) ou SQL Server interdit ORDER BY ; l'ordre
# d'affichage est porte par default_sort.
# ATTENTION : default_sort doit viser une colonne de BASE. Le wrapper de pagination
# fait "SELECT * FROM (requete) ORDER BY [colonne de tri]" : trier sur une colonne
# issue d'une fonction de fenetrage (ROW_NUMBER) fait re-executer la requete interne
# (mesure : 152,7 s contre 1,2 s pour 400 lignes). Aucune colonne OVER() ici.

PARAMETERS = [
    {"name": "dateDebut", "type": "date", "label": u"Date début (date BL)", "required": True,
     "source": "global", "global_key": "dateDebut", "default": "FIRST_DAY_YEAR"},
    {"name": "dateFin", "type": "date", "label": u"Date fin (date BL)", "required": True,
     "source": "global", "global_key": "dateFin", "default": "TODAY"},
    {"name": "gereTonnage", "type": "select", "label": u"Géré en tonnage", "required": False,
     "options": [{"value": "Oui", "label": u"Oui (articles en tonnage)"},
                 {"value": "", "label": u"(non renseigné)"},
                 {"value": "Non", "label": u"Non"}],
     "default": "Oui"},
    {"name": "catalogue", "type": "string", "label": u"Catalogue", "required": False},
    {"name": "client", "type": "string", "label": u"Code client", "required": False},
    {"name": "representant", "type": "string", "label": u"Représentant", "required": False},
    {"name": "fonction", "type": "select", "label": u"Fonction du représentant",
     "required": False,
     "options": [{"value": "COMMERCIAUX", "label": u"Commerciaux seuls"},
                 {"value": "Vendeur", "label": u"Vendeur"},
                 {"value": "V-Traditionnel", "label": u"V-Traditionnel"},
                 {"value": "Distributeur", "label": u"Distributeur"},
                 {"value": "Revendeur", "label": u"Revendeur"},
                 {"value": "Comptoir", "label": u"Comptoir"},
                 {"value": "Vrac", "label": u"Vrac"},
                 {"value": "Litige", "label": u"Litige"}],
     "allow_null": True, "null_label": u"(Toutes fonctions)"},
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
    {"field": "Code Client",  "header": u"Code client",  "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Client",       "header": u"Client",       "width": 240, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Ville",        "header": u"Ville",        "width": 140, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": True,  "pinned": None},
    {"field": "Tonnage Kg",   "header": u"Tonnage (kg)", "width": 130, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "Tonnage T",    "header": u"Tonnage (T)",  "width": 120, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "Montant HT",   "header": u"Montant HT",   "width": 150, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": True,  "pinned": None},
    {"field": "Montant TTC",  "header": u"Montant TTC",  "width": 150, "sortable": True, "filterable": False, "format": "currency", "align": "right",  "visible": False, "pinned": None},
    {"field": "Nb Documents", "header": u"Nb documents", "width": 110, "sortable": True, "filterable": False, "format": None,       "align": "right",  "visible": True,  "pinned": None},
    {"field": "Societe",      "header": u"Société",      "width": 120, "sortable": True, "filterable": True,  "format": None,       "align": "left",   "visible": False, "pinned": None},
]

FEATURES = {
    "show_search": True, "show_column_filters": True, "show_grouping": True,
    "show_column_toggle": True, "show_export": True, "show_pagination": True,
    "show_page_size": True, "allow_sorting": True, "display_full_height": True,
}

DESCRIPTION = (u"Tonnage vendu par mois, représentant et client, sur les articles "
               u"gérés en tonnage et sans remise, à partir de la date BL. "
               u"Portage de la procédure Sage « _PS_ChiffreAffaires_Tonnage » "
               u"(volet ventes).")


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
    totals = json.dumps(["Tonnage Kg", "Tonnage T", "Montant HT", "Nb Documents"])
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
               VALUES (?, ?, 'Users', ?, ?, 'gridview', ?, 1, 0, 0, GETDATE())""",
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
