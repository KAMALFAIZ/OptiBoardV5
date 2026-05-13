# -*- coding: utf-8 -*-
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

codes = [
    'DS_COM_CA_PAR_PERIODE','DS_COM_CA_PAR_CLIENT','DS_COM_CA_PAR_ARTICLE',
    'DS_COM_CA_PAR_FAMILLE','DS_COM_CA_PAR_COMMERCIAL','DS_COM_CA_PAR_REGION',
    'DS_COM_CA_PAR_DEPOT','DS_COM_CA_PAR_AFFAIRE',
    'DS_COM_ABC_CLIENTS','DS_COM_COMPARATIF_CLIENT','DS_COM_MARGE_PAR_LIGNE',
    'DS_COM_RFM','DS_COM_SAISONNALITE','DS_COM_FIDELITE','DS_COM_PERF_COMMERCIAL',
    'DS_ACH_CA_PAR_FOURNISSEUR','DS_ACH_CA_PAR_PERIODE','DS_ACH_CA_PAR_ARTICLE',
    'DS_ACH_CA_PAR_FAMILLE','DS_ACH_ABC_FOURNISSEURS','DS_ACH_EVOLUTION_PRIX',
    'DS_STK_EVOLUTION_MENSUEL',
    'DS_DIR_RENTABILITE_MENSUEL','DS_DIR_RENTABILITE_ANNUEL','DS_DIR_COMPARATIF_3ANS',
    'DS_DIR_EVOLUTION_CA_12M','DS_DIR_SYNTHESE_MENSUELLE',
    'DS_OBJECTIFS_VS_REALISE','DS_REMISE_PAR_COMMERCIAL',
]

codes_in = "','".join(codes)
execute_central(f"UPDATE APP_DataSources_Templates SET type='SQL' WHERE code IN ('{codes_in}')")
r = execute_central(f"SELECT COUNT(1) AS n FROM APP_DataSources_Templates WHERE code IN ('{codes_in}') AND type='SQL'")
print(f"Type=SQL corrige pour {r[0]['n']}/{len(codes)} datasources")

# Verification rapide de quelques DS critiques
print("\nVerification spot check :")
for code in ['DS_COM_CA_PAR_AFFAIRE','DS_COM_PERF_COMMERCIAL','DS_ACH_CA_PAR_FOURNISSEUR','DS_STK_EVOLUTION_MENSUEL']:
    r = execute_central(f"SELECT code, type, LEN(query_template) AS qlen FROM APP_DataSources_Templates WHERE code='{code}'")
    if r:
        print(f"  {r[0]['code']:35} type={r[0]['type']} qlen={r[0]['qlen']}")
    else:
        print(f"  {code} : INTROUVABLE")
