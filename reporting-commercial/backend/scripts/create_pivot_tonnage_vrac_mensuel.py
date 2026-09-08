# -*- coding: utf-8 -*-
"""
Cree la datasource DS_VTE_TONNAGE_VRAC_MENSUEL + le Pivot V2
"Tonnage Vrac par Mois", puis ajoute l'entree de menu pour un tenant donne
(defaut : ALEAFOOD).

Restitue la forme reelle de l'etat Sage, qui est un tableau croise :
    LIGNES   : Representant > Intitule client > Designation article
    COLONNES : mois de la date document (janvier ... decembre)
    VALEURS  : Quantite (somme), en kg

Remplace la forme "grille" de DS_VTE_TONNAGE_VRAC (GridView 760), qui gardait le
mois en ligne. Le GridView reste en place : meme perimetre, presentation a plat.

Idempotent : relancable sans creer de doublon.

    python scripts/create_pivot_tonnage_vrac_mensuel.py
    python scripts/create_pivot_tonnage_vrac_mensuel.py --dwh PORCELAMED
    python scripts/create_pivot_tonnage_vrac_mensuel.py --no-menu

Portage des parametres de la boite de dialogue Sage
---------------------------------------------------
* "Du" / "Au" portent sur [Date document] (et non [Date BL] comme les etats de
  tonnage conditionne). Colonne renseignee a 100 % sur ALEAFOOD.
* "Catalogue" propose CAFE VERT, CAFE TORREFIE VRAC et CAFE TORREFIE VRAC -
  MELANGE : ce sont des valeurs de [Catalogue 3] (CL_No3 dans la vue
  _VKS_Ventes), et non de [Catalogue 1] comme dans _PS_TONNAGE. Verifie sur
  ALEAFOOD : 16 423 / 2 750 / 902 lignes respectivement.
  C'est un SELECTEUR, pas le perimetre : laisser le parametre vide ne doit pas
  restreindre a ces trois valeurs. Le perimetre reste celui de la requete
  d'origine, [Catalogue 1] = 'CAFE' hors articles geres en tonnage — sinon les
  articles conditionnes en 1 kg (CAFE EL FENNA 1KG, CAFE EL MESRARA 1KG...)
  disparaissent de l'etat alors que Sage les affiche.
* Le perimetre vrac est coherent avec le filtre [Géré en Tonnage] <> 'Oui' :
  aucune ligne de ces trois catalogues n'est marquee 'Oui' (elles valent '' ou
  'Non'), et toutes sont en [Catalogue 1] = 'CAFE'. Les deux definitions se
  recoupent donc exactement, le filtre est conserve par securite.
* Les autres filtres sont ceux de la requete sur _VKS_Ventes : DO_Type >= 3
  (exprime en NOT IN) et DL_Remise01REM_Valeur = 0 -> [Remise 1] = '0,00 %',
  colonne stockee en texte formate dans le DWH.
* /!\\ [Souche] = 'Vente' n'est toujours pas portable : DO_Souche n'existe que
  dans [Entête_des_ventes], table incomplete sur ALEAFOOD. Voir
  create_tonnage_vrac.py.

Mise en forme des colonnes
--------------------------
[Date Document] est renvoyee comme une VRAIE date, ramenee au premier jour du
mois. Le regroupement en libelles ("janvier"...) est confie a l'axe du pivot via
date_grouping = "mois" : c'est le moteur qui produit et ordonne les libelles,
la ou une chaine calculee en SQL serait triee alphabetiquement (aout avant
avril). Le grain SQL reste mensuel, donc le volume ne change pas.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import central_cursor, client_cursor

DS_CODE = "DS_VTE_TONNAGE_VRAC_MENSUEL"
PV_NOM = u"Tonnage Vrac par Mois"
PV_CODE = "PV_TONNAGE_VRAC_MENSUEL"
MENU_PARENT_FALLBACK = 2  # dossier "Chiffre d'Affaires"

QUERY_TEMPLATE = u"""SELECT
    LTRIM(RTRIM(cl.[Représentant]))                        AS [Representant],
    li.[Intitulé client]                                   AS [Client],
    ar.[Désignation Article]                               AS [Designation],
    DATEFROMPARTS(YEAR(li.[Date document]),
                  MONTH(li.[Date document]), 1)            AS [Date Document],
    li.[Catalogue 3]                                       AS [Catalogue],
    SUM(li.[Quantité])                                     AS [Tonnage Kg],
    SUM(li.[Montant HT Net])                               AS [Montant HT],
    li.societe                                             AS [Societe]
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
WHERE li.[Date document] BETWEEN @dateDebut AND @dateFin
  AND ISNULL(il.[Géré en Tonnage], N'Non') <> N'Oui'
  AND li.[Type Document] NOT IN (N'Devis', N'Bon de commande', N'Préparation de livraison')
  AND li.[Remise 1] = N'0,00 %'
  AND li.[Catalogue 1] = N'CAFE'
  AND (@catalogue IS NULL OR li.[Catalogue 3] = @catalogue)
  AND (@societe      IS NULL OR li.societe = @societe)
  AND (@representant IS NULL OR LTRIM(RTRIM(cl.[Représentant])) = @representant)
GROUP BY
    LTRIM(RTRIM(cl.[Représentant])), li.[Intitulé client], ar.[Désignation Article],
    DATEFROMPARTS(YEAR(li.[Date document]), MONTH(li.[Date document]), 1),
    li.[Catalogue 3], li.societe"""

PARAMETERS = [
    {"name": "dateDebut", "type": "date", "label": u"Du", "required": True,
     "source": "global", "global_key": "dateDebut", "default": "FIRST_DAY_YEAR"},
    {"name": "dateFin", "type": "date", "label": u"Au", "required": True,
     "source": "global", "global_key": "dateFin", "default": "TODAY"},
    {"name": "catalogue", "type": "select", "label": u"Catalogue", "required": False,
     "options": [{"value": "CAFE VERT", "label": u"CAFE VERT"},
                 {"value": "CAFE TORREFIE VRAC", "label": u"CAFE TORREFIE VRAC"},
                 {"value": "CAFE TORREFIE VRAC - MELANGE",
                  "label": u"CAFE TORREFIE VRAC - MELANGE"}],
     "allow_null": True, "null_label": u"(Tous les vracs)"},
    {"name": "representant", "type": "string", "label": u"Représentant", "required": False},
    {"name": "societe", "type": "select", "label": u"Société", "required": False,
     "source": "query",
     "query": "SELECT code as value, nom + ' (' + code + ')' as label "
              "FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": u"(Toutes)"},
]


def _axis(field, label, date_grouping=None):
    return {"field": field, "label": label, "order": None,
            "type": "date" if date_grouping else "text",
            "date_grouping": date_grouping,
            "numeric_grouping": None, "text_grouping": None}


ROWS_CONFIG = [
    _axis("Representant", u"Représentant"),
    _axis("Client", u"Intitulé"),
    _axis("Designation", u"Désignation"),
]

COLUMNS_CONFIG = [_axis("Date Document", u"Date document", date_grouping="mois")]

VALUES_CONFIG = [
    {"field": "Tonnage Kg", "aggregation": "SUM", "label": u"Tonnage (kg)",
     "format": "number", "decimals": 2, "percentOf": None,
     "summary_aggregation": None, "show_in_totals": True},
]

FILTERS_CONFIG = [{"field": "Catalogue", "type": "text", "default": None, "values": None}]

DESCRIPTION = (u"Tonnage vrac croisé : représentant › client › article en lignes, "
               u"mois de la date document en colonnes. Reproduit l'état Sage "
               u"« tonnage vrac par mois ».")


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
            (PV_NOM + u" (croisé)", PV_CODE, parent_id, ordre, pv_id))
        cur.execute("SELECT id FROM APP_Menus WHERE type = 'pivot-v2' AND target_id = ?", (pv_id,))
        new_id = cur.fetchone()[0]
        print("Menu %s : cree (id=%s, parent=%s, ordre=%s)" % (dwh_code, new_id, parent_id, ordre))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dwh", default="ALEAFOOD")
    ap.add_argument("--no-menu", action="store_true")
    args = ap.parse_args()

    with central_cursor() as cur:
        upsert_datasource(cur)
        pv_id = upsert_pivot(cur)

    if not args.no_menu:
        upsert_menu(args.dwh, pv_id)

    print("Termine.")


if __name__ == "__main__":
    main()
