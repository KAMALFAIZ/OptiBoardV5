# -*- coding: utf-8 -*-
"""Debug: structure APP_DataSources_Templates et test insertion simple."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Structure de la table
print("=== COLONNES APP_DataSources_Templates ===")
cols = execute_central("""
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME='APP_DataSources_Templates'
    ORDER BY ORDINAL_POSITION
""")
for c in cols:
    print(f"  {c['COLUMN_NAME']:35} {c['DATA_TYPE']:15} nullable={c['IS_NULLABLE']} default={c['COLUMN_DEFAULT']}")

# Voir un exemple d'enregistrement complet
print("\n=== EXEMPLE COMPLET (DS_VTE_CA_CLIENT) ===")
ex = execute_central("SELECT * FROM APP_DataSources_Templates WHERE code='DS_VTE_CA_CLIENT'")
if ex:
    for k, v in ex[0].items():
        val = str(v)[:100] if v is not None else 'NULL'
        print(f"  {k:30} = {val}")

# Test insertion simple
print("\n=== TEST INSERTION ===")
try:
    # Supprimer si existe deja
    execute_central("DELETE FROM APP_DataSources_Templates WHERE code='DS_TEST_TEMP'")

    # Copier depuis DS_VTE_CA_CLIENT
    src = execute_central("SELECT * FROM APP_DataSources_Templates WHERE code='DS_VTE_CA_CLIENT'")[0]
    qt = (src['query_template'] or '').replace("'", "''")

    # Insertion minimale
    execute_central(f"""
        INSERT INTO APP_DataSources_Templates (code, nom, actif)
        VALUES ('DS_TEST_TEMP', 'Test temporaire', 1)
    """)

    check = execute_central("SELECT COUNT(1) AS n FROM APP_DataSources_Templates WHERE code='DS_TEST_TEMP'")
    print(f"  Insertion minimale : {check[0]['n']} enregistrement(s)")

    # Nettoyage
    execute_central("DELETE FROM APP_DataSources_Templates WHERE code='DS_TEST_TEMP'")
    print("  Suppression OK")

except Exception as e:
    print(f"  ERREUR : {e}")

# Verifier si les DS creees tout a l'heure sont la
print("\n=== VERIFICATION DS_COM_CA_PAR_PERIODE ===")
r = execute_central("SELECT COUNT(1) AS n FROM APP_DataSources_Templates WHERE code='DS_COM_CA_PAR_PERIODE'")
print(f"  COUNT = {r[0]['n']}")

# Total des DS
total = execute_central("SELECT COUNT(1) AS n FROM APP_DataSources_Templates")[0]['n']
print(f"\nTotal datasources : {total}")
