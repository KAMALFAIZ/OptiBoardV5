"""Script pour creer les GridViews Comptabilite et mettre a jour les menus"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import execute_query, get_db_cursor

GRIDVIEWS = [
    # === Ecritures Comptables ===
    {
        "nom": "Ecritures Global", "description": "Synthese globale des ecritures comptables",
        "data_source_code": "DS_ECRITURES_GLOBAL", "menu_code": "DS_ECRITURES_GLOBAL",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Nb Ecritures", "header": "Nb Ecritures", "width": 120, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Debit", "header": "Total Debit", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Credit", "header": "Total Credit", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde", "header": "Solde", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Comptes", "header": "Nb Comptes", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Journaux", "header": "Nb Journaux", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Total Debit", "direction": "desc"},
        "total_columns": ["Nb Ecritures", "Total Debit", "Total Credit", "Solde"],
    },
    {
        "nom": "Ecritures par Journal", "description": "Ecritures ventilees par journal",
        "data_source_code": "DS_ECRITURES_PAR_JOURNAL", "menu_code": "DS_ECRITURES_PAR_JOURNAL",
        "columns": [
            {"field": "Code Journal", "header": "Code", "width": 80, "sortable": True, "visible": True},
            {"field": "Journal", "header": "Journal", "width": 200, "sortable": True, "visible": True},
            {"field": "Type Journal", "header": "Type", "width": 120, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Ecritures", "header": "Nb Ecritures", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Debit", "header": "Total Debit", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Credit", "header": "Total Credit", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Pieces", "header": "Nb Pieces", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Total Debit", "direction": "desc"},
        "total_columns": ["Nb Ecritures", "Total Debit", "Total Credit"],
    },
    {
        "nom": "Ecritures par Compte", "description": "Ecritures ventilees par compte general",
        "data_source_code": "DS_ECRITURES_PAR_COMPTE", "menu_code": "DS_ECRITURES_PAR_COMPTE",
        "columns": [
            {"field": "Compte", "header": "Compte", "width": 120, "sortable": True, "visible": True},
            {"field": "Intitule", "header": "Intitule", "width": 250, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Total Debit", "header": "Total Debit", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Credit", "header": "Total Credit", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde", "header": "Solde", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Ecritures", "header": "Nb Ecritures", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Compte", "direction": "asc"},
        "total_columns": ["Total Debit", "Total Credit", "Solde"],
    },
    {
        "nom": "Ecritures par Tiers", "description": "Ecritures ventilees par tiers (clients/fournisseurs)",
        "data_source_code": "DS_ECRITURES_PAR_TIERS", "menu_code": "DS_ECRITURES_PAR_TIERS",
        "columns": [
            {"field": "Code Tiers", "header": "Code Tiers", "width": 110, "sortable": True, "visible": True},
            {"field": "Tiers", "header": "Tiers", "width": 220, "sortable": True, "visible": True},
            {"field": "Type", "header": "Type", "width": 100, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Total Debit", "header": "Total Debit", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Credit", "header": "Total Credit", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde", "header": "Solde", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Ecritures", "header": "Nb Ecritures", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Pieces", "header": "Nb Pieces", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Solde", "direction": "desc"},
        "total_columns": ["Total Debit", "Total Credit", "Solde"],
    },
    {
        "nom": "Ecritures par Mois", "description": "Ecritures ventilees par mois",
        "data_source_code": "DS_ECRITURES_PAR_MOIS", "menu_code": "DS_ECRITURES_PAR_MOIS",
        "columns": [
            {"field": "Annee", "header": "Annee", "width": 80, "sortable": True, "visible": True},
            {"field": "Mois", "header": "Mois", "width": 80, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Ecritures", "header": "Nb Ecritures", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Debit", "header": "Total Debit", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Credit", "header": "Total Credit", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Comptes", "header": "Nb Comptes", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Pieces", "header": "Nb Pieces", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Annee", "direction": "desc"},
        "total_columns": ["Nb Ecritures", "Total Debit", "Total Credit"],
    },
    {
        "nom": "Detail Ecritures", "description": "Detail complet de toutes les ecritures comptables",
        "data_source_code": "DS_ECRITURES_DETAIL", "menu_code": "DS_ECRITURES_DETAIL",
        "columns": [
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Journal", "header": "Code Jnl", "width": 80, "sortable": True, "visible": True},
            {"field": "Journal", "header": "Journal", "width": 150, "sortable": True, "visible": True},
            {"field": "Piece", "header": "Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Compte", "header": "Compte", "width": 110, "sortable": True, "visible": True},
            {"field": "Intitule Compte", "header": "Intitule", "width": 200, "sortable": True, "visible": True},
            {"field": "Compte Tiers", "header": "Tiers", "width": 100, "sortable": True, "visible": True},
            {"field": "Tiers", "header": "Nom Tiers", "width": 180, "sortable": True, "visible": True},
            {"field": "Libelle", "header": "Libelle", "width": 250, "sortable": True, "visible": True},
            {"field": "D\u00e9bit", "header": "Debit", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Cr\u00e9dit", "header": "Credit", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Sens", "header": "Sens", "width": 60, "sortable": True, "visible": True},
            {"field": "Echeance", "header": "Echeance", "width": 100, "format": "date", "sortable": True, "visible": False},
            {"field": "Mode Reglement", "header": "Mode Reglement", "width": 120, "sortable": True, "visible": False},
            {"field": "R\u00e9f\u00e9rence", "header": "Reference", "width": 100, "sortable": True, "visible": False},
            {"field": "Lettrage", "header": "Lettrage", "width": 80, "sortable": True, "visible": False},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["D\u00e9bit", "Cr\u00e9dit"],
    },
    # === Grand Livre / Balance ===
    {
        "nom": "Grand Livre", "description": "Grand livre comptable",
        "data_source_code": "DS_GRAND_LIVRE", "menu_code": "DS_GRAND_LIVRE",
        "columns": [
            {"field": "Compte", "header": "Compte", "width": 110, "sortable": True, "visible": True},
            {"field": "Intitule", "header": "Intitule", "width": 220, "sortable": True, "visible": True},
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Journal", "header": "Journal", "width": 80, "sortable": True, "visible": True},
            {"field": "Piece", "header": "Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Libelle", "header": "Libelle", "width": 250, "sortable": True, "visible": True},
            {"field": "D\u00e9bit", "header": "Debit", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Cr\u00e9dit", "header": "Credit", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Compte Tiers", "header": "Tiers", "width": 100, "sortable": True, "visible": True},
            {"field": "Tiers", "header": "Nom Tiers", "width": 180, "sortable": True, "visible": True},
            {"field": "Lettrage", "header": "Lettrage", "width": 80, "sortable": True, "visible": False},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Compte", "direction": "asc"},
        "total_columns": ["D\u00e9bit", "Cr\u00e9dit"],
    },
    {
        "nom": "Balance Generale", "description": "Balance generale des comptes",
        "data_source_code": "DS_BALANCE_GENERALE", "menu_code": "DS_BALANCE_GENERALE",
        "columns": [
            {"field": "Compte", "header": "Compte", "width": 110, "sortable": True, "visible": True},
            {"field": "Intitule", "header": "Intitule", "width": 250, "sortable": True, "visible": True},
            {"field": "Nature", "header": "Nature", "width": 100, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "A Nouveau", "header": "A Nouveau", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Mvt Debit", "header": "Mvt Debit", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Mvt Credit", "header": "Mvt Credit", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Debit", "header": "Total Debit", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Credit", "header": "Total Credit", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde", "header": "Solde", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde Debiteur", "header": "Solde D", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde Crediteur", "header": "Solde C", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Compte", "direction": "asc"},
        "total_columns": ["Mvt Debit", "Mvt Credit", "Total Debit", "Total Credit", "Solde", "Solde Debiteur", "Solde Crediteur"],
    },
    # === Bilan ===
    {
        "nom": "Bilan Synthetique", "description": "Bilan synthetique actif/passif",
        "data_source_code": "DS_BILAN_SYNTHETIQUE", "menu_code": "DS_BILAN_SYNTHETIQUE",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Immob Brut", "header": "Immob. Brut", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Amortissements", "header": "Amortissements", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Actif Immobilise Net", "header": "Actif Immob. Net", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Stocks", "header": "Stocks", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Creances", "header": "Creances", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Tresorerie Actif", "header": "Tresorerie", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Capitaux Propres", "header": "Capitaux Propres", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Dettes", "header": "Dettes", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Actif", "header": "Total Actif", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Passif", "header": "Total Passif", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Societe", "direction": "asc"},
        "total_columns": ["Total Actif", "Total Passif"],
    },
    {
        "nom": "Bilan Actif", "description": "Bilan actif par classe",
        "data_source_code": "DS_BILAN_ACTIF", "menu_code": "DS_BILAN_ACTIF",
        "columns": [
            {"field": "Classe", "header": "Classe", "width": 250, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Montant", "header": "Montant", "width": 150, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Comptes", "header": "Nb Comptes", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Montant", "direction": "desc"},
        "total_columns": ["Montant"],
    },
    {
        "nom": "Actif Immobilise", "description": "Detail de l'actif immobilise",
        "data_source_code": "DS_ACTIF_IMMOBILISE", "menu_code": "DS_ACTIF_IMMOBILISE",
        "columns": [
            {"field": "Classe", "header": "Classe", "width": 250, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Valeur Brute", "header": "Valeur Brute", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Amortissements", "header": "Amortissements", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Nette", "header": "Valeur Nette", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Valeur Nette", "direction": "desc"},
        "total_columns": ["Valeur Brute", "Amortissements", "Valeur Nette"],
    },
    {
        "nom": "Actif Circulant", "description": "Detail de l'actif circulant",
        "data_source_code": "DS_ACTIF_CIRCULANT", "menu_code": "DS_ACTIF_CIRCULANT",
        "columns": [
            {"field": "Categorie", "header": "Categorie", "width": 300, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Montant", "header": "Montant", "width": 150, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Montant", "direction": "desc"},
        "total_columns": ["Montant"],
    },
    {
        "nom": "Bilan Passif", "description": "Bilan passif par classe",
        "data_source_code": "DS_BILAN_PASSIF", "menu_code": "DS_BILAN_PASSIF",
        "columns": [
            {"field": "Classe", "header": "Classe", "width": 250, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Montant", "header": "Montant", "width": 150, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Comptes", "header": "Nb Comptes", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Montant", "direction": "desc"},
        "total_columns": ["Montant"],
    },
    {
        "nom": "Capitaux Propres", "description": "Detail des capitaux propres",
        "data_source_code": "DS_CAPITAUX_PROPRES", "menu_code": "DS_CAPITAUX_PROPRES",
        "columns": [
            {"field": "Compte", "header": "Compte", "width": 120, "sortable": True, "visible": True},
            {"field": "Intitule", "header": "Intitule", "width": 300, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Montant", "header": "Montant", "width": 150, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Compte", "direction": "asc"},
        "total_columns": ["Montant"],
    },
    {
        "nom": "Dettes", "description": "Detail des dettes fournisseurs",
        "data_source_code": "DS_DETTES", "menu_code": "DS_DETTES",
        "columns": [
            {"field": "Fournisseur", "header": "Fournisseur", "width": 250, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Montant", "header": "Montant", "width": 150, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Ecritures", "header": "Nb Ecritures", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Montant", "direction": "desc"},
        "total_columns": ["Montant"],
    },
    # === CPC ===
    {
        "nom": "CPC Global", "description": "Compte de produits et charges global",
        "data_source_code": "DS_CPC_GLOBAL", "menu_code": "DS_CPC_GLOBAL",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Ventes Marchandises", "header": "Ventes March.", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Ventes Biens Services", "header": "Ventes B&S", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Produits Exploitation", "header": "Tot. Produits", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats Marchandises", "header": "Achats March.", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats Matieres", "header": "Achats Mat.", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Autres Charges Externes", "header": "Charges Ext.", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Charges Personnel", "header": "Charges Pers.", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Dotations Amortissements", "header": "Dotations", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Charges Exploitation", "header": "Tot. Charges", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Resultat Exploitation", "header": "Resultat Expl.", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Produits Financiers", "header": "Prod. Financ.", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": False},
            {"field": "Charges Financieres", "header": "Charges Fin.", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": False},
            {"field": "Resultat Net", "header": "Resultat Net", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Resultat Net", "direction": "desc"},
        "total_columns": ["Total Produits Exploitation", "Total Charges Exploitation", "Resultat Exploitation", "Resultat Net"],
    },
    {
        "nom": "CPC Produits", "description": "Detail des produits du CPC",
        "data_source_code": "DS_CPC_PRODUITS", "menu_code": "DS_CPC_PRODUITS",
        "columns": [
            {"field": "Classe", "header": "Classe", "width": 300, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Montant", "header": "Montant", "width": 150, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Comptes", "header": "Nb Comptes", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Montant", "direction": "desc"},
        "total_columns": ["Montant"],
    },
    {
        "nom": "CPC Charges", "description": "Detail des charges du CPC",
        "data_source_code": "DS_CPC_CHARGES", "menu_code": "DS_CPC_CHARGES",
        "columns": [
            {"field": "Classe", "header": "Classe", "width": 300, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Montant", "header": "Montant", "width": 150, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Comptes", "header": "Nb Comptes", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Montant", "direction": "desc"},
        "total_columns": ["Montant"],
    },
    {
        "nom": "CPC par Mois", "description": "Evolution mensuelle du CPC",
        "data_source_code": "DS_CPC_PAR_MOIS", "menu_code": "DS_CPC_PAR_MOIS",
        "columns": [
            {"field": "Annee", "header": "Annee", "width": 80, "sortable": True, "visible": True},
            {"field": "Mois", "header": "Mois", "width": 80, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Produits", "header": "Produits", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Charges", "header": "Charges", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Resultat", "header": "Resultat", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Annee", "direction": "desc"},
        "total_columns": ["Produits", "Charges", "Resultat"],
    },
    # === Tresorerie ===
    {
        "nom": "Tresorerie", "description": "Situation de tresorerie par compte",
        "data_source_code": "DS_TRESORERIE", "menu_code": "DS_TRESORERIE",
        "columns": [
            {"field": "Compte", "header": "Compte", "width": 120, "sortable": True, "visible": True},
            {"field": "Intitule", "header": "Intitule", "width": 250, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Solde Initial", "header": "Solde Initial", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Encaissements", "header": "Encaissements", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Decaissements", "header": "Decaissements", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde Final", "header": "Solde Final", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Solde Final", "direction": "desc"},
        "total_columns": ["Solde Initial", "Encaissements", "Decaissements", "Solde Final"],
    },
    {
        "nom": "Tresorerie par Mois", "description": "Evolution mensuelle de la tresorerie",
        "data_source_code": "DS_TRESORERIE_PAR_MOIS", "menu_code": "DS_TRESORERIE_PAR_MOIS",
        "columns": [
            {"field": "Annee", "header": "Annee", "width": 80, "sortable": True, "visible": True},
            {"field": "Mois", "header": "Mois", "width": 80, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Encaissements", "header": "Encaissements", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Decaissements", "header": "Decaissements", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Flux Net", "header": "Flux Net", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Annee", "direction": "desc"},
        "total_columns": ["Encaissements", "Decaissements", "Flux Net"],
    },
    # === Analytique ===
    {
        "nom": "Analytique Global", "description": "Comptabilite analytique globale",
        "data_source_code": "DS_ANALYTIQUE_GLOBAL", "menu_code": "DS_ANALYTIQUE_GLOBAL",
        "columns": [
            {"field": "Plan", "header": "Plan", "width": 120, "sortable": True, "visible": True},
            {"field": "Compte", "header": "Compte", "width": 120, "sortable": True, "visible": True},
            {"field": "Intitule", "header": "Intitule", "width": 250, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Montant", "header": "Montant", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Quantite", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Ecritures", "header": "Nb Ecritures", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Montant", "direction": "desc"},
        "total_columns": ["Montant", "Quantite"],
    },
    {
        "nom": "Analytique par Plan", "description": "Synthese analytique par plan",
        "data_source_code": "DS_ANALYTIQUE_PAR_PLAN", "menu_code": "DS_ANALYTIQUE_PAR_PLAN",
        "columns": [
            {"field": "Plan", "header": "Plan", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Total Montant", "header": "Total Montant", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Total Quantite", "header": "Total Qte", "width": 120, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Ecritures", "header": "Nb Ecritures", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Comptes", "header": "Nb Comptes", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Total Montant", "direction": "desc"},
        "total_columns": ["Total Montant", "Total Quantite"],
    },
    {
        "nom": "Detail Analytique", "description": "Detail des ecritures analytiques",
        "data_source_code": "DS_ANALYTIQUE_DETAIL", "menu_code": "DS_ANALYTIQUE_DETAIL",
        "columns": [
            {"field": "Plan", "header": "Plan", "width": 120, "sortable": True, "visible": True},
            {"field": "Compte Analytique", "header": "Compte", "width": 120, "sortable": True, "visible": True},
            {"field": "Intitule", "header": "Intitule", "width": 250, "sortable": True, "visible": True},
            {"field": "Montant", "header": "Montant", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Quantite", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Montant", "direction": "desc"},
        "total_columns": ["Montant", "Quantite"],
    },
    # === Echeances / Lettrage ===
    {
        "nom": "Echeances Comptables", "description": "Echeances comptables a venir",
        "data_source_code": "DS_ECHEANCES_COMPTABLES", "menu_code": "DS_ECHEANCES_COMPTABLES",
        "columns": [
            {"field": "Echeance", "header": "Echeance", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Compte", "header": "Compte", "width": 110, "sortable": True, "visible": True},
            {"field": "Compte Tiers", "header": "Code Tiers", "width": 100, "sortable": True, "visible": True},
            {"field": "Tiers", "header": "Tiers", "width": 200, "sortable": True, "visible": True},
            {"field": "Piece", "header": "Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Libelle", "header": "Libelle", "width": 250, "sortable": True, "visible": True},
            {"field": "D\u00e9bit", "header": "Debit", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Cr\u00e9dit", "header": "Credit", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Mode Reglement", "header": "Mode Reglement", "width": 120, "sortable": True, "visible": True},
            {"field": "Jours Avant Echeance", "header": "Jours", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Type tiers", "header": "Type Tiers", "width": 100, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Echeance", "direction": "asc"},
        "total_columns": ["D\u00e9bit", "Cr\u00e9dit"],
    },
    {
        "nom": "Analyse Lettrage", "description": "Analyse du lettrage des comptes",
        "data_source_code": "DS_LETTRAGE", "menu_code": "DS_LETTRAGE",
        "columns": [
            {"field": "Compte", "header": "Compte", "width": 120, "sortable": True, "visible": True},
            {"field": "Intitule", "header": "Intitule", "width": 250, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Nb Lettrees", "header": "Nb Lettrees", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Non Lettrees", "header": "Nb Non Lettrees", "width": 130, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde Non Lettre", "header": "Solde Non Lettre", "width": 140, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Solde Non Lettre", "direction": "desc"},
        "total_columns": ["Nb Lettrees", "Nb Non Lettrees", "Solde Non Lettre"],
    },
]


def create_gridviews():
    results = []
    with get_db_cursor() as cursor:
        for gv in GRIDVIEWS:
            columns_json = json.dumps(gv["columns"], ensure_ascii=False)
            default_sort_json = json.dumps(gv["default_sort"])
            total_columns_json = json.dumps(gv["total_columns"], ensure_ascii=False)
            features_json = json.dumps({
                "show_search": True, "show_column_filters": True,
                "show_grouping": True, "show_column_toggle": True,
                "show_export": True, "show_pagination": True,
                "show_page_size": True, "allow_sorting": True,
            })
            cursor.execute("""
                INSERT INTO APP_GridViews
                    (nom, description, columns_config, features, actif, data_source_code,
                     default_sort, page_size, show_totals, total_columns, is_public, created_by)
                VALUES (?, ?, ?, ?, 1, ?, ?, 50, 1, ?, 1, 1)
            """, (gv["nom"], gv["description"], columns_json, features_json,
                  gv["data_source_code"], default_sort_json, total_columns_json))
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = int(cursor.fetchone()[0])
            cursor.execute("UPDATE APP_Menus SET target_id = ? WHERE code = ? AND type = 'gridview'", (new_id, gv["menu_code"]))
            ok = cursor.rowcount
            results.append({"nom": gv["nom"], "id": new_id, "menu_ok": ok})
            print(f"  OK: {gv['nom']} (GV ID={new_id}, menu={ok})")
    return results

if __name__ == "__main__":
    print(f"Creation de {len(GRIDVIEWS)} GridViews Comptabilite...")
    print()
    results = create_gridviews()
    print()
    ok = sum(1 for r in results if r["menu_ok"] > 0)
    print(f"Termine: {len(results)} GridViews, {ok}/{len(results)} menus OK")
