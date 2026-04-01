"""
Script pour mettre à jour le paramètre @societe en select (combobox) - V2
=========================================================================
Utilise APP_DWH pour récupérer les sociétés disponibles
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import execute_query, get_db_cursor


# Nouveau format du paramètre societe comme select
# Utilise APP_DWH avec:
# - societe_db comme VALUE (valeur utilisee dans les donnees/filtres)
# - nom comme LABEL (nom affiche dans le dropdown)
# IMPORTANT: La colonne societe_db doit exister et etre remplie dans APP_DWH
# Executez 005_add_societe_db_column.sql pour ajouter cette colonne
SOCIETE_PARAM = {
    "name": "societe",
    "label": "Société",
    "type": "select",
    "source": "query",
    "query": "SELECT COALESCE(societe_db, nom) as value, nom as label FROM APP_DWH WHERE actif = 1 ORDER BY nom",
    "allow_null": True,
    "null_label": "(Toutes les sociétés)",
    "required": False
}


def update_templates_societe_param():
    """Met à jour le paramètre societe dans tous les templates"""
    print("\n" + "="*70)
    print("MISE A JOUR DU PARAMETRE SOCIETE EN SELECT (V2)")
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

                print(f"  [OK] {template['code']}")
                updated += 1

        except Exception as e:
            print(f"  [ERROR] {template['code']}: {e}")
            errors += 1

    print("\n" + "-"*70)
    print(f"RESUME: {updated} templates mis à jour, {errors} erreurs")
    print("-"*70 + "\n")

    return updated, errors


def test_query():
    """Teste la requête pour les sociétés"""
    print("\n=== TEST REQUETE SOCIETES ===\n")
    try:
        result = execute_query(
            "SELECT COALESCE(societe_db, nom) as value, nom as label FROM APP_DWH WHERE actif = 1 ORDER BY nom",
            use_cache=False
        )
        print(f"Sociétés disponibles ({len(result)}):")
        for r in result:
            print(f"  - Label: {r['label']}, Value: {r['value']}")
    except Exception as e:
        print(f"Erreur: {e}")
        print("\nSi societe_db n'existe pas, executez:")
        print("  backend/sql/005_add_societe_db_column.sql")


if __name__ == "__main__":
    test_query()
    update_templates_societe_param()
