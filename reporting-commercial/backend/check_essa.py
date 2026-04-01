"""Vérification des tables ETL dans OptiBoard_ESSA"""
import sys
sys.path.insert(0, '.')
from app.database_unified import execute_client, execute_central

print("=== Tables APP_ETL dans OptiBoard_ESSA ===")
try:
    rows = execute_client(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'APP_ETL%' ORDER BY TABLE_NAME",
        dwh_code='ESSA', use_cache=False
    )
    if rows:
        for r in rows:
            print(" -", r['TABLE_NAME'])
    else:
        print("  AUCUNE TABLE APP_ETL trouvée dans OptiBoard_ESSA !")
except Exception as e:
    print(f"ERREUR: {e}")

print()
print("=== Tables APP_ETL dans OptiBoard_SaaS (centrale) ===")
try:
    rows = execute_central(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'APP_ETL%' ORDER BY TABLE_NAME",
        use_cache=False
    )
    for r in rows:
        print(" -", r['TABLE_NAME'])
except Exception as e:
    print(f"ERREUR: {e}")
