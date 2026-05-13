"""Test Python types returned by DS_FACTURES query on DWH KA."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')

from app.database_unified import execute_central, DWHConnectionManager
from app.services.parameter_resolver import inject_params

# Get DS_FACTURES query template
rows = execute_central("SELECT query_template FROM APP_DataSources_Templates WHERE code = 'DS_FACTURES'")
q = rows[0]['query_template']

# Inject default params
ctx = {'dateDebut': '2024-01-01', 'dateFin': '2026-05-09'}
q = inject_params(q, ctx)
q_top3 = q.replace('SELECT ', 'SELECT TOP 3 ', 1) if 'TOP' not in q.upper() else q

print('Query head:', q_top3[:300])
print()

import decimal as _dec, datetime as _dt

def py_to_col_type(v):
    if v is None: return None
    if isinstance(v, bool): return 'boolean'
    if isinstance(v, (int, float, _dec.Decimal)): return 'number'
    if isinstance(v, (_dt.datetime, _dt.date)): return 'date'
    return 'text'

try:
    results = DWHConnectionManager.execute_dwh_query('KA', q_top3, use_cache=False)
    if results:
        print(f'Got {len(results)} rows, {len(results[0])} columns')
        print('\nTypes from DS_FACTURES first row:')
        for k, v in results[0].items():
            t = py_to_col_type(v)
            print(f'  [{k}]: python={type(v).__name__}  grid_type={t}  val={repr(v)[:40]}')
    else:
        print('EMPTY results')
except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
