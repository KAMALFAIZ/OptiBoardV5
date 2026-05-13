"""
Cree des gridviews dans APP_GridViews pour chaque datasource utilise dans les menus,
puis met a jour APP_Menus.target_id pour pointer sur ces gridviews.
"""
import sys
import os
import re
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

from app.database_unified import execute_central, central_cursor

# Mapping ds_code -> nom convivial du gridview
GV_NOMS = {
    'DS_KPI_RESUME': 'KPIs Globaux',
    'DS_COMPARATIF_ANNUEL': 'Comparatif Annuel',
    'DS_TOP10_CLIENTS': 'Top 10 Clients',
    'DS_TOP10_ARTICLES': 'Top 10 Articles',
    'DS_VENTES_GLOBAL': 'CA Global',
    'DS_VENTES_PAR_MOIS': 'CA par Mois',
    'DS_VENTES_PAR_CATALOGUE': 'CA par Gamme',
    'DS_VENTES_PAR_CANAL': 'CA par Canal',
    'DS_VENTES_PAR_ZONE': 'CA par Zone Geographique',
    'DS_VENTES_PAR_COMMERCIAL': 'CA par Commercial',
    'DS_VENTES_PAR_CLIENT': 'CA par Client',
    'DS_VENTES_PAR_ARTICLE': 'CA par Article',
    'DS_VENTES_PAR_AFFAIRE': 'CA par Affaire',
    'DS_VENTES_PAR_DEPOT': 'CA par Depot',
    'DS_FACTURES': 'Factures de Vente',
    'DS_BONS_LIVRAISON': 'Bons de Livraison',
    'DS_BONS_COMMANDE': 'Bons de Commande',
    'DS_DEVIS': 'Devis',
    'DS_AVOIRS': 'Avoirs',
    'DS_CA_MARGE_DYNAMIQUE': 'Marge Globale Dynamique',
    'DS_CA_AGREGE_CLIENT': 'Marge par Client',
    'DS_CA_AGREGE_ARTICLE': 'Marge par Article',
    'DS_CA_AGREGE_CATALOGUE': 'Marge par Catalogue',
    'DS_CA_AGREGE_REPRESENTANT': 'Marge par Commercial',
    'DS_CA_PAR_MOIS_DYNAMIQUE': 'Evolution Mensuelle CA/Marge',
    'DS_CA_DETAIL_COMPLET': 'Detail CA et Marges',
    'DS_TOP_CLIENTS': 'Top Clients CA',
    'DS_VENTES_CLIENT_MOIS': 'CA par Client et Mois',
    'DS_PANIER_MOYEN_CLIENT': 'Panier Moyen Client',
    'DS_CLIENTS_NOUVEAUX': 'Clients Nouveaux',
    'DS_CLIENTS_PERDUS': 'Clients Perdus',
    'DS_SEGMENTATION_ABC': 'Segmentation ABC Clients',
    'DS_BALANCE_AGEE': 'Balance Agee',
    'DS_REGLEMENTS_PAR_CLIENT': 'Reglements par Client',
    'DS_VENTES_DETAIL': 'Detail Ventes Complet',
    'DS_VENTES_COMMERCIAL_MOIS': 'CA Commercial par Mois',
    'DS_COMMANDES_EN_COURS': 'Commandes en Cours',
    'DS_TAUX_TRANSFORMATION': 'Taux de Transformation Devis',
    'DS_ECHEANCES_PAR_COMMERCIAL': 'Echeances par Commercial',
    'DS_VENTES_ARTICLE_MOIS': 'CA par Article et Mois',
    'DS_VENTES_CATALOGUE_MOIS': 'CA par Catalogue et Mois',
    'DS_EVOLUTION_PRIX_ACHATS': 'Evolution Prix Achats',
    'DS_PIVOT_VENTES_CA': 'Pivot Ventes CA',
    'DS_DSO': 'DSO par Client',
    'DS_CREANCES_DOUTEUSES': 'Creances Douteuses',
    'DS_ECHEANCES_NON_REGLEES': 'Echeances Non Reglees',
    'DS_REGLEMENTS_PAR_PERIODE': 'Reglements par Periode',
    'DS_REGLEMENTS_PAR_MODE': 'Reglements par Mode',
    'DS_FACTURES_NON_REGLEES': 'Factures Non Reglees',
    'DS_STOCK_ACTUEL': 'Stock Actuel',
    'DS_MVT_STOCK_GLOBAL': 'Mouvements Globaux Stock',
    'DS_MVT_ENTREES': 'Entrees Stock',
    'DS_MVT_SORTIES': 'Sorties Stock',
    'DS_STOCK_PAR_DEPOT': 'Stock par Depot',
    'DS_STOCK_ROTATION': 'Rotation des Stocks',
    'DS_STOCK_DORMANT': 'Stock Dormant',
    'DS_MVT_PAR_ARTICLE': 'Mouvements par Article',
    'DS_TOP_ARTICLES_MVT': 'Top Articles Mou  ementes',
    'DS_MVT_DETAIL': 'Detail des Mouvements',
    'DS_ACHATS_GLOBAL': 'Achats Global',
    'DS_ACHATS_PAR_FOURNISSEUR': 'Achats par Fournisseur',
    'DS_ACHATS_PAR_ARTICLE': 'Achats par Article',
    'DS_ACHATS_PAR_FAMILLE': 'Achats par Famille',
    'DS_FACTURES_ACHATS': 'Factures Achats',
    'DS_COMMANDES_ACHATS': 'Commandes Achats',
    'DS_COMMANDES_ACHATS_EN_COURS': 'Commandes Achats en Cours',
    'DS_TOP_FOURNISSEURS': 'Top Fournisseurs',
    'DS_ECHEANCES_ACHATS': 'Echeances Achats',
    'DS_COMPARAISON_FOURNISSEURS': 'Comparaison Fournisseurs',
    'DS_PREPARATIONS_LIVRAISON': 'Preparations de Livraison',
    'DS_BONS_RECEPTION': 'Bons de Reception',
    'DS_BL_NON_FACTURES': 'BL Non Factures',
}


def slugify(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_')[:30]


def get_or_create_gridview(ds_code, nom):
    """Cree un gridview pour ce datasource si il n'existe pas encore."""
    existing = execute_central(
        "SELECT id FROM APP_GridViews WHERE data_source_code = ? AND is_public = 1",
        (ds_code,)
    )
    if existing:
        return existing[0]['id'], False

    gv_code = f"GV_{slugify(nom)}_{ds_code[-4:].lower()}"

    with central_cursor() as cursor:
        cursor.execute("""
            INSERT INTO APP_GridViews
                (nom, description, data_source_code, code, columns_config,
                 parameters, actif, is_public, page_size, show_totals, is_custom, is_customized)
            VALUES
                (?, ?, ?, ?, ?, ?, 1, 1, 100, 0, 0, 0)
        """, (
            nom,
            nom,
            ds_code,
            gv_code,
            '[]',
            '[]',
        ))
        cursor.execute("SELECT @@IDENTITY AS id")
        row = cursor.fetchone()
        new_id = int(row[0])

    return new_id, True


def update_menu_target(menu_code, new_target_id):
    """Met a jour target_id du menu."""
    with central_cursor() as cursor:
        cursor.execute(
            "UPDATE APP_Menus SET target_id = ? WHERE code = ?",
            (new_target_id, menu_code)
        )


def main():
    print("=== Creation gridviews pour les menus (datasource -> gridview) ===\n")

    # Reconstruire le mapping menu_code -> ds_code depuis init_menus.py
    from init_menus import MENU_STRUCTURE

    menu_ds_pairs = []
    for section in MENU_STRUCTURE:
        for child in section.get('children', []):
            if child.get('type') == 'datasource':
                menu_ds_pairs.append((child['code'], child['ds_code']))

    created = 0
    updated = 0
    skipped = 0

    for menu_code, ds_code in menu_ds_pairs:
        nom = GV_NOMS.get(ds_code, ds_code.replace('DS_', '').replace('_', ' ').title())
        gv_id, was_created = get_or_create_gridview(ds_code, nom)

        if was_created:
            created += 1
            print(f"  [CREATE] GV {gv_id:4} <- {ds_code}")
        else:
            skipped += 1

        # Verifier le target_id actuel du menu
        menu_row = execute_central(
            "SELECT target_id FROM APP_Menus WHERE code = ?",
            (menu_code,)
        )
        if menu_row:
            current_target = menu_row[0]['target_id']
            if current_target != gv_id:
                update_menu_target(menu_code, gv_id)
                updated += 1
                print(f"  [UPDATE] menu '{menu_code}': target_id {current_target} -> {gv_id}")

    print(f"\nGridviews crees: {created}")
    print(f"Gridviews existants: {skipped}")
    print(f"Menus mis a jour: {updated}")

    # Verification finale
    broken = execute_central("""
        SELECT m.code, m.nom, m.target_id
        FROM APP_Menus m
        LEFT JOIN APP_GridViews g ON g.id = m.target_id
        WHERE m.parent_id IS NOT NULL AND m.type = 'gridview'
          AND g.id IS NULL
    """)
    if broken:
        print(f"\nWARN: {len(broken)} menus toujours avec target_id invalide:")
        for b in broken:
            print(f"  {b['code']}: target_id={b['target_id']}")
    else:
        print("\nTous les menus ont un target_id valide.")


if __name__ == '__main__':
    main()
