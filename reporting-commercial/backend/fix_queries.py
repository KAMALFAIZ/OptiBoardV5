"""Injecte les SQL Sage corriges dans APP_ETL_Tables_Config."""
import pyodbc

conn_str = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;'
    'UID=sa;PWD=SQL@2019;TrustServerCertificate=yes'
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# PK: plain CSV (pas JSON array) pour ParsePrimaryKeys qui fait Trim('[',']')
queries = {

    'Entête_des_ventes': {
        'sq': """SELECT DO_Piece, DO_Date, DO_Type, DO_Ref, DO_Tiers, DO_Period,
DO_Devise, DO_Cours, DE_No, DO_TotalHT, DO_TotalHTNet, DO_TotalTTC, DO_NetAPayer,
DO_MontantRegle, DO_NbFacture, DO_Ventile, DO_Tarif, DO_Statut,
CA_No, DO_Condition, DO_DateLivr, DO_Expedit, DO_Transaction,
cbCreation, cbModification
FROM F_DOCENTETE WHERE DO_Domaine = 0""",
        'pk': 'DO_Piece', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Lignes_des_ventes': {
        'sq': """SELECT DL_No, DO_Piece, DO_Date, DO_Ref, DO_Type, CT_Num,
AR_Ref, DL_Design, DL_Qte, DL_QteBC, DL_QteBL,
DL_PrixUnitaire, DL_PUTTC, DL_Remise01REM_Valeur,
DL_MontantHT, DL_MontantTTC, DL_Taxe1, DE_No,
DL_Ligne, DL_PoidsBrut, DL_PoidsNet,
cbCreation, cbModification
FROM F_DOCLIGNE WHERE DO_Domaine = 0""",
        'pk': 'DL_No', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Entête_des_achats': {
        'sq': """SELECT DO_Piece, DO_Date, DO_Type, DO_Ref, DO_Tiers, DO_Period,
DO_Devise, DO_Cours, DE_No, DO_TotalHT, DO_TotalHTNet, DO_TotalTTC, DO_NetAPayer,
DO_MontantRegle, DO_NbFacture, DO_Ventile, DO_Tarif, DO_Statut,
CA_No, DO_Condition, DO_DateLivr, DO_Transaction,
cbCreation, cbModification
FROM F_DOCENTETE WHERE DO_Domaine = 1""",
        'pk': 'DO_Piece', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Lignes_des_achats': {
        'sq': """SELECT DL_No, DO_Piece, DO_Date, DO_Ref, DO_Type, CT_Num,
AR_Ref, DL_Design, DL_Qte, DL_QteBC, DL_QteBL,
DL_PrixUnitaire, DL_PUTTC, DL_Remise01REM_Valeur,
DL_MontantHT, DL_MontantTTC, DL_Taxe1, DE_No, DL_Ligne,
AF_RefFourniss, cbCreation, cbModification
FROM F_DOCLIGNE WHERE DO_Domaine = 1""",
        'pk': 'DL_No', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Echeances_Achats': {
        'sq': """SELECT ECH_No, ENT_No, CT_Num, ECH_Piece, ECH_RefPiece,
ECH_Montant, ECH_DateEch, ECH_Libelle, ECH_Type, ECH_Sens,
ECH_ModePaie, N_Devise, ECH_MontantDev, ECH_Etape,
ECH_DateCreat, cbModification, cbCreation
FROM F_ECHEANCES WHERE ECH_Sens = 1""",
        'pk': 'ECH_No', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Échéances_Ventes': {
        'sq': """SELECT ECH_No, ENT_No, CT_Num, ECH_Piece, ECH_RefPiece,
ECH_Montant, ECH_DateEch, ECH_Libelle, ECH_Type, ECH_Sens,
ECH_ModePaie, N_Devise, ECH_MontantDev, ECH_Etape,
ECH_DateCreat, cbModification, cbCreation
FROM F_ECHEANCES WHERE ECH_Sens = 0""",
        'pk': 'ECH_No', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Ecritures_Comptables': {
        'sq': """SELECT EC_No, JO_Num, EC_Date, EC_Piece, EC_RefPiece,
CG_Num, CG_NumCont, CT_Num, EC_Intitule, N_Reglement,
EC_Echeance, EC_Sens, EC_Montant, EC_Devise, N_Devise,
EC_Lettre, EC_Lettrage, EC_Cloture, EC_StatusRegle, EC_MontantRegle,
cbCreation, cbModification
FROM F_ECRITUREC""",
        'pk': 'EC_No', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Encaissement_MP': {
        'sq': """SELECT RG_No, CT_NumPayeur, RG_Date, RG_Montant, RG_MontantDev,
N_Reglement, RG_Piece, RG_Reference, RG_Libelle,
N_Devise, RG_Cours, RG_Banque, RG_Type, RG_Impaye,
JO_Num, CG_Num, cbCreation, cbModification
FROM F_CREGLEMENT WHERE RG_Type = 0""",
        'pk': 'RG_No', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Decaissement_MP': {
        'sq': """SELECT RG_No, CT_NumPayeur, RG_Date, RG_Montant, RG_MontantDev,
N_Reglement, RG_Piece, RG_Reference, RG_Libelle,
N_Devise, RG_Cours, RG_Banque, RG_Type,
JO_Num, CG_Num, cbCreation, cbModification
FROM F_CREGLEMENT WHERE RG_Type = 1""",
        'pk': 'RG_No', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Imputation_BL': {
        'sq': """SELECT DR_No, DO_Domaine, DO_Type, DO_Piece, DR_TypeRegl,
DR_Date, DR_Libelle, DR_Pourcent, DR_Montant, DR_MontantDev,
DR_Equil, N_Reglement, DR_Regle, cbCreation, cbModification
FROM F_DOCREGL WHERE DO_Domaine = 0 AND DO_Type = 2""",
        'pk': 'DR_No', 'sync': 'full', 'ts': 'cbModification'
    },

    'Imputation_Factures_Ventes': {
        'sq': """SELECT DR_No, DO_Domaine, DO_Type, DO_Piece, DR_TypeRegl,
DR_Date, DR_Libelle, DR_Pourcent, DR_Montant, DR_MontantDev,
N_Reglement, DR_Regle, cbCreation, cbModification
FROM F_DOCREGL WHERE DO_Domaine = 0 AND DO_Type = 3""",
        'pk': 'DR_No', 'sync': 'full', 'ts': 'cbModification'
    },

    'Imputation_Factures_Achats': {
        'sq': """SELECT DR_No, DO_Domaine, DO_Type, DO_Piece, DR_TypeRegl,
DR_Date, DR_Libelle, DR_Pourcent, DR_Montant, DR_MontantDev,
N_Reglement, DR_Regle, cbCreation, cbModification
FROM F_DOCREGL WHERE DO_Domaine = 1 AND DO_Type = 3""",
        'pk': 'DR_No', 'sync': 'full', 'ts': 'cbModification'
    },

    'Entête_des_documents_internes': {
        'sq': """SELECT DO_Piece, DO_Date, DO_Type, DO_Ref, DO_Tiers, DO_Period,
DO_TotalHT, DO_TotalHTNet, DO_TotalTTC, DO_Statut,
DE_No, DO_Condition, cbCreation, cbModification
FROM F_DOCENTETE WHERE DO_Domaine = 3""",
        'pk': 'DO_Piece', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Ligne_des_documents_interne': {
        'sq': """SELECT DL_No, DO_Piece, DO_Date, DO_Ref, DO_Type,
AR_Ref, DL_Design, DL_Qte, DL_PrixUnitaire,
DL_MontantHT, DL_MontantTTC, DE_No, DL_Ligne,
cbCreation, cbModification
FROM F_DOCLIGNE WHERE DO_Domaine = 3""",
        'pk': 'DL_No', 'sync': 'incremental', 'ts': 'cbModification'
    },

    'Mouvement_stock': {
        'sq': """SELECT AR_Ref, DE_No, AS_QteSto [Qte stock], AS_QteRes [Qte reservee],
AS_QteCom [Qte commandee], AS_QtePrepa [Qte en preparation],
AS_MontSto [Montant stock], AS_QteMini [Qte mini],
AS_QteMaxi [Qte maxi], cbModification
FROM F_ARTSTOCK""",
        'pk': 'AR_Ref,DE_No', 'sync': 'full', 'ts': 'cbModification'
    },
}

updated = 0
for code, info in queries.items():
    cursor.execute(
        '''UPDATE APP_ETL_Tables_Config
           SET source_query=?, primary_key_columns=?, sync_type=?, timestamp_column=?,
               date_modification=GETDATE()
           WHERE code=?''',
        (info['sq'], info['pk'], info['sync'], info['ts'], code)
    )
    if cursor.rowcount > 0:
        updated += 1
        print(f'OK: {code}')
    else:
        print(f'NON TROUVE: {code}')

conn.commit()
conn.close()
print(f'\nTotal: {updated}/15')
