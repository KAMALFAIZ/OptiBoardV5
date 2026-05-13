# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database_unified import get_central_connection

conn = get_central_connection()
cur = conn.cursor()

cur.execute("SELECT code, nom, query_template FROM APP_DataSources_Templates WHERE code = 'DS_TB_CA_NvsN1_MOIS'")
row = cur.fetchone()
if row:
    print("Code:", row[0])
    print("Nom:", row[1])
    print("Query:\n", row[2])
else:
    print("DS_TB_CA_NvsN1_MOIS introuvable")

conn.close()
