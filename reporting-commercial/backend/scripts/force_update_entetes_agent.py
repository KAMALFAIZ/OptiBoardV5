"""
Force la mise à jour de la requête 'Entête_des_ventes' dans APP_ETL_Agent_Tables
de toutes les bases DWH clients — même si is_customized = 1.

Usage: python scripts/force_update_entetes_agent.py
"""
import sys, pyodbc
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CENTRAL_CONN = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes"

NEW_QUERY = """SELECT
    F_DOCENTETE.cbMarq [N° interne],
    case
        when F_DOCENTETE.DO_Type between 0 and 6 then 'Oui'
        else 'Non'
    end as Encours,
    isnull(
        case F_DOCENTETE.DO_Type
            when 0 then 'Devis'
            when 1 then 'Bon de commande'
            when 2 then 'Préparation de livraison'
            when 3 then 'Bon de livraison'
            when 4 then 'Bon de retour'
            when 5 then 'Bon avoir financier'
            when 6 then case DO_Provenance
                when 0 then 'Facture'
                when 1 then 'Facture de retour'
                when 2 then 'Facture avoir'
                when 3 then 'Facture caisse décentralisée'
                when 4 then 'Facture d''accompte'
            end
            when 7 then case DO_Provenance
                when 0 then 'Facture comptabilisée'
                when 1 then 'Facture de retour comptabilisée'
                when 2 then 'Facture avoir comptabilisée'
                when 3 then 'Facture caisse décentralisée comptabilisée'
                when 4 then 'Facture d''accompte comptabilisée'
            end
            when 8 then 'Archive'
            else 'ERREUR sur F_DOCENTETE.DO_Type - Contactez votre revendeur.'
        end,
        'ERREUR sur F_DOCENTETE.DO_Type - Contactez votre revendeur.'
    ) as [Type Document],
    (select S_Intitule from dbo.P_SOUCHEVENTE where cbIndice = DO_Souche + 1) Souche,
    case
        when DO_Domaine = 1 then case
            when F_DOCENTETE.DO_Type = 10 then case DO_Statut
                when 0 then 'Saisi'
                when 1 then 'Confermé'
                when 2 then 'Accepté'
            end
            else case
                when F_DOCENTETE.DO_Type = 11 and DO_Statut = 2 then 'Accepté'
                when F_DOCENTETE.DO_Type = 12 and DO_Statut = 2 then 'Envoyé'
                when F_DOCENTETE.DO_Type = 13 and DO_Statut = 2 then 'Réceptionné'
                when F_DOCENTETE.DO_Type = 14 and DO_Statut = 2 then 'Facturé'
                when F_DOCENTETE.DO_Type = 15 and DO_Statut = 2 then 'Facturé'
                when F_DOCENTETE.DO_Type = 16 and DO_Statut = 2 then 'A comptabiliser'
                when F_DOCENTETE.DO_Type = 17 and DO_Statut = 2 then 'Comptabilisé'
                when F_DOCENTETE.DO_Type = 18 and DO_Statut = 2 then 'Archivé'
                when DO_Statut = 0 then 'Saisie'
                when DO_Statut = 1 then 'Confirmé'
                else 'Contactez votre revendeur.'
            end
        end
        else case
            when F_DOCENTETE.DO_Type = 0 and F_DOCENTETE.DO_Statut = 2 then 'Accepté'
            when F_DOCENTETE.DO_Type = 1 and F_DOCENTETE.DO_Statut = 2 then 'A préparer'
            when F_DOCENTETE.DO_Type = 2 and F_DOCENTETE.DO_Statut = 2 then 'A livrer'
            when F_DOCENTETE.DO_Type = 3 and F_DOCENTETE.DO_Statut = 2 then 'A facturer'
            when F_DOCENTETE.DO_Type = 4 and F_DOCENTETE.DO_Statut = 2 then 'A facturer'
            when F_DOCENTETE.DO_Type = 5 and F_DOCENTETE.DO_Statut = 2 then 'A facturer'
            when F_DOCENTETE.DO_Type = 6 and F_DOCENTETE.DO_Statut = 2 then 'A comptabiliser'
            when F_DOCENTETE.DO_Type = 7 and F_DOCENTETE.DO_Statut = 2 then 'Comptabilisé'
            when F_DOCENTETE.DO_Type = 8 and F_DOCENTETE.DO_Statut = 2 then 'Archivé'
            when F_DOCENTETE.DO_Statut = 0 then 'Saisie'
            when F_DOCENTETE.DO_Statut = 1 then 'Confirmé'
            else 'ERREUR. Contactez votre revendeur.'
        end
    end as Statut,
    F_DOCENTETE.DO_Tiers as [Code client],
    F_COMPTET.CT_Intitule as [Intitulé client],
    F_DOCENTETE.CO_No [Code représentant],
    CO_Nom+' '+CO_Prenom [Nom représentant],
    convert(datetime, F_DOCENTETE.DO_Date, 3) as [Date],
    isnull(F_DOCENTETE.DO_Piece, '') as [N° pièce],
    case
        when F_DOCENTETE.DO_Ventile = 0 then 'Non'
        else 'Oui'
    end as [Document ventilé],
    case
        when F_DOCENTETE.DO_Reliquat = 1 then 'Reliquat'
        when F_DOCENTETE.DO_Reliquat = 0 and F_DOCENTETE.DO_Imprim = 1 then 'Imprimé'
        when F_DOCENTETE.DO_Reliquat = 0 and F_DOCENTETE.DO_Imprim = 0 then ' '
        else 'ERREUR. Contactez votre revendeur.'
    end as Etat,
    F_DOCENTETE.DO_Coord01 as [Entête 1],
    F_DOCENTETE.DO_Coord02 as [Entête 2],
    F_DOCENTETE.DO_Coord03 as [Entête 3],
    F_DOCENTETE.DO_Coord04 as [Entête 4],
    F_DOCENTETE.CT_NumPayeur as [N° Compte Payeur],
    F_COMPTET_1.CT_Intitule as [Intitulé tiers payeur],
    F_DEPOT.DE_Intitule as Dépôt,
    isnull(P_DEVISE.D_Intitule, 'Aucune') as Devise,
    P_EXPEDITION.E_Intitule as Expédition,
    case (F_DOCENTETE.DO_Langue)
        when 0 then 'Aucune'
        when 1 then 'Langue 1'
        when 2 then 'Langue 2'
    end as Langue,
    case F_DOCENTETE.DO_BLFact
        when 1 then 'Oui'
        when 0 then 'Non'
    end as [Fact/BL],
    F_DOCENTETE.DO_NbFacture as [Nb Facture],
    F_DOCENTETE.CG_Num as [Compte Général],
    F_DOCENTETE.CA_Num [Code d'affaire],
    (select top 1 CA_Intitule from F_COMPTEA where F_COMPTEA.CA_Num = F_DOCENTETE.CA_Num) as [Intitulé affaire],
    case F_DOCENTETE.N_CatCompta
        when 1 then (select P_CATCOMPTA.CA_ComptaVen01 from P_CATCOMPTA)
        when 2 then (select P_CATCOMPTA.CA_ComptaVen02 from P_CATCOMPTA)
        when 3 then (select P_CATCOMPTA.CA_ComptaVen03 from P_CATCOMPTA)
        when 4 then (select P_CATCOMPTA.CA_ComptaVen04 from P_CATCOMPTA)
        when 5 then (select P_CATCOMPTA.CA_ComptaVen05 from P_CATCOMPTA)
        when 6 then (select P_CATCOMPTA.CA_ComptaVen06 from P_CATCOMPTA)
        when 7 then (select P_CATCOMPTA.CA_ComptaVen07 from P_CATCOMPTA)
        when 8 then (select P_CATCOMPTA.CA_ComptaVen08 from P_CATCOMPTA)
        when 9 then (select P_CATCOMPTA.CA_ComptaVen09 from P_CATCOMPTA)
        when 10 then (select P_CATCOMPTA.CA_ComptaVen10 from P_CATCOMPTA)
        else ' '
    end as [Catégorie Comptable],
    F_DEPOT.DE_No as [Code dépôt],
    F_DOCENTETE.DO_Ref as Référence,
    F_DOCENTETE.DO_Cours as Cours,
    F_DOCENTETE.DO_TxEscompte as [Taux escompte],
    case
        when DO_Reliquat = 0 then 'Reliquet'
        else 'Non'
    end as [Document de reliquat],
    case
        when DO_Imprim = 0 then 'Oui'
        else 'Non'
    end as [Document imprimé ],
    F_DOCENTETE.DO_DateLivr as [Date livraison souhite],
    F_DOCENTETE.DO_DebutAbo as [Date début de l'abonnement lié],
    F_DOCENTETE.DO_FinAbo as [Date fin de l'abonnement lié],
    F_DOCENTETE.DO_DebutPeriod as [Date début de la périodicité liée],
    F_DOCENTETE.DO_FinPeriod as [Date Fin de la périodicité liée],
    F_DOCENTETE.DO_Cloture as [Document clôturé],
    case DO_TypeFrais
        when 0 then 'Montant Forfaitaire'
        when 1 then 'Quantité'
        when 2 then 'Poids net'
        when 3 then 'Poids brut'
        else 'Erreur. Contactez votre revendeur.'
    end as [Type frais],
    F_DOCENTETE.DO_ValFrais as [Valeur frais],
    case
        when DO_TypeLigneFrais = 0 then 'HT'
        else 'TTC'
    end as [Type HT/TTC frais],
    case
        when DO_Valide = 0 then 'Oui'
        else 'Non'
    end as [Statut validé],
    P_DEVISE.D_Intitule as [Intitulé Devise],
    P_CATTARIF.CT_Intitule as [Catégorie tarifaire ],
    P_CONDLIVR.C_Intitule as [Condition de livraison],
    case F_DOCENTETE.DO_Colisage
        when 0 then P_UNITE.U_Intitule
        else cast(F_DOCENTETE.DO_Colisage as varchar) + ' ' + P_UNITE.U_Intitule
    end as Colisage,
    F_DOCENTETE.DO_TotalHT as [Montant HT],
    F_DOCENTETE.DO_TotalTTC [Montant TTC],
    F_DOCENTETE.DO_NetAPayer [Montant net à payer],
    F_DOCENTETE.DO_MontantRegle [Montant réglé],
    F_LIVRAISON.LI_No as [Code lieu de livraison],
    F_LIVRAISON.LI_Intitule [Lieu de livraison],
    F_DOCENTETE.cbCreation [Date création],
    F_DOCENTETE.cbModification [Date modification],
    CASE
        WHEN F_DOCENTETE.DO_Type < 3 THEN 'Non'
        ELSE 'Oui'
    END AS [Valorise CA]
from F_DEPOT inner join
    F_COMPTET inner join
    F_DOCENTETE on F_COMPTET.cbCT_Num = F_DOCENTETE.cbDO_Tiers on F_DEPOT.DE_No = F_DOCENTETE.DE_No
    left outer join F_COMPTET as F_COMPTET_1 on F_DOCENTETE.CT_NumPayeur = F_COMPTET_1.CT_Num
    left outer join F_COLLABORATEUR as COLLABORATEUR_DOC on F_DOCENTETE.cbCO_No = COLLABORATEUR_DOC.CO_No
    left outer join F_LIVRAISON ON F_DOCENTETE.cbLI_No = F_LIVRAISON.LI_No
    LEFT OUTER JOIN P_CONDLIVR ON F_DOCENTETE.DO_DateLivr = P_CONDLIVR.cbIndice
    LEFT OUTER JOIN P_CATTARIF ON F_DOCENTETE.DO_Tarif = P_CATTARIF.cbIndice
    LEFT OUTER JOIN P_DEVISE ON F_DOCENTETE.DO_Devise = P_DEVISE.cbIndice
    LEFT OUTER JOIN P_EXPEDITION ON F_DOCENTETE.DO_Expedit = P_EXPEDITION.cbIndice
    LEFT OUTER JOIN P_UNITE ON F_DOCENTETE.DO_TypeColis = P_UNITE.cbIndice
WHERE (F_DOCENTETE.DO_Domaine IN ( 0 ))"""

TARGET_TABLE = "Entête_des_ventes"


def get_dwh_databases(central_conn):
    """Récupère la liste des bases DWH depuis APP_ClientDB."""
    cur = central_conn.cursor()
    cur.execute("SELECT DISTINCT db_name FROM APP_ClientDB WHERE db_name IS NOT NULL")
    return [row[0] for row in cur.fetchall()]


def update_agent_tables(db_name):
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=kasoft.selfip.net;"
        f"DATABASE={db_name};UID=sa;PWD=SQL@2019;TrustServerCertificate=yes"
    )
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cur = conn.cursor()

        # Vérifier que la table existe
        cur.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_NAME = 'APP_ETL_Agent_Tables'"
        )
        if cur.fetchone()[0] == 0:
            print(f"  [{db_name}] APP_ETL_Agent_Tables absente — ignoré")
            conn.close()
            return 0

        cur.execute(
            "SELECT id, table_name, is_customized, is_inherited "
            "FROM APP_ETL_Agent_Tables WHERE target_table = ?",
            (TARGET_TABLE,)
        )
        rows = cur.fetchall()
        if not rows:
            print(f"  [{db_name}] Aucune entrée '{TARGET_TABLE}' trouvée")
            conn.close()
            return 0

        updated = 0
        for row in rows:
            rid, tname, is_cust, is_inh = row
            cur.execute(
                """UPDATE APP_ETL_Agent_Tables
                   SET source_query = ?,
                       is_customized = 0,
                       is_inherited = 1,
                       updated_at = GETDATE()
                   WHERE id = ?""",
                (NEW_QUERY, rid)
            )
            print(f"  [{db_name}] id={rid} '{tname}' mis à jour "
                  f"(was customized={is_cust}, inherited={is_inh})")
            updated += 1

        conn.close()
        return updated
    except Exception as e:
        print(f"  [{db_name}] ERREUR : {e}")
        return 0


def main():
    print("Connexion centrale...")
    central = pyodbc.connect(CENTRAL_CONN, autocommit=True)

    print("Récupération des bases DWH...")
    dbs = get_dwh_databases(central)
    central.close()

    if not dbs:
        print("Aucune base DWH trouvée dans APP_ClientDB")
        return

    print(f"  {len(dbs)} base(s) trouvée(s) : {dbs}")
    total = 0
    for db in dbs:
        total += update_agent_tables(db)

    print(f"\nDone — {total} entrée(s) mise(s) à jour")
    print("Rafraîchissez la page dans l'UI pour voir le changement.")


if __name__ == '__main__':
    main()
