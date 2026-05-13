# -*- coding: utf-8 -*-
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central
import re

def get_aliases(code):
    r = execute_central(f"SELECT query_template FROM APP_DataSources_Templates WHERE code='{code}'")
    if not r or not r[0]['query_template']: return []
    q = r[0]['query_template']
    # Extraire les alias : AS [Nom] ou AS Nom
    aliases = re.findall(r'\bAS\s+(?:\[([^\]]+)\]|(\w+))', q, re.IGNORECASE)
    return [a[0] or a[1] for a in aliases]

for code in ['DS_KPI_RESUME', 'DS_CA_AGREGE_ARTICLE', 'DS_CA_AGREGE_CATALOGUE',
             'DS_CA_AGREGE_REPRESENTANT', 'DS_VENTES_PAR_CATALOGUE']:
    aliases = get_aliases(code)
    print(f"\n[{code}]")
    for a in aliases:
        print(f"  -> {a}")
