"""
Nettoyage des anciens menus du DWH KA et verification
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

from app.database_unified import client_cursor, execute_client, execute_central, execute_dwh

DWH_CODE = 'KA'

def check_and_clean():
    print(f"=== DWH {DWH_CODE} — Nettoyage APP_Menus client ===")

    # Compter les anciens menus dans la base client
    try:
        result = execute_client('SELECT COUNT(*) AS nb FROM APP_Menus', dwh_code=DWH_CODE)
        nb = result[0]['nb']
        print(f"  Menus existants dans OptiBoard_{DWH_CODE}: {nb}")
    except Exception as e:
        print(f"  Erreur lecture APP_Menus: {e}")
        return

    if nb > 0:
        try:
            with client_cursor(DWH_CODE) as cursor:
                cursor.execute('DELETE FROM APP_Menus')
            print(f"  {nb} anciens menus supprimes")
        except Exception as e:
            print(f"  Erreur suppression: {e}")
            return
    else:
        print("  Aucun ancien menu a supprimer (deja vide)")

    result = execute_client('SELECT COUNT(*) AS nb FROM APP_Menus', dwh_code=DWH_CODE)
    print(f"  Menus apres nettoyage: {result[0]['nb']}")


def test_central_menus():
    print(f"\n=== Menus centraux disponibles ===")
    result = execute_central('SELECT COUNT(*) AS nb FROM APP_Menus')
    print(f"  APP_Menus central: {result[0]['nb']} menus")

    sections = execute_central("""
        SELECT nom, ordre FROM APP_Menus
        WHERE parent_id IS NULL ORDER BY ordre
    """)
    print(f"  Sections ({len(sections)}):")
    for s in sections:
        print(f"    [{s['ordre']}] {s['nom']}")

    result = execute_central('SELECT COUNT(*) AS nb FROM APP_DataSources_Templates')
    print(f"  APP_DataSources_Templates: {result[0]['nb']} templates")


def test_datasource(ds_code):
    print(f"\n=== Test {ds_code} sur DWH {DWH_CODE} ===")

    templates = execute_central(
        "SELECT query_template FROM APP_DataSources_Templates WHERE code = ?",
        (ds_code,)
    )
    if not templates:
        print(f"  Template {ds_code} introuvable!")
        return

    query = templates[0]['query_template']

    from datetime import date
    date_fin = date.today().strftime('%Y-%m-%d')
    date_debut = f"{date.today().year}-01-01"

    # Remplacer les parametres par des valeurs litterales pour le test
    query_test = query.replace('@dateDebut', f"'{date_debut}'")
    query_test = query_test.replace('@dateFin', f"'{date_fin}'")
    query_test = query_test.replace("(@societe IS NULL OR [societe] = @societe)", "1=1")
    query_test = query_test.replace("(@societe IS NULL OR e.[societe] = @societe)", "1=1")
    query_test = query_test.replace("(@societe IS NULL OR l.[societe] = @societe)", "1=1")
    query_test = query_test.replace("(@societe IS NULL OR s.[societe] = @societe)", "1=1")

    try:
        result = execute_dwh(query_test, dwh_code=DWH_CODE)
        print(f"  OK — {len(result)} ligne(s)")
        if result:
            print(f"  Colonnes: {list(result[0].keys())}")
            if len(result) > 0:
                first = result[0]
                preview = {k: v for k, v in list(first.items())[:4]}
                print(f"  Apercu: {preview}")
    except Exception as e:
        print(f"  ERREUR: {e}")


if __name__ == '__main__':
    check_and_clean()
    test_central_menus()
    test_datasource('DS_KPI_RESUME')
    test_datasource('DS_VENTES_GLOBAL')
    test_datasource('DS_TOP10_CLIENTS')
    test_datasource('DS_FACTURES')
    print("\n=== Termine ===")
