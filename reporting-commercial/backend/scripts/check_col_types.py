"""Check what Python types the DWH returns for DS_FACTURES columns."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')

from app.database_unified import execute_central, execute_dwh
import re

# Get the DS_FACTURES template
rows = execute_central("SELECT query_template FROM APP_DataSources_Templates WHERE code = 'DS_FACTURES'")
q = rows[0]['query_template']

# Replace params
q = q.replace('@dateDebut', "'2024-01-01'")
q = q.replace('@dateFin', "'2026-05-09'")
q = q.replace('@ValorisationCA', "'HT'")
q = q.replace('@Valorisation', "'CMUP'")
q = re.sub(r'\(@societe IS NULL OR \S+\.\[societe\] = @societe\)', '1=1', q)
q = re.sub(r'\(@societe IS NULL OR \[societe\] = @societe\)', '1=1', q)
q = q.replace('@societe', 'NULL')
q = re.sub(r'\(@typeDocument IS NULL OR \[[^\]]+\] = @typeDocument\)', '1=1', q)
q = q.replace('@typeDocument', 'NULL')

# Limit to 5 rows
q = q.replace('SELECT ', 'SELECT TOP 5 ', 1)

result = execute_dwh(q, dwh_code='KA')
if result:
    print("Column types from Python:")
    for k, v in result[0].items():
        print(f"  [{k}]: python_type={type(v).__name__}  sample={repr(v)[:40]}")
