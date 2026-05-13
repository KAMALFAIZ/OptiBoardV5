# -*- coding: utf-8 -*-
"""
Creer les 27 datasources manquantes pour les pivots.
Strategie : chaque DS manquante est creee en copiant la query de la DS existante
la plus proche. Les noms de colonnes seront identiques a la DS source.
"""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

def ds_exists(code):
    r = execute_central(f"SELECT COUNT(1) AS n FROM APP_DataSources_Templates WHERE code='{code}'")
    return r[0]['n'] > 0

def copy_ds(new_code, new_nom, source_code):
    """Copier la query d'une DS existante sous un nouveau code."""
    if ds_exists(new_code):
        print(f"  . {new_code} (existe deja)")
        return False
    src = execute_central(f"SELECT query_template, actif FROM APP_DataSources_Templates WHERE code='{source_code}'")
    if not src:
        print(f"  ! SOURCE INTROUVABLE : {source_code}")
        return False
    qt = src[0]['query_template'] or ''
    qt_sql = qt.replace("'", "''")
    nom_sql = new_nom.replace("'", "''")
    execute_central(f"""
        INSERT INTO APP_DataSources_Templates (code, nom, query_template, actif)
        VALUES ('{new_code}', '{nom_sql}', '{qt_sql}', 1)
    """)
    print(f"  + {new_code} (copie de {source_code})")
    return True

created = 0

print("=== DS_COM_* (Ventes / CA) ===")
# CA par dimensions commerciales
r = copy_ds('DS_COM_CA_PAR_PERIODE',    'CA par Periode',           'DS_CA_PAR_MOIS_DYNAMIQUE')
r = copy_ds('DS_COM_CA_PAR_CLIENT',     'CA par Client',            'DS_CA_AGREGE_CLIENT')
r = copy_ds('DS_COM_CA_PAR_ARTICLE',    'CA par Article',           'DS_CA_AGREGE_ARTICLE')
r = copy_ds('DS_COM_CA_PAR_FAMILLE',    'CA par Famille Article',   'DS_VTE_CA_FAMILLE')
r = copy_ds('DS_COM_CA_PAR_COMMERCIAL', 'CA par Commercial',        'DS_CA_AGREGE_REPRESENTANT')
r = copy_ds('DS_COM_CA_PAR_REGION',     'CA par Region / Ville',    'DS_VTE_CA_REGION')
r = copy_ds('DS_COM_CA_PAR_DEPOT',      'CA par Depot',             'DS_VTE_CA_DEPOT')
r = copy_ds('DS_COM_CA_PAR_AFFAIRE',    'CA par Affaire',           'DS_VTE_CA_AFFAIRE')

# Analyses clients
r = copy_ds('DS_COM_ABC_CLIENTS',       'Analyse ABC Clients',      'DS_SEGMENTATION_ABC')
r = copy_ds('DS_COM_COMPARATIF_CLIENT', 'Comparatif N/N-1 Client',  'DS_VTE_COMPARATIF')
r = copy_ds('DS_COM_MARGE_PAR_LIGNE',   'Marge par Ligne',          'DS_CA_MARGE_DYNAMIQUE')
r = copy_ds('DS_COM_RFM',               'Segmentation RFM',         'DS_VTE_RFM')
r = copy_ds('DS_COM_SAISONNALITE',      'Saisonnalite CA',          'DS_VTE_SAISONNALITE')
r = copy_ds('DS_COM_FIDELITE',          'Fidelite Clients',         'DS_VTE_FIDELITE')
r = copy_ds('DS_COM_PERF_COMMERCIAL',   'Performance Commercial',   'DS_CA_AGREGE_REPRESENTANT')

print("\n=== DS_ACH_* (Achats) ===")
r = copy_ds('DS_ACH_CA_PAR_FOURNISSEUR','Achats par Fournisseur',   'DS_ACHATS_PAR_FOURNISSEUR')
r = copy_ds('DS_ACH_CA_PAR_PERIODE',    'Achats par Periode',       'DS_ACHATS_PAR_MOIS')
r = copy_ds('DS_ACH_CA_PAR_ARTICLE',    'Achats par Article',       'DS_ACHATS_PAR_ARTICLE')
r = copy_ds('DS_ACH_CA_PAR_FAMILLE',    'Achats par Famille',       'DS_ACHATS_PAR_FAMILLE')
r = copy_ds('DS_ACH_ABC_FOURNISSEURS',  'ABC Fournisseurs',         'DS_ACH_TOP20_FOURNISSEURS')
r = copy_ds('DS_ACH_EVOLUTION_PRIX',    'Evolution Prix Achat',     'DS_EVOLUTION_PRIX_ACHATS')

print("\n=== DS_STK_* (Stock) ===")
# DS_STK_EVOLUTION_MENSUEL (sans E final) copie de DS_STK_EVOLUTION_MENSUELLE (avec E)
r = copy_ds('DS_STK_EVOLUTION_MENSUEL', 'Evolution Stock Mensuelle','DS_STK_EVOLUTION_MENSUELLE')

print("\n=== DS_DIR_* (Direction) ===")
r = copy_ds('DS_DIR_RENTABILITE_MENSUEL','Rentabilite Mensuelle',   'DS_CA_PAR_MOIS_DYNAMIQUE')
r = copy_ds('DS_DIR_RENTABILITE_ANNUEL', 'Rentabilite Annuelle',    'DS_COMPARATIF_ANNUEL')
r = copy_ds('DS_DIR_COMPARATIF_3ANS',    'Comparatif 3 ans',        'DS_COMPARATIF_ANNUEL')
r = copy_ds('DS_DIR_EVOLUTION_CA_12M',   'Evolution CA 12 mois',    'DS_VTE_CA_MENSUEL')
r = copy_ds('DS_DIR_SYNTHESE_MENSUELLE', 'Synthese Mensuelle',      'DS_CA_PAR_MOIS_DYNAMIQUE')

# Verification finale
print("\n=== VERIFICATION FINALE ===")
missing_codes = [
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
]

ok_count = 0
for code in missing_codes:
    exists = ds_exists(code)
    status = "OK" if exists else "TOUJOURS MANQUANTE"
    if exists: ok_count += 1
    print(f"  {'[OK]' if exists else '[!!]'} {code}")

print(f"\n{ok_count}/{len(missing_codes)} datasources resolues")
