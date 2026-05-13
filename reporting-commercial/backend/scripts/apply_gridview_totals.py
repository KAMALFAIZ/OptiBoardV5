# -*- coding: utf-8 -*-
"""
Applique total_columns sur chaque GridView selon la logique métier.

Règles :
  - SUM (inclure dans total_columns) : montants, quantités, poids, coûts, marges, nb docs/clients/articles
  - EXCLURE : taux (%), moyennes, prix unitaires, rangs, identifiants, dates, textes

Le frontend buildTotalsRow() fait un SUM simple — on ne met que les champs sommables.
"""
import pyodbc
import json
import re

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

conn = pyodbc.connect(CONN_STR, autocommit=True)
cursor = conn.cursor()

# =====================================================================
#  PATTERNS : champs à EXCLURE du total (pas sommables)
# =====================================================================
EXCLUDE_PATTERNS = [
    # Taux, pourcentages
    r'taux',
    r'%',
    r'evolution\s*%',
    r'taux\s+marge',
    r'taux\s+retour',
    r'taux\s+conversion',
    r'taux\s+recouvrement',
    r'cout\s+possession\s+%',
    # Prix unitaires, moyennes
    r'prix\s+moyen',
    r'prix\s+min',
    r'prix\s+max',
    r'pu\s+ht',
    r'^pu$',
    r'^cmup$',
    r'panier\s+moyen',
    r'pv\s+moyen',
    r'pr\s+moyen',
    r'cout\s+revient\s+moyen',
    r'montant\s+moyen',
    r'ca\s+moyen',
    r'qte\s+moy',
    r'ecart\s+type',
    r'delai\s+moyen',
    r'delai\s+min',
    r'delai\s+max',
    r'moy\s+jours',
    r'prix\s+unitaire',
    r'dpa\s+',
    r'dpr\s+',
    r'cout\s+standard',
    # Rangs
    r'^rang\b',
    # Identifiants, codes
    r'^code\s',
    r'^num',
    r'^n°',
    r'^id\b',
    r'^societe$',
    r'^commercial$',
    r'^client$',
    r'^fournisseur$',
    r'^designation',
    r'^intitul',
    r'^tiers\b',
    r'^tier\s',
    r'^depot$',
    r'^famille$',
    r'^sous.famille$',
    r'^catalogue',
    r'^gamme',
    r'^unite$',
    r'^lot\s',
    r'^reference$',
    r'^motif$',
    r'^statut',
    r'^segment',
    r'^categorie',
    r'^region$',
    r'^ville$',
    r'^nom\s+mois',
    r'^type\s+',
    r'^domaine',
    r'^sens\b',
    r'^suivi',
    r'^urgence',
    r'^niveau',
    r'^tranche',
    r'^mode\s+',
    r'^mouvemente$',
    r'^depot\s+principal',
    r'^valorise',
    r'^souche',
    r'^classe\s+',
    # Dates
    r'date\b',
    r'^annee$',
    r'^mois$',
    r'^periode$',
    r'derniere\s+vente',
    r'premiere\s+vente',
    r'premier\s+achat',
    r'^anciennete',
    r'ancienne\s+echeance',
    r'plus\s+ancienne',
    r'plus\s+recente',
    r'peremption',
    r'fabrication',
    # Textes/labels divers
    r'^article$',
    r'^affaire$',
    r'^tiers\s+payeur',
    r'^risque$',
    r'^jours\s+sans\s+achat',
    r'^jours\s+inactif',
    r'^jours\s+restants',
    r'^jours\s+retard',
    r'^jours\s+de\s+retard',
    r'^max\s+jours',
    r'^recence',
    r'^frequence$',
    r'^score\s',
    r'^nb\s+mois',
]


def is_summable(field_name):
    """Retourne True si le champ est sommable (montants, quantites, poids, nb)."""
    f = field_name.lower().strip()

    # Vérifier les exclusions
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, f, re.IGNORECASE):
            return False

    # Patterns positifs : champs sommables
    SUM_PATTERNS = [
        r'^ca\s',
        r'^ca$',
        r'montant',
        r'marge\s+brute',
        r'^marge$',
        r'cout\s+revient(?!\s+moyen)',
        r'quantit',
        r'^qte\b',
        r'^nb\s',
        r'poids',
        r'valeur\s+stock',
        r'total\b',
        r'ecart$',
        r'excedent',
        r'reste\s+a',
        r'caution',
        r'solde',
        r'non\s+echu',
        r'1-30j',
        r'31-60j',
        r'61-90j',
        r'plus\s+90j',
        r'impay',
        r'reglements\s+non',
        r'bl\s+non\s+factur',
        r'articles\s+rupture',
        r'articles\s+surstock',
        r'stock\s+min',
        r'stock\s+max',
        r'consommation',
        r'qte\s+entree',
        r'qte\s+sortie',
        r'valeur\s+entree',
        r'valeur\s+sortie',
        r'qte\s+stock',
        r'qte\s+command',
        r'qte\s+livr',
        r'qte\s+re[cç]ue',
        r'qte\s+restante',
        r'remise',
        r'montant\s+brut',
        r'total\s+remises',
        r'^nb\s+factures',
        r'^nb\s+devis',
        r'^nb\s+convertis',
        r'^nb\s+documents',
        r'^nb\s+lignes',
        r'^nb\s+livres',
        r'^nb\s+retours',
        r'^nb\s+clients',
        r'^nb\s+articles',
        r'^nb\s+fournisseurs',
        r'^nb\s+transactions',
        r'^nb\s+reglements',
        r'^nb\s+echeances',
        r'^nb\s+documents\s+retour',
        r'quantite\s+retournee',
        r'montant\s+ht\s+retour',
        r'ca\s+ht',
        r'ca\s+ttc',
        r'ca\s+n$',
        r'ca\s+n-1',
        r'ca\s+n-2',
        r'ca\s+6m',
        r'ca\s+ht\s+total',
        r'ca\s+ht\s+historique',
        r'nb\s+docs',
        r'nb\s+documents\s+historique',
        r'^marge\s+n',
    ]

    for pat in SUM_PATTERNS:
        if re.search(pat, f, re.IGNORECASE):
            return True

    return False


# =====================================================================
#  Mise à jour de toutes les GridViews
# =====================================================================
rows = cursor.execute(
    "SELECT id, nom, data_source_code, columns_config FROM APP_GridViews WHERE actif = 1"
).fetchall()

print(f"{'=' * 70}")
print(f"  APPLICATION DES TOTAUX — {len(rows)} GridViews")
print(f"{'=' * 70}")

updated = 0
for row in rows:
    gv_id, nom, ds_code, cols_json = row
    if not cols_json:
        continue

    cols = json.loads(cols_json)
    fields = [c.get("field", "") for c in cols]

    total_cols = [f for f in fields if f and is_summable(f)]

    if total_cols:
        tc_json = json.dumps(total_cols, ensure_ascii=False)
        cursor.execute(
            "UPDATE APP_GridViews SET show_totals = 1, total_columns = ? WHERE id = ?",
            (tc_json, gv_id)
        )
        updated += 1
        print(f"  [{gv_id}] {ds_code or '?':<35} -> {len(total_cols)} totaux: {total_cols}")
    else:
        cursor.execute(
            "UPDATE APP_GridViews SET show_totals = 0, total_columns = '[]' WHERE id = ?",
            (gv_id,)
        )
        print(f"  [{gv_id}] {ds_code or '?':<35} -> aucun total")

print(f"\n{'=' * 70}")
print(f"  {updated} / {len(rows)} GridViews avec totaux")
print(f"{'=' * 70}")

cursor.close()
conn.close()
