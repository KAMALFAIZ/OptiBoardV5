# -*- coding: utf-8 -*-
"""
Met a jour total_columns et show_totals pour tous les GridViews existants.
Chaque DS_CODE est mappe aux colonnes numeriques qui ont du sens en total (SUM).
Les taux/pourcentages ne sont PAS totalises (somme de % = absurde).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import execute_query, get_db_cursor

# Mapping: data_source_code -> liste de colonnes a totaliser
TOTAL_COLUMNS_MAP = {
    # ==================== VENTES ====================
    "DS_VENTES_GLOBAL": ["CA HT", "CA TTC", "Marge", "Nb Clients", "Nb Documents", "Qte Totale", "Nb Lignes"],
    "DS_VENTES_PAR_MOIS": ["CA HT", "CA TTC", "Cout Revient", "Marge", "Nb Clients", "Nb Documents", "Nb Articles", "Qte Totale"],
    "DS_VENTES_PAR_CLIENT": ["CA HT", "CA TTC", "Marge", "Nb Factures", "Qte Totale"],
    "DS_VENTES_PAR_ARTICLE": ["Qte Vendue", "CA HT", "Marge", "Nb Clients"],
    "DS_VENTES_PAR_CATALOGUE": ["Nb Articles", "Qte Vendue", "CA HT", "Marge", "Nb Clients"],
    "DS_VENTES_PAR_DEPOT": ["CA HT", "Marge", "Qte Vendue", "Nb Articles", "Nb Clients", "Nb Documents"],
    "DS_VENTES_PAR_TYPE_DOC": ["Nb Documents", "Nb Lignes", "Qte Totale", "Montant HT", "Montant TTC", "Nb Clients", "Nb Articles"],
    "DS_FACTURES": ["Qte", "Montant HT", "Montant TTC", "Marge"],
    "DS_BONS_LIVRAISON": ["Qte BL", "Qte BC", "Montant HT"],
    "DS_BONS_COMMANDE": ["Qte Commandee", "Qte Livree", "Reste A Livrer", "Montant HT"],
    "DS_DEVIS": ["Qte", "Montant HT", "Montant TTC"],
    "DS_AVOIRS": ["Qte", "Montant HT", "Montant TTC"],
    "DS_PREPARATIONS_LIVRAISON": ["Qte PL", "Qte BC", "Montant HT"],
    "DS_VENTES_DETAIL": ["Qte", "Montant HT", "Montant TTC", "Marge"],
    "DS_VENTES_PAR_AFFAIRE": ["CA HT", "Marge", "Nb Documents"],
    "DS_COMMANDES_EN_COURS": ["Qte Commandee", "Qte Livree", "Reste A Livrer", "Montant Reste"],
    "DS_TOP_ARTICLES": ["Qte Vendue", "CA HT", "Marge", "Nb Clients", "Nb Ventes"],
    "DS_TOP_CLIENTS": ["CA HT", "Marge", "Nb Factures", "Nb Articles"],
    "DS_VENTES_PAR_COMMERCIAL": ["Nb Clients", "Nb Factures", "CA HT", "Marge"],
    "DS_VENTES_PAR_ZONE": ["Nb Clients", "CA HT", "Marge"],

    # ==================== CA DETAIL / MARGE DYNAMIQUE ====================
    "DS_CA_DETAIL_COMPLET": ["Quantité", "Montant HT Net", "Montant TTC Net", "Marge PR", "Marge CMUP", "Marge DPA-Vente", "Coût PR", "Coût CMUP"],
    "DS_CA_MARGE_DYNAMIQUE": ["Quantité", "Montant HT Net", "Montant TTC Net", "Marge", "Coût marchandise"],
    "DS_CA_AGREGE_CLIENT": ["Nb Documents", "Qte Totale", "CA", "Marge", "Coût marchandise"],
    "DS_CA_AGREGE_ARTICLE": ["Nb Clients", "Nb Documents", "Qte Vendue", "CA", "Marge"],
    "DS_CA_AGREGE_CATALOGUE": ["Nb Articles", "Nb Clients", "Qte Vendue", "CA", "Marge"],
    "DS_CA_AGREGE_REPRESENTANT": ["Nb Clients", "Nb Documents", "Qte Vendue", "CA", "Marge"],
    "DS_CA_PAR_MOIS_DYNAMIQUE": ["Qte Totale", "CA", "Marge", "Coût marchandise"],

    # ==================== VENTES PAR MOIS (TCD) ====================
    "DS_VENTES_CLIENT_MOIS": ["CA HT", "CA TTC", "Marge", "Nb Factures", "Qte Totale"],
    "DS_VENTES_ARTICLE_MOIS": ["Qte Vendue", "CA HT", "Marge"],
    "DS_VENTES_COMMERCIAL_MOIS": ["Nb Clients", "CA HT", "Marge"],
    "DS_VENTES_CATALOGUE_MOIS": ["Nb Articles", "Qte Vendue", "CA HT", "Marge"],
    "DS_VENTES_GAMME_MOIS": ["Nb Articles", "Qte Vendue", "CA HT", "Marge"],
    "DS_VENTES_FAMILLE_MOIS": ["Nb Articles", "Qte Vendue", "CA HT", "Marge"],

    # ==================== ANALYSES ====================
    "DS_VENTES_PAR_CANAL": ["Nb Clients", "CA HT", "Marge"],
    "DS_PANIER_MOYEN_CLIENT": ["Nb Factures", "CA HT", "Marge"],
    "DS_CLIENTS_NOUVEAUX": ["CA HT", "Nb Factures"],
    "DS_CLIENTS_PERDUS": ["CA Derniere Annee"],
    "DS_SEGMENTATION_ABC": ["CA HT", "Marge"],
    "DS_CONTRIBUTION_MARGINALE": ["CA HT", "Marge"],
    "DS_MARGE_NEGATIVE": ["CA HT", "Marge", "Qte Vendue"],
    "DS_CONCENTRATION_RISQUE": ["CA HT", "Marge"],
    "DS_EVOLUTION_ABC": ["CA Annee N", "CA Annee N-1"],
    "DS_TAUX_TRANSFORMATION": ["Nb Devis", "Montant Devis", "Nb BC", "Montant BC"],
    "DS_PORTEFEUILLE_COMMERCIAL": ["Nb Clients", "CA HT", "Marge"],
    "DS_BL_NON_FACTURES": ["Montant HT"],

    # ==================== ACHATS ====================
    "DS_ACHATS_GLOBAL": ["Achats HT", "Achats TTC", "Nb Fournisseurs", "Nb Documents", "Qte Totale", "Nb Lignes"],
    "DS_ACHATS_PAR_MOIS": ["Achats HT", "Achats TTC", "Nb Fournisseurs", "Nb Documents", "Qte Totale"],
    "DS_ACHATS_PAR_FOURNISSEUR": ["Achats HT", "Achats TTC", "Nb Documents", "Qte Totale", "Nb Articles"],
    "DS_ACHATS_PAR_ARTICLE": ["Qte Achetee", "Achats HT", "Nb Fournisseurs", "Nb Documents"],
    "DS_ACHATS_PAR_FAMILLE": ["Qte Achetee", "Achats HT", "Achats TTC", "Nb Articles", "Nb Fournisseurs"],
    "DS_ACHATS_PAR_TYPE_DOC": ["Nb Documents", "Qte Totale", "Montant HT", "Montant TTC", "Nb Fournisseurs", "Nb Articles"],
    "DS_FACTURES_ACHATS": ["Quantite", "Montant HT", "Montant TTC"],
    "DS_BONS_RECEPTION": ["Quantite", "Montant HT"],
    "DS_COMMANDES_ACHATS": ["Quantite", "Montant HT"],
    "DS_AVOIRS_ACHATS": ["Quantite", "Montant HT", "Montant TTC"],
    "DS_ACHATS_DETAIL": ["Quantité", "Montant HT Net", "Montant TTC Net"],
    "DS_COMMANDES_ACHATS_EN_COURS": ["Qte Commandee", "Qte Recue", "Reste A Recevoir", "Montant Reste"],
    "DS_TOP_FOURNISSEURS": ["Achats HT", "Nb Documents", "Nb Articles"],
    "DS_TOP_ARTICLES_ACHATS": ["Qte Achetee", "Achats HT", "Nb Fournisseurs"],
    "DS_ACHATS_PAR_AFFAIRE": ["Achats HT", "Nb Documents", "Qte Totale"],
    "DS_ACHATS_PAR_ACHETEUR": ["Achats HT", "Nb Documents", "Nb Fournisseurs"],
    "DS_ACHATS_PAR_CATALOGUE": ["Achats HT", "Achats TTC", "Qte Achetee", "Nb Articles"],
    "DS_COMPARAISON_FOURNISSEURS": ["Achats HT", "Qte Achetee"],
    "DS_ACHATS_VS_VENTES": ["Qte Achetee", "Achats HT", "Qte Vendue", "Ventes HT", "Marge"],
    "DS_ECHEANCES_ACHATS": ["Montant échéance", "Montant réglé", "Reste à Régler"],

    # ==================== STOCK ====================
    "DS_MVT_STOCK_GLOBAL": ["Nb Mouvements", "Qte Totale", "Valeur Totale"],
    "DS_MVT_PAR_DEPOT": ["Nb Mouvements", "Qte Totale", "Valeur Totale"],
    "DS_MVT_PAR_FAMILLE": ["Nb Mouvements", "Qte Totale", "Valeur Totale"],
    "DS_MVT_PAR_ARTICLE": ["Nb Mouvements", "Qte Totale", "Valeur Totale"],
    "DS_MVT_PAR_DOMAINE": ["Nb Mouvements", "Qte Totale", "Valeur Totale"],
    "DS_MVT_PAR_TYPE": ["Nb Mouvements", "Qte Totale", "Valeur Totale"],
    "DS_MVT_ENTREES": ["Quantité", "Montant"],
    "DS_MVT_SORTIES": ["Quantité", "Montant"],
    "DS_STOCK_ACTUEL": ["Quantité en stock", "Valeur Stock"],
    "DS_STOCK_PAR_DEPOT": ["Nb Articles", "Qte Totale", "Valeur Totale"],
    "DS_MVT_PAR_MOIS": ["Nb Mouvements", "Qte Totale", "Valeur Totale"],
    "DS_MVT_VENTES": ["Quantité", "Montant"],
    "DS_MVT_ACHATS": ["Quantité", "Montant"],
    "DS_MVT_INTERNES": ["Quantité", "Montant"],
    "DS_MVT_DETAIL": ["Quantité", "Montant"],
    "DS_TOP_ARTICLES_MVT": ["Nb Mouvements", "Qte Totale", "Valeur Totale"],
    "DS_MVT_CATALOGUE": ["Nb Mouvements", "Qte Totale", "Valeur Totale"],
    "DS_STOCK_VALORISATION": ["Quantité en stock", "Valeur CMUP", "Valeur DPA", "Valeur Standard"],
    "DS_STOCK_COUVERTURE": ["Quantité en stock", "Qte Vendue Mois", "Valeur Stock"],
    "DS_MVT_INTER_DEPOTS": ["Quantité"],
    "DS_ARTICLES_COMPOSES": ["Quantité"],

    # ==================== RECOUVREMENT ====================
    "DS_BALANCE_AGEE": ["Total Échéances", "Total Réglé", "Reste à Régler", "A Echoir", "0-30j", "31-60j", "61-90j", "91-120j", "+120j"],
    "DS_ECHEANCES_NON_REGLEES": ["Montant échéance", "Montant réglé", "Reste à Régler"],
    "DS_ECHEANCES_PAR_CLIENT": ["Nb Échéances", "Total Échéances", "Total Réglé", "Reste à Régler", "A Echoir", "0-30j", "31-60j", "61-90j", "91-120j", "+120j"],
    "DS_ECHEANCES_PAR_COMMERCIAL": ["Nb Clients", "Nb Échéances", "Encours Total", "A Echoir", "0-30j", "31-60j", "61-90j", "91-120j", "+120j"],
    "DS_ECHEANCES_PAR_MODE": ["Nb Échéances", "Total Échéances", "Reste à Régler"],
    "DS_ECHEANCES_A_ECHOIR": ["Montant à Régler"],
    "DS_REGLEMENTS_PAR_PERIODE": ["Nb Règlements", "Montant Total"],
    "DS_REGLEMENTS_PAR_CLIENT": ["Nb Règlements", "Total Réglé"],
    "DS_REGLEMENTS_PAR_MODE": ["Nb Règlements", "Total Réglé"],
    "DS_FACTURES_NON_REGLEES": ["Montant HT", "Montant Réglé", "Reste à Régler"],
    "DS_DSO": ["CA 12 Mois", "Encours Total"],
    "DS_CREANCES_DOUTEUSES": ["Montant Douteux"],

    # ==================== COMPTABILITE ====================
    "DS_ECRITURES_GLOBAL": ["Nb Ecritures", "Total Debit", "Total Credit"],
    "DS_ECRITURES_PAR_JOURNAL": ["Nb Ecritures", "Total Debit", "Total Credit"],
    "DS_ECRITURES_PAR_COMPTE": ["Nb Ecritures", "Total Debit", "Total Credit", "Solde"],
    "DS_ECRITURES_PAR_TIERS": ["Nb Ecritures", "Total Debit", "Total Credit", "Solde"],
    "DS_ECRITURES_PAR_MOIS": ["Nb Ecritures", "Total Debit", "Total Credit"],
    "DS_ECRITURES_DETAIL": ["Débit", "Crédit"],
    "DS_GRAND_LIVRE": ["Débit", "Crédit", "Solde"],
    "DS_BALANCE_GENERALE": ["Débit", "Crédit", "Solde Débiteur", "Solde Créditeur"],

    # ==================== PIVOT V2 (brut) ====================
    "DS_PIVOT_LIGNES_VENTES": ["Quantité", "Montant HT Net", "Montant TTC Net", "Marge"],
    "DS_PIVOT_VENTES_CA": ["Quantité", "Montant HT Net", "Montant TTC Net", "Marge"],

    # ==================== ANCIENS CODES (init_complete_menus) ====================
    "DS_COMPARATIF_ANNUEL": ["CA HT", "CA TTC", "Marge", "Nb Clients", "Nb Documents", "Qte Totale"],
    "DS_COMPORTEMENT_PAIEMENT": ["Nb Echeances", "Montant Total"],
    "DS_DELAIS_ETAPES": ["Nb Documents"],
    "DS_DOCUMENTS_ANOMALIE": ["Montant HT"],
    "DS_EVOLUTION_PRIX_ACHATS": ["Qte Achetee", "Nb Fournisseurs"],
    "DS_HISTORIQUE_PRIX_FOURNISSEUR": ["Qte", "Montant HT"],
    "DS_MARGE_PAR_GAMME": ["CA HT", "Cout Revient", "Marge", "Qte Vendue", "Nb Articles"],
    "DS_MATRICE_CLIENT_ARTICLE": ["Qte Totale", "CA HT", "Nb Commandes"],
    "DS_PIPELINE_COMMERCIAL": ["Nb Documents", "Nb Lignes", "Montant HT", "Montant TTC", "Nb Clients", "Nb Articles", "Qte Totale"],
    "DS_PREVISION_ENCAISSEMENTS": ["Nb Echeances", "Nb Clients", "Montant Total", "Deja Regle", "Reste a Encaisser"],
    "DS_STOCK_DORMANT": ["Stock Qte", "Valeur Stock"],
    "DS_STOCK_PEREMPTION": ["Stock Qte", "Valeur Stock"],
    "DS_STOCK_ROTATION": ["Stock Actuel", "Valeur Stock"],
    "DS_TOP10_ARTICLES": ["Qte"],
    "DS_VENTES_PAR_CATEGORIE_TARIF": ["Nb Clients", "Qte Vendue", "CA HT", "Marge", "Nb Documents"],
    "DS_VENTES_PAR_GAMME": ["Nb Articles", "Qte Vendue", "CA HT", "CA TTC", "Marge", "Nb Clients", "Nb Documents"],
}


def main():
    print("=" * 70)
    print("MISE A JOUR total_columns POUR TOUS LES GRIDVIEWS")
    print("=" * 70)

    with get_db_cursor() as cursor:
        cursor.execute("SELECT id, nom, data_source_code, total_columns FROM APP_GridViews WHERE actif = 1")
        gridviews = cursor.fetchall()

    updated = 0
    skipped = 0

    for gv in gridviews:
        gv_id = gv[0]
        nom = gv[1]
        ds_code = gv[2]
        current = gv[3]

        if not ds_code:
            skipped += 1
            continue

        if ds_code in TOTAL_COLUMNS_MAP:
            new_cols = json.dumps(TOTAL_COLUMNS_MAP[ds_code])
            with get_db_cursor() as cursor:
                cursor.execute(
                    "UPDATE APP_GridViews SET total_columns = ?, show_totals = 1 WHERE id = ?",
                    (new_cols, gv_id)
                )
            print(f"  [OK] id={gv_id} {nom} ({ds_code}) -> {len(TOTAL_COLUMNS_MAP[ds_code])} colonnes")
            updated += 1
        else:
            print(f"  [--] id={gv_id} {nom} ({ds_code}) -> pas de mapping")
            skipped += 1

    print(f"\n{'=' * 70}")
    print(f"TERMINE: {updated} mis a jour, {skipped} ignores")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
