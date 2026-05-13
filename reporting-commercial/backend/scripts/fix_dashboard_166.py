# -*- coding: utf-8 -*-
"""
Configurer les widgets du dashboard 166 Vue Commerciale avec les bonnes datasources.
Ce dashboard etait un template vide - on lui assigne les DS appropriees.
"""
import sys, os, warnings, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Verifier les champs de DS_KPI_RESUME
print("=== Champs disponibles DS_KPI_RESUME (preview) ===")
kpi_ds = execute_central("SELECT query_template FROM APP_DataSources_Templates WHERE code='DS_KPI_RESUME'")
if kpi_ds:
    print(kpi_ds[0]['query_template'][:500])

print("\n=== Champs DS_CA_AGREGE_ARTICLE (apercu) ===")
art_ds = execute_central("SELECT query_template FROM APP_DataSources_Templates WHERE code='DS_CA_AGREGE_ARTICLE'")
if art_ds:
    print(art_ds[0]['query_template'][:400])

print("\n=== Champs DS_CA_AGREGE_REPRESENTANT (apercu) ===")
rep_ds = execute_central("SELECT query_template FROM APP_DataSources_Templates WHERE code='DS_CA_AGREGE_REPRESENTANT'")
if rep_ds:
    print(rep_ds[0]['query_template'][:400])
