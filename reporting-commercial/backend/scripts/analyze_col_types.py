"""Analyse les colonnes des gridviews : propose le bon type pour chaque champ."""
import sys, os, json, warnings, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Patterns pour détecter le type correct par nom de colonne
DATE_PATTERNS   = re.compile(r'date|echeance|livraison|reglement|creation|modification|debut|fin|expir', re.I)
NUMBER_PATTERNS = re.compile(r'montant|ht|ttc|tva|qte|quantit|prix|pu|pv|marge|ca|chiffre|taux|total|solde|credit|debit|poids|cout|ecart|stock|valeur|budget|ratio|score|duree|nb_|_nb|nombre|rang|page|remise|encours|reste|deja|paye|impaye', re.I)
TEXT_PATTERNS   = re.compile(r'^(code|ref|reference|num|numero|n\s*°|n\s*\.|piece|societe|intitule|libelle|designation|description|categorie|famille|depot|commercial|client|fournisseur|article|affaire|representant|type|statut|mode|nature|pays|ville|region)', re.I)

grids = execute_central(
    "SELECT id, nom, data_source_code, columns_config FROM APP_GridViews WHERE actif=1 ORDER BY nom"
)

# Collecter toutes les colonnes sans type explicite et proposer
print("=== COLONNES SANS TYPE DEFINI (type=?) — PROPOSITION ===\n")
print(f"{'GridView':<35} {'Colonne':<35} {'Type actuel':<12} {'Type proposé'}")
print("-"*100)

seen = set()
for g in grids:
    cfg = g['columns_config'] or '[]'
    try:
        cols = json.loads(cfg)
    except:
        cols = []
    for c in cols:
        t   = c.get('type', '')
        fmt = c.get('format', '') or ''
        f   = c.get('field', c.get('header', ''))
        if not f:
            continue

        # Proposer un type
        if DATE_PATTERNS.search(f) or fmt == 'date':
            proposed = 'date'
        elif NUMBER_PATTERNS.search(f) or fmt in ('#,##0.00', '#,##0', 'number', 'currency'):
            proposed = 'number'
        elif TEXT_PATTERNS.search(f):
            proposed = 'text'
        else:
            proposed = '?'

        # Signaler seulement les cas ambigus ou manquants
        actual = t or '(vide)'
        key = f.lower().strip()
        if key in seen:
            continue
        if actual not in ('number', 'date', 'text', 'boolean'):
            seen.add(key)
            gname = g['nom'][:34]
            fname = f[:34]
            print(f"{gname:<35} {fname:<35} {actual:<12} {proposed}")
