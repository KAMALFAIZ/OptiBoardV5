# -*- coding: utf-8 -*-
"""
Patch : injecte la documentation du rapport "Balance Âgée Complète (DSO + Coûts)"
dans APP_GridViews (champs doc_description, doc_fields, doc_formula, doc_advantage).
À lancer une seule fois sur chaque DWH client.
"""
import sys
import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

DS_CODE = "DS_REC_BALANCE_AGEE_COMPLETE"

DOC_DESCRIPTION = (
    "Analyse complète de l'encours client par tranches d'ancienneté à une date donnée.\n"
    "Permet de piloter le recouvrement, mesurer la performance des encaissements (DSO)\n"
    "et quantifier le coût financier du crédit client."
)

DOC_FIELDS = (
    "Societe           : Société commerciale source\n"
    "Client            : Code + intitulé client\n"
    "Tiers Payeur      : Payeur réel si différent du client facturé\n"
    "Representant      : Commercial responsable du client\n"
    "Ville / Region    : Localisation géographique du client\n"
    "Caution           : Encours d'autorisation accordé au client\n"
    "Non Echu          : Créances dont la date d'échéance est après la date de fin\n"
    "0-30 jours        : Retard entre 1 et 30 jours\n"
    "31-60 jours       : Retard entre 31 et 60 jours\n"
    "61-90 jours       : Retard entre 61 et 90 jours\n"
    "91-120 jours      : Retard entre 91 et 120 jours\n"
    "Plus de 120 jours : Retard supérieur à 120 jours\n"
    "Encours Total     : Somme de toutes les créances non réglées\n"
    "Encours Echu      : Part de l'encours dont l'échéance est dépassée\n"
    "Encours Non Echu  : Part de l'encours encore dans les délais\n"
    "Reglements Non Echus   : Règlements reçus non encore imputés à des factures\n"
    "BL Non Factures        : Bons de livraison non encore facturés\n"
    "Impayes                : Factures en litige ou impayées définitives\n"
    "Reglements Non Imputes : Avances client non rattachées à une facture\n"
    "Chiffre Affaires  : CA facturé sur la période sélectionnée\n"
    "DSO Global        : Délai moyen de paiement global (en jours)\n"
    "DSO Retard        : Part du DSO attribuable aux retards\n"
    "DSO Contractuel   : Part du DSO dans les délais contractuels\n"
    "Cout DSO CA       : Coût financier du DSO sur le CA (taux 8%/an)\n"
    "Cout DSO Encours  : Coût financier du DSO sur l'encours (taux 8%/an)\n"
    "Factures Retour   : Montant des factures de retour marchandise\n"
    "Taux Retour       : % retours / CA période\n"
    "Avoirs Financiers : Montant des avoirs accordés aux clients\n"
    "Taux Avoirs       : % avoirs / CA période\n"
    "Nb Echeances      : Nombre total d'échéances par client\n"
    "Nb Echeances Echues : Nombre d'échéances en retard avec solde > 0"
)

DOC_FORMULA = (
    "DSO Global      = Encours Total × Nb jours période / CA période\n"
    "DSO Retard      = Encours Échu × Nb jours période / CA période\n"
    "DSO Contractuel = Encours Non Échu × Nb jours période / CA période\n"
    "Coût DSO        = Montant × 8% × (Nb jours / 365)\n"
    "Tranches        = DATEDIFF(day, Date Échéance, @dateFin) → 6 intervalles\n"
    "Source          : Échéances_Ventes jointure règlements au @dateFin\n"
    "                  (état exact de la balance à la date de clôture choisie)"
)

DOC_ADVANTAGE = (
    "Vue consolidée par client en une seule ligne : balance âgée 6 tranches + DSO + coût financier.\n"
    "Identifie en un coup d'œil les clients à risque, le coût du crédit accordé et les anomalies\n"
    "(BL non facturés, règlements non imputés).\n"
    "Indispensable pour le responsable recouvrement et la direction financière."
)


def run(conn_str=CONN_STR):
    print(f"Connexion à {conn_str.split(';')[1]}...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Vérifier que la grille existe
    cursor.execute("SELECT id, nom FROM APP_GridViews WHERE data_source_code = ?", DS_CODE)
    row = cursor.fetchone()
    if not row:
        print(f"ERREUR : aucune GridView avec data_source_code = '{DS_CODE}' trouvée.")
        conn.close()
        sys.exit(1)

    gv_id, nom = row
    print(f"GridView trouvée : [{gv_id}] {nom}")

    # S'assurer que les colonnes doc_* existent (migration sécurisée)
    for col in ("doc_description", "doc_fields", "doc_formula", "doc_advantage"):
        cursor.execute(f"""
            IF NOT EXISTS (
                SELECT 1 FROM sys.columns
                WHERE object_id = OBJECT_ID('APP_GridViews') AND name = '{col}'
            )
            ALTER TABLE APP_GridViews ADD {col} NVARCHAR(MAX)
        """)

    # Mettre à jour la documentation
    cursor.execute("""
        UPDATE APP_GridViews
        SET doc_description = ?,
            doc_fields      = ?,
            doc_formula     = ?,
            doc_advantage   = ?,
            updated_at      = GETDATE()
        WHERE data_source_code = ?
    """, DOC_DESCRIPTION, DOC_FIELDS, DOC_FORMULA, DOC_ADVANTAGE, DS_CODE)

    conn.commit()
    print(f"OK  : documentation injectée sur GridView [{gv_id}] \"{nom}\"")
    conn.close()


if __name__ == "__main__":
    # Optionnel : passer une conn string en argument
    conn_str = sys.argv[1] if len(sys.argv) > 1 else CONN_STR
    run(conn_str)
