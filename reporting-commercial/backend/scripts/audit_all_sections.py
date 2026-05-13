# -*- coding: utf-8 -*-
"""Audit complet de toutes les sections - ce qui existe, ce qui manque."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

sections = execute_central(
    "SELECT id, nom, ordre FROM APP_Menus WHERE parent_id IS NULL ORDER BY ordre"
)

print("="*75)
print("AUDIT COMPLET DES SECTIONS")
print("="*75)

for sec in sections:
    sid = sec['id']
    snom = sec['nom']
    items = execute_central(
        f"SELECT id, nom, type, target_id, ordre FROM APP_Menus WHERE parent_id={sid} ORDER BY ordre"
    )
    print(f"\n[{sid}] {snom} ({len(items)} items)")
    for r in items:
        t = r['type']
        icon = {'gridview':'GV','pivot':'PV','dashboard':'DB','folder':'FL'}.get(t,'??')
        print(f"  {r['ordre']:2}. [{icon}] {r['nom']} (target={r['target_id']})")
    if not items:
        print("  (vide)")
