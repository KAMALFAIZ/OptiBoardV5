"""
Script pour initialiser la structure complete des menus
basee sur les categories de DataSources Templates
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import execute_query, get_db_cursor

# =============================================================================
# STRUCTURE DES MENUS
# =============================================================================
# Structure hierarchique des menus a creer
# Chaque menu peut avoir des enfants et des liens vers des datasources

MENU_STRUCTURE = [
    # ==================== VENTES ====================
    {
        "nom": "Ventes",
        "code": "ventes",
        "icon": "ShoppingCart",
        "ordre": 1,
        "children": [
            {
                "nom": "Chiffre d'Affaires",
                "code": "ventes-ca",
                "icon": "BarChart3",
                "ordre": 1,
                "children": [
                    {"nom": "CA Global", "code": "DS_VENTES_GLOBAL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "CA par Mois", "code": "DS_VENTES_PAR_MOIS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "CA par Client", "code": "DS_VENTES_PAR_CLIENT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "CA par Article", "code": "DS_VENTES_PAR_ARTICLE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                    {"nom": "CA par Catalogue", "code": "DS_VENTES_PAR_CATALOGUE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 5},
                    {"nom": "CA par Depot", "code": "DS_VENTES_PAR_DEPOT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 6},
                    {"nom": "CA par Commercial", "code": "DS_VENTES_PAR_COMMERCIAL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 7},
                    {"nom": "CA par Zone Geo", "code": "DS_VENTES_PAR_ZONE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 8},
                    {"nom": "CA par Affaire", "code": "DS_VENTES_PAR_AFFAIRE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 9},
                ]
            },
            {
                "nom": "Documents Ventes",
                "code": "ventes-docs",
                "icon": "FileSpreadsheet",
                "ordre": 2,
                "children": [
                    {"nom": "Factures", "code": "DS_FACTURES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Bons de Livraison", "code": "DS_BONS_LIVRAISON", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Bons de Commande", "code": "DS_BONS_COMMANDE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "Devis", "code": "DS_DEVIS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                    {"nom": "Avoirs", "code": "DS_AVOIRS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 5},
                    {"nom": "Preparations Livraison", "code": "DS_PREPARATIONS_LIVRAISON", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 6},
                    {"nom": "Ventes par Type Doc", "code": "DS_VENTES_PAR_TYPE_DOC", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 7},
                    {"nom": "Ventes Detail Complet", "code": "DS_VENTES_DETAIL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 8},
                ]
            },
            {
                "nom": "Analyses Ventes",
                "code": "ventes-analyses",
                "icon": "BarChart3",
                "ordre": 3,
                "children": [
                    {"nom": "Top Clients", "code": "DS_TOP_CLIENTS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Top Articles", "code": "DS_TOP_ARTICLES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Commandes en Cours", "code": "DS_COMMANDES_EN_COURS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                ]
            },
        ]
    },

    # ==================== ACHATS ====================
    {
        "nom": "Achats",
        "code": "achats",
        "icon": "ShoppingCart",
        "ordre": 2,
        "children": [
            {
                "nom": "Synthese Achats",
                "code": "achats-synthese",
                "icon": "BarChart3",
                "ordre": 1,
                "children": [
                    {"nom": "Achats Global", "code": "DS_ACHATS_GLOBAL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Achats par Mois", "code": "DS_ACHATS_PAR_MOIS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Achats par Fournisseur", "code": "DS_ACHATS_PAR_FOURNISSEUR", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "Achats par Article", "code": "DS_ACHATS_PAR_ARTICLE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                    {"nom": "Achats par Famille", "code": "DS_ACHATS_PAR_FAMILLE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 5},
                    {"nom": "Achats par Catalogue", "code": "DS_ACHATS_PAR_CATALOGUE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 6},
                    {"nom": "Achats par Type Doc", "code": "DS_ACHATS_PAR_TYPE_DOC", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 7},
                    {"nom": "Achats par Affaire", "code": "DS_ACHATS_PAR_AFFAIRE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 8},
                    {"nom": "Achats par Acheteur", "code": "DS_ACHATS_PAR_ACHETEUR", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 9},
                ]
            },
            {
                "nom": "Documents Achats",
                "code": "achats-docs",
                "icon": "FileSpreadsheet",
                "ordre": 2,
                "children": [
                    {"nom": "Factures Achats", "code": "DS_FACTURES_ACHATS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Bons de Reception", "code": "DS_BONS_RECEPTION", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Commandes Achats", "code": "DS_COMMANDES_ACHATS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "Avoirs Achats", "code": "DS_AVOIRS_ACHATS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                    {"nom": "Achats Detail Complet", "code": "DS_ACHATS_DETAIL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 5},
                ]
            },
            {
                "nom": "Analyses Achats",
                "code": "achats-analyses",
                "icon": "BarChart3",
                "ordre": 3,
                "children": [
                    {"nom": "Commandes en Cours", "code": "DS_COMMANDES_ACHATS_EN_COURS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Top Fournisseurs", "code": "DS_TOP_FOURNISSEURS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Top Articles Achetes", "code": "DS_TOP_ARTICLES_ACHATS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "Evolution Prix Achats", "code": "DS_EVOLUTION_PRIX_ACHATS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                    {"nom": "Comparaison Fournisseurs", "code": "DS_COMPARAISON_FOURNISSEURS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 5},
                ]
            },
        ]
    },

    # ==================== STOCKS ====================
    {
        "nom": "Stocks",
        "code": "stocks",
        "icon": "Package",
        "ordre": 3,
        "children": [
            {
                "nom": "Mouvements",
                "code": "stocks-mvt",
                "icon": "BarChart3",
                "ordre": 1,
                "children": [
                    {"nom": "Mouvements Global", "code": "DS_MVT_STOCK_GLOBAL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Mouvements par Mois", "code": "DS_MVT_PAR_MOIS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Mouvements par Depot", "code": "DS_MVT_PAR_DEPOT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "Mouvements par Famille", "code": "DS_MVT_PAR_FAMILLE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                    {"nom": "Mouvements par Article", "code": "DS_MVT_PAR_ARTICLE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 5},
                    {"nom": "Mouvements par Domaine", "code": "DS_MVT_PAR_DOMAINE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 6},
                    {"nom": "Mouvements par Type Doc", "code": "DS_MVT_PAR_TYPE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 7},
                    {"nom": "Mouvements par Catalogue", "code": "DS_MVT_CATALOGUE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 8},
                    {"nom": "Mouvements par Lot/Serie", "code": "DS_MVT_PAR_LOT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 9},
                    {"nom": "Detail Complet Mouvements", "code": "DS_MVT_DETAIL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 10},
                ]
            },
            {
                "nom": "Entrees / Sorties",
                "code": "stocks-es",
                "icon": "FileSpreadsheet",
                "ordre": 2,
                "children": [
                    {"nom": "Entrees Stock", "code": "DS_MVT_ENTREES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Sorties Stock", "code": "DS_MVT_SORTIES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Mouvements Ventes", "code": "DS_MVT_VENTES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "Mouvements Achats", "code": "DS_MVT_ACHATS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                    {"nom": "Mouvements Internes", "code": "DS_MVT_INTERNES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 5},
                ]
            },
            {
                "nom": "Situation Stock",
                "code": "stocks-situation",
                "icon": "BarChart3",
                "ordre": 3,
                "children": [
                    {"nom": "Stock Actuel par Article", "code": "DS_STOCK_ACTUEL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Stock par Depot", "code": "DS_STOCK_PAR_DEPOT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Top Articles Mouvementes", "code": "DS_TOP_ARTICLES_MVT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                ]
            },
            {
                "nom": "Analyses Stock",
                "code": "stocks-analyses",
                "icon": "BarChart3",
                "ordre": 4,
                "children": [
                    {"nom": "Rotation des Stocks", "code": "DS_STOCK_ROTATION", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Stock Dormant", "code": "DS_STOCK_DORMANT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                ]
            },
        ]
    },

    # ==================== COMPTABILITE ====================
    {
        "nom": "Comptabilite",
        "code": "comptabilite",
        "icon": "Wallet",
        "ordre": 4,
        "children": [
            {
                "nom": "Ecritures Comptables",
                "code": "compta-ecritures",
                "icon": "FileSpreadsheet",
                "ordre": 1,
                "children": [
                    {"nom": "Ecritures Global", "code": "DS_ECRITURES_GLOBAL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Ecritures par Journal", "code": "DS_ECRITURES_PAR_JOURNAL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Ecritures par Compte", "code": "DS_ECRITURES_PAR_COMPTE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "Ecritures par Tiers", "code": "DS_ECRITURES_PAR_TIERS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                    {"nom": "Ecritures par Mois", "code": "DS_ECRITURES_PAR_MOIS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 5},
                    {"nom": "Detail Ecritures", "code": "DS_ECRITURES_DETAIL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 6},
                ]
            },
            {
                "nom": "Grand Livre / Balance",
                "code": "compta-gl",
                "icon": "FileSpreadsheet",
                "ordre": 2,
                "children": [
                    {"nom": "Grand Livre", "code": "DS_GRAND_LIVRE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Balance Generale", "code": "DS_BALANCE_GENERALE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                ]
            },
            {
                "nom": "Bilan",
                "code": "compta-bilan",
                "icon": "BarChart3",
                "ordre": 3,
                "children": [
                    {"nom": "Bilan Synthetique", "code": "DS_BILAN_SYNTHETIQUE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Bilan Actif", "code": "DS_BILAN_ACTIF", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Actif Immobilise", "code": "DS_ACTIF_IMMOBILISE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "Actif Circulant", "code": "DS_ACTIF_CIRCULANT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                    {"nom": "Bilan Passif", "code": "DS_BILAN_PASSIF", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 5},
                    {"nom": "Capitaux Propres", "code": "DS_CAPITAUX_PROPRES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 6},
                    {"nom": "Dettes", "code": "DS_DETTES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 7},
                ]
            },
            {
                "nom": "CPC",
                "code": "compta-cpc",
                "icon": "BarChart3",
                "ordre": 4,
                "children": [
                    {"nom": "CPC Global", "code": "DS_CPC_GLOBAL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "CPC Produits", "code": "DS_CPC_PRODUITS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "CPC Charges", "code": "DS_CPC_CHARGES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "CPC par Mois", "code": "DS_CPC_PAR_MOIS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                ]
            },
            {
                "nom": "Tresorerie",
                "code": "compta-tresorerie",
                "icon": "Wallet",
                "ordre": 5,
                "children": [
                    {"nom": "Tresorerie", "code": "DS_TRESORERIE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Tresorerie par Mois", "code": "DS_TRESORERIE_PAR_MOIS", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                ]
            },
            {
                "nom": "Analytique",
                "code": "compta-analytique",
                "icon": "BarChart3",
                "ordre": 6,
                "children": [
                    {"nom": "Analytique Global", "code": "DS_ANALYTIQUE_GLOBAL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Analytique par Plan", "code": "DS_ANALYTIQUE_PAR_PLAN", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Detail Analytique", "code": "DS_ANALYTIQUE_DETAIL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                ]
            },
            {
                "nom": "Echeances / Lettrage",
                "code": "compta-echeances",
                "icon": "FileSpreadsheet",
                "ordre": 7,
                "children": [
                    {"nom": "Echeances Comptables", "code": "DS_ECHEANCES_COMPTABLES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Analyse Lettrage", "code": "DS_LETTRAGE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                ]
            },
        ]
    },

    # ==================== RECOUVREMENT ====================
    {
        "nom": "Recouvrement",
        "code": "recouvrement",
        "icon": "Wallet",
        "ordre": 5,
        "children": [
            {
                "nom": "Encours Clients",
                "code": "recouv-encours",
                "icon": "BarChart3",
                "ordre": 1,
                "children": [
                    {"nom": "Balance Agee", "code": "DS_BALANCE_AGEE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "DSO par Client", "code": "DS_DSO", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Creances Douteuses", "code": "DS_CREANCES_DOUTEUSES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "KPIs Recouvrement", "code": "DS_KPI_RECOUVREMENT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                ]
            },
            {
                "nom": "Echeances Ventes",
                "code": "recouv-echeances",
                "icon": "FileSpreadsheet",
                "ordre": 2,
                "children": [
                    {"nom": "Echeances Non Reglees", "code": "DS_ECHEANCES_NON_REGLEES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Echeances par Client", "code": "DS_ECHEANCES_PAR_CLIENT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Echeances par Commercial", "code": "DS_ECHEANCES_PAR_COMMERCIAL", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "Echeances par Mode Reglement", "code": "DS_ECHEANCES_PAR_MODE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                    {"nom": "Echeances a Echoir", "code": "DS_ECHEANCES_A_ECHOIR", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 5},
                ]
            },
            {
                "nom": "Reglements",
                "code": "recouv-reglements",
                "icon": "FileSpreadsheet",
                "ordre": 3,
                "children": [
                    {"nom": "Reglements par Periode", "code": "DS_REGLEMENTS_PAR_PERIODE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 1},
                    {"nom": "Reglements par Client", "code": "DS_REGLEMENTS_PAR_CLIENT", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 2},
                    {"nom": "Reglements par Mode", "code": "DS_REGLEMENTS_PAR_MODE", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 3},
                    {"nom": "Factures Non Reglees", "code": "DS_FACTURES_NON_REGLEES", "type": "datasource", "icon": "FileSpreadsheet", "ordre": 4},
                ]
            },
        ]
    },
]


def get_datasource_template_id(code):
    """Recupere l'ID d'un template de datasource par son code"""
    try:
        result = execute_query(
            "SELECT id FROM APP_DataSources_Templates WHERE code = ?",
            (code,),
            use_cache=False
        )
        if result:
            return result[0]['id']
        return None
    except Exception as e:
        print(f"  Erreur recherche template {code}: {e}")
        return None


def create_menu(menu, parent_id=None):
    """Cree un menu de facon recursive"""
    try:
        # Verifier si existe deja
        existing = execute_query(
            "SELECT id FROM APP_Menus WHERE code = ?",
            (menu['code'],),
            use_cache=False
        )

        if existing:
            menu_id = existing[0]['id']
            print(f"  Menu '{menu['nom']}' existe deja (id={menu_id})")
        else:
            # Determiner le type et target_id
            menu_type = menu.get('type', 'folder')
            target_id = None

            if menu_type == 'datasource':
                # C'est un lien vers un template de datasource
                target_id = get_datasource_template_id(menu['code'])
                if not target_id:
                    print(f"  WARN: Template '{menu['code']}' non trouve")
                    return None
                menu_type = 'gridview'  # Les datasources sont affichees en gridview

            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO APP_Menus (parent_id, nom, code, icon, type, target_id, ordre, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    parent_id,
                    menu['nom'],
                    menu['code'],
                    menu.get('icon', 'Folder'),
                    menu_type,
                    target_id,
                    menu.get('ordre', 1)
                ))
                cursor.execute("SELECT @@IDENTITY AS id")
                menu_id = cursor.fetchone()[0]
                print(f"  Menu '{menu['nom']}' cree (id={menu_id})")

        # Creer les enfants
        if 'children' in menu:
            for child in menu['children']:
                create_menu(child, menu_id)

        return menu_id

    except Exception as e:
        print(f"  ERREUR menu '{menu['nom']}': {e}")
        return None


def delete_old_menus():
    """Supprime les anciens menus pour recreer proprement"""
    try:
        with get_db_cursor() as cursor:
            # Compter les menus existants
            cursor.execute("SELECT COUNT(*) as cnt FROM APP_Menus")
            count = cursor.fetchone()[0]

            if count > 0:
                print(f"  Suppression de {count} menus existants...")
                cursor.execute("DELETE FROM APP_Menus")
                print("  Menus supprimes")
            else:
                print("  Aucun menu existant")

    except Exception as e:
        print(f"  Erreur suppression menus: {e}")


def main():
    print("=" * 60)
    print("INITIALISATION DE LA STRUCTURE DES MENUS")
    print("=" * 60)

    # Option: supprimer les anciens menus
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("\n[0/2] Suppression des anciens menus...")
        delete_old_menus()

    # 1. Verifier les templates de datasources
    print("\n[1/2] Verification des templates de datasources...")
    templates = execute_query(
        "SELECT COUNT(*) as cnt FROM APP_DataSources_Templates",
        use_cache=False
    )
    print(f"  {templates[0]['cnt']} templates disponibles")

    # 2. Creer les menus
    print("\n[2/2] Creation des menus...")
    for menu in MENU_STRUCTURE:
        create_menu(menu)

    # Resume
    print("\n" + "=" * 60)
    print("TERMINE!")
    menus_count = execute_query(
        "SELECT COUNT(*) as cnt FROM APP_Menus",
        use_cache=False
    )
    print(f"  {menus_count[0]['cnt']} menus dans la base")
    print("=" * 60)


if __name__ == "__main__":
    main()
