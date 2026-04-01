"""
Script pour mettre à jour le paramètre @societe en select (combobox)
=====================================================================
Ce script modifie les templates de DataSources pour que le paramètre
@societe soit un select avec les sociétés disponibles.
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import execute_query, get_db_cursor


# Nouveau format du paramètre societe comme select
SOCIETE_PARAM = {
    "name": "societe",
    "label": "Société",
    "type": "select",
    "source": "query",
    "query": "SELECT DISTINCT DB_Caption as value, DB_Caption as label FROM Lignes_des_ventes WHERE DB_Caption IS NOT NULL ORDER BY DB_Caption",
    "allow_null": True,
    "null_label": "(Toutes les sociétés)",
    "required": False
}


def update_templates_societe_param():
    """Met à jour le paramètre societe dans tous les templates"""
    print("\n" + "="*70)
    print("MISE A JOUR DU PARAMETRE SOCIETE EN SELECT")
    print("="*70 + "\n")

    # Récupérer tous les templates avec un paramètre societe
    templates = execute_query("""
        SELECT id, code, nom, parameters
        FROM APP_DataSources_Templates
        WHERE parameters LIKE '%societe%'
    """, use_cache=False)

    print(f"  {len(templates)} templates avec paramètre societe trouvés\n")

    updated = 0
    errors = 0

    for template in templates:
        try:
            params_str = template.get('parameters', '[]')

            # Parser les paramètres existants
            try:
                params = json.loads(params_str) if params_str else []
            except json.JSONDecodeError:
                params = []

            if not isinstance(params, list):
                params = []

            # Chercher et mettre à jour le paramètre societe
            param_updated = False
            new_params = []

            for p in params:
                if p.get('name') == 'societe':
                    # Remplacer par le nouveau format select
                    new_params.append(SOCIETE_PARAM)
                    param_updated = True
                else:
                    new_params.append(p)

            if param_updated:
                # Sauvegarder les nouveaux paramètres
                new_params_str = json.dumps(new_params, ensure_ascii=False)

                with get_db_cursor() as cursor:
                    cursor.execute("""
                        UPDATE APP_DataSources_Templates
                        SET parameters = ?
                        WHERE id = ?
                    """, (new_params_str, template['id']))

                print(f"  [OK] {template['code']} - paramètre societe mis à jour")
                updated += 1
            else:
                print(f"  [SKIP] {template['code']} - pas de paramètre societe à mettre à jour")

        except Exception as e:
            print(f"  [ERROR] {template['code']}: {e}")
            errors += 1

    print("\n" + "-"*70)
    print(f"RESUME: {updated} templates mis à jour, {errors} erreurs")
    print("-"*70 + "\n")

    return updated, errors


def verify_update():
    """Vérifie la mise à jour"""
    print("\n=== VERIFICATION ===\n")

    # Vérifier un template
    templates = execute_query("""
        SELECT TOP 3 code, nom, parameters
        FROM APP_DataSources_Templates
        WHERE parameters LIKE '%societe%'
    """, use_cache=False)

    for t in templates:
        print(f"Template: {t['code']}")
        try:
            params = json.loads(t['parameters']) if t['parameters'] else []
            societe_param = next((p for p in params if p.get('name') == 'societe'), None)
            if societe_param:
                print(f"  Type: {societe_param.get('type')}")
                print(f"  Source: {societe_param.get('source')}")
                print(f"  Allow null: {societe_param.get('allow_null')}")
                print(f"  Query: {societe_param.get('query', 'N/A')[:80]}...")
        except:
            print(f"  [Erreur parsing parameters]")
        print()


if __name__ == "__main__":
    update_templates_societe_param()
    verify_update()
