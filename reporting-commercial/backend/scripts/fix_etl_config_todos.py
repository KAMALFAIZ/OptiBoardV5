"""
Script de correction : remplace les TODO dans 03_insert_etl_config_data.sql
par les vraies requetes depuis sync_tables.yaml.

Usage: python fix_etl_config_todos.py
"""
import yaml
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = os.path.join(SCRIPT_DIR, '..', 'etl', 'config', 'sync_tables.yaml')
SQL_PATH = os.path.join(SCRIPT_DIR, '..', 'sql', 'sql_jobs', '03_insert_etl_config_data.sql')
DIST_SQL_PATH = os.path.join(SCRIPT_DIR, '..', 'dist_client', 'sql', 'sql_jobs', '03_insert_etl_config_data.sql')


def load_yaml_queries():
    """Charge les requetes depuis le YAML, indexees par nom de table."""
    with open(YAML_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    queries = {}
    for table in config.get('tables', []):
        name = table.get('name', '')
        query = table.get('source', {}).get('query', '')
        if name and query:
            queries[name] = query
    return queries


def escape_for_tsql(query):
    """Echappe une requete pour insertion dans un string N'...' T-SQL."""
    # Normaliser les retours a la ligne
    q = query.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
    # Supprimer les espaces multiples
    q = re.sub(r'\s+', ' ', q).strip()
    # Supprimer le point-virgule final si present
    q = q.rstrip(';').strip()
    # Doubler les apostrophes pour T-SQL
    q = q.replace("'", "''")
    return q


def fix_sql_file(sql_path, yaml_queries):
    """Remplace les TODO dans le fichier SQL par les requetes du YAML."""
    with open(sql_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Mapping: texte TODO -> nom dans le YAML
    todo_mapping = {
        "TODO: Copier depuis sync_tables.yaml - Lignes des ventes (YAML L588)":
            "Lignes des ventes",
        "TODO: Copier depuis sync_tables.yaml - Entetes des ventes DO_Domaine=0 (YAML L303)":
            "Entêtes des ventes",
        "TODO: Copier depuis sync_tables.yaml - Imputation factures ventes (YAML L532)":
            "Imputation les factures des ventes",
        "TODO: Copier depuis sync_tables.yaml - Echeances ventes avec CTE (YAML L825)":
            "Echéances ventes",
        "TODO: Copier depuis sync_tables.yaml - Entetes des achats DO_Domaine=1 (YAML L1081)":
            "Entêtes des achats",
        "TODO: Copier depuis sync_tables.yaml - Imputation factures achats (YAML L1305)":
            "Imputation factures des achats",
        "TODO: Copier depuis sync_tables.yaml - Lignes des achats (YAML L1405)":
            "Lignes des achats",
        "TODO: Copier depuis sync_tables.yaml - Echeances achats (YAML L1617)":
            "Echéances achats",
        "TODO: Copier depuis sync_tables.yaml - Entete docs internes DO_Domaine=4 (YAML L1731)":
            "Entête des documents interne",
        "TODO: Copier depuis sync_tables.yaml - Ligne docs internes (YAML L1827)":
            "Ligne des documents internes",
        "TODO: Copier depuis sync_tables.yaml - Mouvement stock (YAML L2023)":
            "Mouvement stock",
        "TODO: Copier depuis sync_tables.yaml (YAML L2224) - AJOUTER CAST(EC_No AS NVARCHAR(250)) AS [id] dans le SELECT":
            "Les écritures comptables",
    }

    replaced = 0
    not_found = []

    for todo_text, yaml_name in todo_mapping.items():
        if yaml_name in yaml_queries:
            escaped_query = escape_for_tsql(yaml_queries[yaml_name])
            old = f"N'{todo_text}'"
            new = f"N'{escaped_query}'"
            if old in content:
                content = content.replace(old, new)
                replaced += 1
                print(f"  OK: {yaml_name}")
            else:
                print(f"  WARN: TODO text non trouve dans le SQL: {todo_text[:60]}...")
        else:
            not_found.append(yaml_name)
            print(f"  SKIP: {yaml_name} - non trouve dans YAML")

    with open(sql_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return replaced, not_found


def main():
    print("=" * 60)
    print("Fix ETL Config TODOs")
    print("=" * 60)

    # Charger les requetes YAML
    print(f"\nChargement YAML: {YAML_PATH}")
    yaml_queries = load_yaml_queries()
    print(f"  {len(yaml_queries)} tables trouvees dans le YAML")
    print(f"  Noms: {list(yaml_queries.keys())[:5]}...")

    # Corriger le fichier SQL source
    print(f"\nCorrection: {SQL_PATH}")
    if os.path.exists(SQL_PATH):
        replaced, not_found = fix_sql_file(SQL_PATH, yaml_queries)
        print(f"  {replaced} requetes remplacees")
    else:
        print(f"  ERREUR: fichier non trouve")

    # Corriger le fichier dist_client aussi
    print(f"\nCorrection dist: {DIST_SQL_PATH}")
    if os.path.exists(DIST_SQL_PATH):
        replaced2, _ = fix_sql_file(DIST_SQL_PATH, yaml_queries)
        print(f"  {replaced2} requetes remplacees")
    else:
        print(f"  SKIP: dist_client non trouve (normal en dev)")

    # Rapport final
    print("\n" + "=" * 60)
    print("RAPPORT")
    print("=" * 60)

    # Compter les TODO restants
    with open(SQL_PATH, 'r', encoding='utf-8') as f:
        remaining = f.read()
    todo_count = remaining.count("N'TODO:")
    non_dispo_count = remaining.count("Non disponible dans sync_tables.yaml")

    print(f"  TODO restants (depuis YAML):     {todo_count}")
    print(f"  TODO non-disponibles (manuels):   {non_dispo_count}")
    print(f"  Tables manuelles a definir:")
    print(f"    - Imputation BLs")
    print(f"    - Encaissements (MP)")
    print(f"    - Decaissement (MP)")
    print(f"    - Historique affectations")
    print(f"    - Detail paie")
    print(f"    - Historique salaire")
    print(f"    - Historique effectifs")
    print(f"    - Historique")


if __name__ == '__main__':
    main()
