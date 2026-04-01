"""
Script pour mettre à jour les menus CA afin qu'ils pointent vers les GridViews
==============================================================================
Ce script met à jour les menus existants de type 'datasource' pour qu'ils
pointent vers les GridViews correspondantes plutôt que vers les templates.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import execute_query, get_db_cursor


# Correspondance code datasource -> nom GridView
DATASOURCE_TO_GRIDVIEW = {
    "DS_VENTES_GLOBAL": "CA Global",
    "DS_VENTES_PAR_MOIS": "CA par Mois",
    "DS_VENTES_PAR_CLIENT": "CA par Client",
    "DS_VENTES_PAR_ARTICLE": "CA par Article",
    "DS_VENTES_PAR_CATALOGUE": "CA par Catalogue",
    "DS_VENTES_PAR_DEPOT": "CA par Depot",
    "DS_VENTES_PAR_COMMERCIAL": "CA par Commercial",
    "DS_VENTES_PAR_ZONE": "CA par Zone Geo",
    "DS_VENTES_PAR_AFFAIRE": "CA par Affaire",
}


def get_gridview_id(nom):
    """Récupère l'ID d'une GridView par son nom"""
    result = execute_query(
        "SELECT id FROM APP_GridViews WHERE nom = ?",
        (nom,),
        use_cache=False
    )
    return result[0]['id'] if result else None


def update_menu_targets():
    """Met à jour les target_id des menus pour pointer vers les GridViews"""
    print("\n" + "="*70)
    print("MISE A JOUR DES MENUS VERS LES GRIDVIEWS")
    print("="*70 + "\n")

    updated = 0
    errors = 0

    for ds_code, gridview_nom in DATASOURCE_TO_GRIDVIEW.items():
        try:
            # Trouver le GridView ID
            gridview_id = get_gridview_id(gridview_nom)
            if not gridview_id:
                print(f"  [WARN] GridView '{gridview_nom}' non trouvee")
                continue

            # Trouver le menu avec ce code
            menus = execute_query(
                "SELECT id, nom, target_id, type FROM APP_Menus WHERE code = ?",
                (ds_code,),
                use_cache=False
            )

            if not menus:
                print(f"  [WARN] Menu avec code '{ds_code}' non trouve")
                continue

            menu = menus[0]

            # Mettre à jour le menu
            with get_db_cursor() as cursor:
                cursor.execute("""
                    UPDATE APP_Menus
                    SET target_id = ?, type = 'gridview'
                    WHERE id = ?
                """, (gridview_id, menu['id']))

            print(f"  [OK] Menu '{menu['nom']}' -> GridView ID {gridview_id}")
            updated += 1

        except Exception as e:
            print(f"  [ERROR] {ds_code}: {e}")
            errors += 1

    print("\n" + "-"*70)
    print(f"RESUME: {updated} menus mis a jour, {errors} erreurs")
    print("-"*70 + "\n")

    return updated, errors


def list_ca_menus():
    """Liste les menus CA actuels"""
    print("\n=== MENUS CA ACTUELS ===\n")

    menus = execute_query("""
        SELECT m.id, m.nom, m.code, m.type, m.target_id, g.nom as gridview_nom
        FROM APP_Menus m
        LEFT JOIN APP_GridViews g ON m.target_id = g.id AND m.type = 'gridview'
        WHERE m.code LIKE 'DS_VENTES%'
        ORDER BY m.id
    """, use_cache=False)

    for m in menus:
        target_info = f"-> GridView: {m['gridview_nom']} (id={m['target_id']})" if m['gridview_nom'] else f"target_id={m['target_id']}"
        print(f"  [{m['id']}] {m['nom']} ({m['type']}) {target_info}")

    return menus


if __name__ == "__main__":
    # Afficher l'état actuel
    list_ca_menus()

    # Mettre à jour
    update_menu_targets()

    # Afficher le nouvel état
    print("\n=== APRES MISE A JOUR ===")
    list_ca_menus()
