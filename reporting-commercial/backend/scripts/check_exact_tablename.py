# -*- coding: utf-8 -*-
import pyodbc

DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'
conn = pyodbc.connect(DWH_KA, timeout=15)
c = conn.cursor()

# List all tables with their exact names + hex encoding
c.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")
tables = [r[0] for r in c.fetchall()]

print("=== Tables contenant 'ance' (hex) ===")
for t in tables:
    if 'ance' in t.lower() or 'ch' in t.lower()[:5]:
        hex_name = t.encode('utf-8').hex()
        print(f"  Nom: {repr(t)}")
        print(f"  UTF8: {hex_name}")
        print()

# Test directly
print("=== Test SELECT TOP 1 FROM each candidate ===")
candidates = [
    'Echeances_Ventes',
    'Echéances_Ventes',   # Echéances_Ventes with é
    'Echèances_Ventes',   # Echèances_Ventes with è
]
for name in candidates:
    try:
        c.execute(f"SELECT TOP 1 1 FROM [{name}]")
        c.fetchone()
        print(f"  [{name}] -> EXISTS (repr: {repr(name)})")
    except Exception as e:
        print(f"  [{name}] -> MISSING")

conn.close()
