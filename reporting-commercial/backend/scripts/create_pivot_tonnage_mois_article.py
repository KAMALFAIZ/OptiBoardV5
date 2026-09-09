# -*- coding: utf-8 -*-
"""
Cree le Pivot V2 "Etat de tonnage par mois, representant et article", puis ajoute
l'entree de menu pour un tenant donne (defaut : ALEAFOOD).

    LIGNES   : mois
    COLONNES : Representant > Designation abregee (hierarchie a deux niveaux)
    VALEURS  : Quantite (somme), en kg

C'est la troisieme mise en forme du meme perimetre, et il faut les distinguer :
- PV_TONNAGE_CLIENT_ARTICLE (267) : representant > mois > CLIENT en lignes,
  article en colonnes — l'etat Sage "par mois par representants et par clients".
- PV_TONNAGE_MOIS_ARTICLE (celui-ci) : mois en lignes, representant puis ARTICLE
  en colonnes — l'etat Sage "par mois par representants et par article".
- GV_TONNAGE_CLIENT (761) : la meme chose a plat, en grille.

Les trois partagent DS_VTE_TONNAGE_CLIENT_ARTICLE : aucune datasource
supplementaire n'est creee, donc aucun risque de voir les chiffres diverger
d'une presentation a l'autre. La dimension Client, presente dans le grain de la
datasource mais absente de ce pivot, est simplement agregee par le moteur.

Idempotent : relancable sans creer de doublon.

    python scripts/create_pivot_tonnage_mois_article.py
    python scripts/create_pivot_tonnage_mois_article.py --dwh PORCELAMED
    python scripts/create_pivot_tonnage_mois_article.py --no-menu

Volumetrie
----------
Les colonnes sont le produit representant x article : le garde-fou de
execute_pivot (MAX_PIVOT_CELLS) s'applique et refusera proprement une periode
trop large plutot que de fabriquer une reponse que le navigateur ne recevra pas.
Comme l'etat Sage d'origine, il se consulte sur un mois.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import central_cursor, client_cursor

DS_CODE = "DS_VTE_TONNAGE_CLIENT_ARTICLE"   # datasource partagee, non modifiee ici
PV_NOM = u"Etat de tonnage par mois, représentant et article"
PV_CODE = "PV_TONNAGE_MOIS_ARTICLE"
MENU_PARENT_FALLBACK = 2  # dossier "Chiffre d'Affaires"


def _axis(field, label):
    return {"field": field, "label": label, "order": None, "type": "text",
            "date_grouping": None, "numeric_grouping": None, "text_grouping": None}


ROWS_CONFIG = [_axis("Periode Libelle", u"Mois")]

COLUMNS_CONFIG = [
    _axis("Representant", u"Représentant"),
    _axis("Designation Abregee", u"Désignation abrégé"),
]

VALUES_CONFIG = [
    {"field": "Tonnage Kg", "aggregation": "SUM", "label": u"Tonnage (kg)",
     "format": "number", "decimals": 2, "percentOf": None,
     "summary_aggregation": None, "show_in_totals": True},
]

FILTERS_CONFIG = [{"field": "Societe", "type": "text", "default": None, "values": None}]

DESCRIPTION = (u"Tonnage croisé : mois en lignes, représentant puis désignation "
               u"abrégée de l'article en colonnes. Reproduit l'état Sage "
               u"« tonnage par mois par représentants et par article ». "
               u"Même périmètre et mêmes chiffres que « par client » (267), "
               u"seule la mise en forme change.")


def upsert_pivot(cur):
    cur.execute("SELECT id FROM APP_DataSources_Templates WHERE code = ?", (DS_CODE,))
    if not cur.fetchone():
        raise SystemExit(
            "DataSource %s absente — lancer d'abord "
            "scripts/create_pivot_tonnage_client_article.py" % DS_CODE)

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
            (PV_NOM, PV_CODE, parent_id, ordre, pv_id))
        cur.execute("SELECT id FROM APP_Menus WHERE type = 'pivot-v2' AND target_id = ?", (pv_id,))
        print("Menu %s : cree (id=%s, parent=%s, ordre=%s)" % (
            dwh_code, cur.fetchone()[0], parent_id, ordre))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dwh", default="ALEAFOOD")
    ap.add_argument("--no-menu", action="store_true")
    args = ap.parse_args()
    with central_cursor() as cur:
        pv_id = upsert_pivot(cur)
    if not args.no_menu:
        upsert_menu(args.dwh, pv_id)
    print("Termine.")


if __name__ == "__main__":
    main()
