import sys, os, warnings, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')

from app.database_unified import execute_central, execute_dwh
from datetime import date

DWH = 'KA'
DATE_DEBUT = '2024-01-01'
DATE_FIN = date.today().strftime('%Y-%m-%d')

# DS codes effectivement utilises dans les menus (init_menus.py MENU_STRUCTURE)
MENU_MAP = {
    # Tableau de Bord (4)
    'DS_KPI_RESUME': 'Tableau de Bord',
    'DS_COMPARATIF_ANNUEL': 'Tableau de Bord',
    'DS_TOP10_CLIENTS': 'Tableau de Bord',
    'DS_TOP10_ARTICLES': 'Tableau de Bord',
    # CA (10)
    'DS_VENTES_GLOBAL': 'CA',
    'DS_VENTES_PAR_MOIS': 'CA',
    'DS_VENTES_PAR_CATALOGUE': 'CA',
    'DS_VENTES_PAR_CANAL': 'CA',
    'DS_VENTES_PAR_ZONE': 'CA',
    'DS_VENTES_PAR_COMMERCIAL': 'CA',
    'DS_VENTES_PAR_CLIENT': 'CA',
    'DS_VENTES_PAR_ARTICLE': 'CA',
    'DS_VENTES_PAR_AFFAIRE': 'CA',
    'DS_VENTES_PAR_DEPOT': 'CA',
    # Documents (5)
    'DS_FACTURES': 'Documents',
    'DS_BONS_LIVRAISON': 'Documents',
    'DS_BONS_COMMANDE': 'Documents',
    'DS_DEVIS': 'Documents',
    'DS_AVOIRS': 'Documents',
    # Marges (7)
    'DS_CA_MARGE_DYNAMIQUE': 'Marges',
    'DS_CA_AGREGE_CLIENT': 'Marges',
    'DS_CA_AGREGE_ARTICLE': 'Marges',
    'DS_CA_AGREGE_CATALOGUE': 'Marges',
    'DS_CA_AGREGE_REPRESENTANT': 'Marges',
    'DS_CA_PAR_MOIS_DYNAMIQUE': 'Marges',
    'DS_CA_DETAIL_COMPLET': 'Marges',
    # Clients (10)
    'DS_TOP_CLIENTS': 'Clients',
    'DS_VENTES_CLIENT_MOIS': 'Clients',
    'DS_PANIER_MOYEN_CLIENT': 'Clients',
    'DS_CLIENTS_NOUVEAUX': 'Clients',
    'DS_CLIENTS_PERDUS': 'Clients',
    'DS_SEGMENTATION_ABC': 'Clients',
    'DS_BALANCE_AGEE': 'Clients',
    'DS_REGLEMENTS_PAR_CLIENT': 'Clients',
    'DS_VENTES_DETAIL': 'Clients',
    # Performance (8)
    'DS_VENTES_COMMERCIAL_MOIS': 'Performance',
    'DS_COMMANDES_EN_COURS': 'Performance',
    'DS_TAUX_TRANSFORMATION': 'Performance',
    'DS_ECHEANCES_PAR_COMMERCIAL': 'Performance',
    # Tendances (6)
    'DS_VENTES_ARTICLE_MOIS': 'Tendances',
    'DS_VENTES_CATALOGUE_MOIS': 'Tendances',
    'DS_EVOLUTION_PRIX_ACHATS': 'Tendances',
    'DS_PIVOT_VENTES_CA': 'Tendances',
    # Recouvrement (8)
    'DS_DSO': 'Recouvrement',
    'DS_CREANCES_DOUTEUSES': 'Recouvrement',
    'DS_ECHEANCES_NON_REGLEES': 'Recouvrement',
    'DS_REGLEMENTS_PAR_PERIODE': 'Recouvrement',
    'DS_REGLEMENTS_PAR_MODE': 'Recouvrement',
    'DS_FACTURES_NON_REGLEES': 'Recouvrement',
    # Stock (10)
    'DS_STOCK_ACTUEL': 'Stock',
    'DS_MVT_STOCK_GLOBAL': 'Stock',
    'DS_MVT_ENTREES': 'Stock',
    'DS_MVT_SORTIES': 'Stock',
    'DS_STOCK_PAR_DEPOT': 'Stock',
    'DS_STOCK_ROTATION': 'Stock',
    'DS_STOCK_DORMANT': 'Stock',
    'DS_MVT_PAR_ARTICLE': 'Stock',
    'DS_TOP_ARTICLES_MVT': 'Stock',
    'DS_MVT_DETAIL': 'Stock',
    # Achats (10)
    'DS_ACHATS_GLOBAL': 'Achats',
    'DS_ACHATS_PAR_FOURNISSEUR': 'Achats',
    'DS_ACHATS_PAR_ARTICLE': 'Achats',
    'DS_ACHATS_PAR_FAMILLE': 'Achats',
    'DS_FACTURES_ACHATS': 'Achats',
    'DS_COMMANDES_ACHATS': 'Achats',
    'DS_COMMANDES_ACHATS_EN_COURS': 'Achats',
    'DS_TOP_FOURNISSEURS': 'Achats',
    'DS_ECHEANCES_ACHATS': 'Achats',
    'DS_COMPARAISON_FOURNISSEURS': 'Achats',
    # Logistique (4)
    'DS_PREPARATIONS_LIVRAISON': 'Logistique',
    'DS_BONS_RECEPTION': 'Logistique',
    'DS_BL_NON_FACTURES': 'Logistique',
}


def run_template(ds_code):
    t = execute_central(
        "SELECT query_template FROM APP_DataSources_Templates WHERE code = ?",
        (ds_code,)
    )
    if not t:
        return None, "INTROUVABLE"

    q = t[0]['query_template']
    q = q.replace('@dateDebut', f"'{DATE_DEBUT}'")
    q = q.replace('@dateFin', f"'{DATE_FIN}'")
    q = q.replace('@ValorisationCA', "'HT'")
    q = q.replace('@Valorisation', "'CMUP'")
    # Remplacer les filtres societe et autres params optionnels par 1=1 / NULL
    q = re.sub(r'\(@societe IS NULL OR \S+\.\[societe\] = @societe\)', '1=1', q)
    q = re.sub(r'\(@societe IS NULL OR \[societe\] = @societe\)', '1=1', q)
    q = q.replace('@societe', 'NULL')
    q = re.sub(r'\(@typeDocument IS NULL OR \[[^\]]+\] = @typeDocument\)', '1=1', q)
    q = q.replace('@typeDocument', 'NULL')

    try:
        result = execute_dwh(q, dwh_code=DWH)
        return len(result), None
    except Exception as e:
        return None, str(e)


def main():
    print(f"=== Test DWH {DWH} --- {DATE_DEBUT} a {DATE_FIN} ===\n")

    by_group = {}
    results = {}

    for code, group in MENU_MAP.items():
        nb, err = run_template(code)
        results[code] = (nb, err, group)
        if group not in by_group:
            by_group[group] = {'ok': 0, 'fail': 0, 'errors': []}
        if err:
            by_group[group]['fail'] += 1
            by_group[group]['errors'].append((code, err))
        else:
            by_group[group]['ok'] += 1

    # Afficher resultats par groupe
    total_ok = 0
    total_fail = 0
    for group, stats in by_group.items():
        ok = stats['ok']
        fail = stats['fail']
        total_ok += ok
        total_fail += fail
        status = "OK" if fail == 0 else f"{fail} ERREUR(S)"
        print(f"[{group}] {ok}/{ok+fail} — {status}")
        for code, err in stats['errors']:
            short_err = err[:120].replace('\n', ' ')
            print(f"  ERREUR {code}: {short_err}")

    print(f"\n=== TOTAL: {total_ok}/{total_ok+total_fail} templates OK ===")

    # Lister les echecs detailles
    if total_fail > 0:
        print(f"\n--- Erreurs détaillées ---")
        for code, (nb, err, group) in results.items():
            if err and err != "INTROUVABLE":
                print(f"\n{code} ({group}):")
                print(f"  {err[:300]}")


if __name__ == '__main__':
    main()
