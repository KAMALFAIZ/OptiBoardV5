# -*- coding: utf-8 -*-
"""
Cree la datasource DS_VTE_TONNAGE_CLIENT_ARTICLE + le Pivot V2
"Etat de tonnage par mois, representant et client", puis ajoute l'entree de menu
pour un tenant donne (defaut : ALEAFOOD).

Restitue la forme REELLE de l'etat Sage, qui est un tableau croise et non une
grille :
    LIGNES   : Representant > mois (Date BL) > Intitule client
    COLONNES : Designation abregee de l'article
    VALEURS  : Quantite (somme), en kg

C'est le pendant "tableau croise" de DS_VTE_TONNAGE_CLIENT (GridView 761), qui
porte le meme perimetre mais garde l'article en ligne. Les deux partagent
exactement les memes filtres, issus de [_PS_ChiffreAffaires_Tonnage].

Idempotent : relancable sans creer de doublon.

    python scripts/create_pivot_tonnage_client_article.py
    python scripts/create_pivot_tonnage_client_article.py --dwh PORCELAMED
    python scripts/create_pivot_tonnage_client_article.py --no-menu

Points de portage specifiques a cette forme
-------------------------------------------
* [Designation Abregee] reproduit le calcul de la vue _VKS_Ventes :
      replace(replace(AR_Design, 'CAFE CITTA D''ITALIA ', ''), 'CAFE LA VARENNE - ', '')
  applique a [Articles].[Désignation Article]. Ce sont ces libelles raccourcis qui
  servent d'en-tetes de colonnes (ALEA EXPRESSO, BLUE MOON, CAFE CALEAFFE...).
* [Periode Libelle] produit "septembre 2026" comme dans Sage, via un CASE sur
  MONTH() plutot que FORMAT(date,'MMMM yyyy','fr-FR') : FORMAT est nettement plus
  couteux en SQL Server, et le CASE ne depend pas de la langue du serveur.
  [Periode] ('yyyy-MM') est conservee a cote pour le tri chronologique.
* Le grain descend jusqu'a l'article : c'est indispensable pour qu'il puisse
  servir de dimension de colonnes. Les mesures restent additives, donc les totaux
  et sous-totaux du pivot sont exacts a tous les niveaux.
* Nb documents n'est volontairement PAS expose : un COUNT DISTINCT n'est pas
  additif, le pivot le sommerait et afficherait un total faux.

Filtres communs, repris de la procedure : date BL, DO_Type >= 3 (exprime en
NOT IN), remise nulle ([Remise 1] = '0,00 %', colonne stockee en texte formate
dans le DWH), et [Géré en Tonnage] via l'information libre article. La procedure
ne filtre sur aucun catalogue, et sa boite de dialogue Sage ne propose que
Du, Au et Type article.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import central_cursor, client_cursor

DS_CODE = "DS_VTE_TONNAGE_CLIENT_ARTICLE"
PV_NOM = u"Etat de tonnage par mois, représentant et client"
PV_CODE = "PV_TONNAGE_CLIENT_ARTICLE"
MENU_PARENT_FALLBACK = 2  # dossier "Chiffre d'Affaires"

QUERY_TEMPLATE = u"""SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(co.[nom])), N''), LTRIM(RTRIM(cl.[Représentant])))        AS [Representant],
    ISNULL(co.[fonction], N'(non renseignée)')             AS [Fonction],
    CONVERT(CHAR(7), li.[Date BL], 126)                    AS [Periode],
    CASE MONTH(li.[Date BL])
        WHEN  1 THEN N'janvier'   WHEN  2 THEN N'février' WHEN  3 THEN N'mars'
        WHEN  4 THEN N'avril'     WHEN  5 THEN N'mai'      WHEN  6 THEN N'juin'
        WHEN  7 THEN N'juillet'   WHEN  8 THEN N'août'     WHEN  9 THEN N'septembre'
        WHEN 10 THEN N'octobre'   WHEN 11 THEN N'novembre' ELSE N'décembre'
    END + N' ' + CAST(YEAR(li.[Date BL]) AS NVARCHAR(4))   AS [Periode Libelle],
    li.[Intitulé client]                                   AS [Client],
    REPLACE(REPLACE(ar.[designation],
        'CAFE CITTA D''ITALIA ', ''), 'CAFE LA VARENNE - ', '')
                                                           AS [Designation Abregee],
    SUM(li.[Quantité])                                     AS [Tonnage Kg],
    SUM(li.[Montant HT Net])                               AS [Montant HT],
    li.societe                                             AS [Societe]
FROM (
    -- Partir des ARTICLES geres en tonnage (une soixantaine) et non des lignes
    -- de vente (573 000) : c'est le seul ordre de jointure qui tienne sans index
    -- sur le DWH. Mesure ALEAFOOD, septembre : 1,6 s contre une expiration.
    SELECT ar.[Code Article] AS [code_art], ar.[Désignation Article] AS [designation],
           ar.societe
    FROM [Articles] ar
    JOIN [IL_Articles] il
          ON il.entity_key = CAST(ar.[Code interne] AS NVARCHAR(50))
         AND il.societe = ar.societe
    WHERE ISNULL(il.[Géré en Tonnage], N'') = ISNULL(@gereTonnage, N'Oui')
) ar
JOIN [Lignes_des_ventes] li
      ON li.[Code article] = ar.[code_art]
     AND li.societe = ar.societe
LEFT JOIN [Clients] cl
      ON cl.[Code client] = li.[Code client]
     AND cl.societe = li.societe
LEFT JOIN (
    SELECT TRY_CAST([Code collaborateur] AS INT) AS [code], societe,
           [Nom collaborateur] AS [nom], [Fonction collaborateur] AS [fonction]
    FROM [Collaborateurs]
) co ON co.[code] = cl.[Code représentant] AND co.societe = li.societe
WHERE li.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND li.[Type Document] NOT IN (N'Devis', N'Bon de commande', N'Préparation de livraison')
  AND li.[Remise 1] = N'0,00 %'
  AND (
        @fonction IS NULL OR @fonction = N'TOUTES'
     OR (@fonction = N'COMMERCIAUX'
         AND co.[fonction] IN (N'Vendeur', N'V-Traditionnel', N'V-traditionnel'))
     OR (@fonction NOT IN (N'TOUTES', N'COMMERCIAUX')
         AND co.[fonction] = @fonction)
      )
  AND (@societe      IS NULL OR li.societe = @societe)
  AND (@client       IS NULL OR li.[Code client] = @client)
  AND (@representant IS NULL OR COALESCE(NULLIF(LTRIM(RTRIM(co.[nom])), N''), LTRIM(RTRIM(cl.[Représentant]))) = @representant)
GROUP BY
    COALESCE(NULLIF(LTRIM(RTRIM(co.[nom])), N''), LTRIM(RTRIM(cl.[Représentant]))),
    ISNULL(co.[fonction], N'(non renseignée)'),
    CONVERT(CHAR(7), li.[Date BL], 126),
    CASE MONTH(li.[Date BL])
        WHEN  1 THEN N'janvier'   WHEN  2 THEN N'février' WHEN  3 THEN N'mars'
        WHEN  4 THEN N'avril'     WHEN  5 THEN N'mai'      WHEN  6 THEN N'juin'
        WHEN  7 THEN N'juillet'   WHEN  8 THEN N'août'     WHEN  9 THEN N'septembre'
        WHEN 10 THEN N'octobre'   WHEN 11 THEN N'novembre' ELSE N'décembre'
    END + N' ' + CAST(YEAR(li.[Date BL]) AS NVARCHAR(4)),
    li.[Intitulé client],
    REPLACE(REPLACE(ar.[designation],
        'CAFE CITTA D''ITALIA ', ''), 'CAFE LA VARENNE - ', ''),
    li.societe"""
# Volume : cet etat est lourd par nature (representant x mois x client x article).
# Mesures ALEAFOOD : 1 mois = 657 lignes / 2,4 s ; 1 an = 11 251 / 11,6 s ;
# 10 ans (plage par defaut du viewer) = 47 352 / ~31-50 s, au-dela du timeout de
# 60 s du frontend une fois le rendu compris. D'ou les choix ci-dessous :
#   - CONVERT + CASE plutot que FORMAT(), nettement moins couteux en SQL Server ;
#   - seules les colonnes reellement consommees par le pivot sont renvoyees
#     (ni code article, ni code client, ni ville, ni Tonnage T), pour reduire la
#     charge utile JSON et le travail de rendu.
# Cela ne dispense pas de borner la periode : l'etat Sage d'origine est consulte
# sur une journee ou un mois.

PARAMETERS = [
    {"name": "dateDebut", "type": "date", "label": u"Date début (date BL)", "required": True,
     "source": "global", "global_key": "dateDebut", "default": "FIRST_DAY_YEAR"},
    {"name": "dateFin", "type": "date", "label": u"Date fin (date BL)", "required": True,
     "source": "global", "global_key": "dateFin", "default": "TODAY"},
    {"name": "gereTonnage", "type": "select", "label": u"Type article", "required": False,
     "options": [{"value": "Oui", "label": u"Oui (articles en tonnage)"},
                 {"value": "", "label": u"(non renseigné)"},
                 {"value": "Non", "label": u"Non"}],
     "default": "Oui"},
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


def _axis(field, label):
    return {"field": field, "label": label, "order": None, "type": "text",
            "date_grouping": None, "numeric_grouping": None, "text_grouping": None}


ROWS_CONFIG = [
    _axis("Representant", u"Représentant"),
    _axis("Periode Libelle", u"Date BL"),
    _axis("Client", u"Intitulé"),
]

COLUMNS_CONFIG = [_axis("Designation Abregee", u"Désignation abrégé")]

VALUES_CONFIG = [
    {"field": "Tonnage Kg", "aggregation": "SUM", "label": u"Tonnage (kg)",
     "format": "number", "decimals": 2, "percentOf": None,
     "summary_aggregation": None, "show_in_totals": True},
]

FILTERS_CONFIG = [{"field": "Societe", "type": "text", "default": None, "values": None}]

DESCRIPTION = (u"Tonnage vendu, croisé : représentant › mois › client en lignes, "
               u"désignation abrégée de l'article en colonnes. Reproduit la forme "
               u"de l'état Sage « tonnage par mois par représentants et par clients ».")


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
            (PV_NOM, DESCRIPTION, QUERY_TEMPLATE, params, DS_CODE))
        print("DataSource %s : mise a jour" % DS_CODE)
    else:
        cur.execute(
            """INSERT INTO APP_DataSources_Templates
               (code, nom, type, category, description, query_template, parameters,
                is_system, actif, date_creation)
               VALUES (?, ?, 'query', 'ventes', ?, ?, ?, 0, 1, GETDATE())""",
            (DS_CODE, PV_NOM, DESCRIPTION, QUERY_TEMPLATE, params))
        print("DataSource %s : creee" % DS_CODE)


def upsert_pivot(cur):
    cur.execute("SELECT id FROM APP_Pivots_V2 WHERE code = ?", (PV_CODE,))
    row = cur.fetchone()
    j = lambda v: json.dumps(v, ensure_ascii=False)
    if row:
        pv_id = row[0]
        cur.execute(
            """UPDATE APP_Pivots_V2
               SET nom = ?, description = ?, data_source_code = ?,
                   rows_config = ?, columns_config = ?, values_config = ?,
                   filters_config = ?, show_grand_totals = 1, show_subtotals = 1,
                   grand_total_position = 'bottom', subtotal_position = 'bottom',
                   is_public = 1, updated_at = GETDATE()
               WHERE id = ?""",
            (PV_NOM, DESCRIPTION, DS_CODE, j(ROWS_CONFIG), j(COLUMNS_CONFIG),
             j(VALUES_CONFIG), j(FILTERS_CONFIG), pv_id))
        print("Pivot %s (id=%s) : mis a jour" % (PV_CODE, pv_id))
    else:
        cur.execute(
            """INSERT INTO APP_Pivots_V2
               (nom, code, description, data_source_code, rows_config, columns_config,
                values_config, filters_config, show_grand_totals, show_subtotals,
                grand_total_position, subtotal_position, is_public, is_custom,
                is_customized, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 'bottom', 'bottom', 1, 0, 0,
                       GETDATE(), GETDATE())""",
            (PV_NOM, PV_CODE, DESCRIPTION, DS_CODE, j(ROWS_CONFIG), j(COLUMNS_CONFIG),
             j(VALUES_CONFIG), j(FILTERS_CONFIG)))
        cur.execute("SELECT id FROM APP_Pivots_V2 WHERE code = ?", (PV_CODE,))
        pv_id = cur.fetchone()[0]
        print("Pivot %s : cree (id=%s)" % (PV_CODE, pv_id))
    return pv_id


def upsert_menu(dwh_code, pv_id):
    """Entree de menu dans la base du tenant : visibilite limitee a ce client.

    Le target_id d'un menu pointe sur l'id CENTRAL du pivot : _pv_read resout
    ensuite la ligne cliente equivalente par code (a defaut par nom), et retombe
    sur la centrale si le tenant n'a pas sa propre copie.
    """
    with client_cursor(dwh_code) as cur:
        cur.execute(
            "SELECT id FROM APP_Menus WHERE type = 'pivot-v2' AND target_id = ?", (pv_id,))
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
               VALUES (?, ?, 'Grid3x3', ?, ?, 'pivot-v2', ?, 1, 0, 0, GETDATE())""",
            (PV_NOM, PV_CODE, parent_id, ordre, pv_id))
        cur.execute("SELECT id FROM APP_Menus WHERE type = 'pivot-v2' AND target_id = ?", (pv_id,))
        new_id = cur.fetchone()[0]
        print("Menu %s : cree (id=%s, parent=%s, ordre=%s)" % (dwh_code, new_id, parent_id, ordre))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dwh", default="ALEAFOOD", help="code DWH du tenant (defaut: ALEAFOOD)")
    ap.add_argument("--no-menu", action="store_true", help="ne pas creer l'entree de menu")
    args = ap.parse_args()

    with central_cursor() as cur:
        upsert_datasource(cur)
        pv_id = upsert_pivot(cur)

    if not args.no_menu:
        upsert_menu(args.dwh, pv_id)

    print("Termine.")


if __name__ == "__main__":
    main()
