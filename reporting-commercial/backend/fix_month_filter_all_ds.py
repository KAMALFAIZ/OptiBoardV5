# -*- coding: utf-8 -*-
"""
fix_month_filter_all_ds.py
==========================
Corrige automatiquement TOUS les DataSources qui filtrent par YEAR(@dateFin)
sans restreindre le mois -> ils affichent toujours 12 mois meme si l'utilisateur
choisit une periode de 5 mois.

Logique metier appliquee :
  Si dateDebut = 01/01/2025 et dateFin = 31/05/2025
  -> comparer les MOIS 1 a 5 de 2025 vs les MOIS 1 a 5 de 2024

Correction injectee apres chaque filtre YEAR([champ]) IN (...) :
  AND MONTH([<champ_date>]) BETWEEN MONTH(@dateDebut) AND MONTH(@dateFin)

Exclusions (logique metier) :
  - Pattern [Exercice] = YEAR(@dateFin) : rapports comptables annuels
    (Bilan, CPC, etc.) - le filtre mois n'a pas de sens sur un exercice fiscal

Usage :
  python fix_month_filter_all_ds.py            -> applique les corrections
  python fix_month_filter_all_ds.py --dry-run  -> simulation sans modifier la DB
"""

import sys, os, re, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database_unified import get_central_connection

DRY_RUN = "--dry-run" in sys.argv

# ---------------------------------------------------------------------------
# Pattern 1 (A CORRIGER) : comparatif multi-annees sur un champ DATE
# Exemples :
#   AND YEAR([Date BL]) IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
#   AND YEAR([Date])    IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
# ---------------------------------------------------------------------------
YEAR_IN_PATTERN = re.compile(
    r'(AND\s+YEAR\(\[([^\]]+)\]\)\s+IN\s*\([^)]*YEAR\(@dateFin\)[^)]*\))',
    re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Pattern 2 (EXCLURE) : rapports comptables sur champ entier [Exercice]
# Exemple : WHERE [Exercice] = YEAR(@dateFin)
# -> MONTH([Exercice]) impossible (entier, pas une date) + logique annuelle
# ---------------------------------------------------------------------------
EXERCICE_PATTERN = re.compile(
    r'\[Exercice\]\s*=\s*YEAR\(@dateFin\)',
    re.IGNORECASE
)

# Deja corrige si cette expression existe
ALREADY_FIXED_PATTERN = re.compile(
    r'MONTH\s*\(\s*@dateDebut\s*\)',
    re.IGNORECASE
)

PARAMS_OBJ_DATEDEBUT = {"name": "dateDebut", "type": "date", "source": "global"}


def ensure_datedebut_in_params(params_str: str) -> str:
    """
    Ajoute dateDebut dans le JSON parameters s'il n'y est pas deja.
    Supporte les deux formats :
      - ["dateDebut","dateFin","societe"]           (simple array de strings)
      - [{"name":"dateFin",...}, ...]               (array d'objets)
    """
    if not params_str:
        return params_str

    if re.search(r'"dateDebut"', params_str, re.IGNORECASE):
        return params_str  # deja present

    try:
        params = json.loads(params_str)
    except Exception:
        return params_str  # JSON invalide -> on ne touche pas

    if not isinstance(params, list) or len(params) == 0:
        return params_str

    if isinstance(params[0], str):
        # Format simple : ["dateFin", "societe"]
        if "dateDebut" not in params:
            params.insert(0, "dateDebut")
    elif isinstance(params[0], dict):
        # Format objet
        names = [p.get("name", "") for p in params]
        if "dateDebut" not in names:
            params.insert(0, PARAMS_OBJ_DATEDEBUT)

    return json.dumps(params, ensure_ascii=False)


def inject_month_filter(query: str) -> tuple:
    """
    Detecte chaque filtre YEAR([champ]) IN (...) et insere le filtre MONTH
    juste apres.
    Retourne (nouvelle_query, liste_des_champs_corriges).
    """
    if ALREADY_FIXED_PATTERN.search(query):
        return query, []

    fixed_fields = []
    result = query

    for match in YEAR_IN_PATTERN.finditer(query):
        full_match = match.group(1)
        field_name = match.group(2)
        month_line = f"\n  AND MONTH([{field_name}]) BETWEEN MONTH(@dateDebut) AND MONTH(@dateFin)"
        result = result.replace(full_match, full_match + month_line, 1)
        fixed_fields.append(field_name)

    return result, fixed_fields


def classify(query: str):
    """
    Retourne :
      'already_ok'  -> filtre MONTH(@dateDebut) deja present
      'exercice'    -> rapport comptable annuel, exclusion metier
      'fixable'     -> YEAR IN detecte, correction possible
      'unknown'     -> YEAR(@dateFin) present mais pattern non reconnu
    """
    if ALREADY_FIXED_PATTERN.search(query):
        return 'already_ok'
    if EXERCICE_PATTERN.search(query):
        return 'exercice'
    if YEAR_IN_PATTERN.search(query):
        return 'fixable'
    return 'unknown'


def run():
    conn = get_central_connection()
    conn.autocommit = True
    cur = conn.cursor()

    # Tous les datasources utilisant YEAR(@dateFin)
    cur.execute("""
        SELECT code, nom, query_template, parameters
        FROM APP_DataSources_Templates
        WHERE query_template LIKE '%YEAR(@dateFin)%'
        ORDER BY code
    """)
    rows = cur.fetchall()

    print("=" * 70)
    print("  Fix MONTH filter - {} datasource(s) avec YEAR(@dateFin)".format(len(rows)))
    if DRY_RUN:
        print("  MODE DRY-RUN : aucune modification en base")
    print("=" * 70)
    print()

    updated  = []
    ok       = []
    excluded = []
    unknown  = []

    for code, nom, query, params_str in rows:
        query = query or ""
        params_str = params_str or ""
        cat = classify(query)

        if cat == 'already_ok':
            ok.append(code)
            print("[OK]      {} - deja corrige".format(code))

        elif cat == 'exercice':
            excluded.append(code)
            print("[EXCLUDE] {} - rapport comptable annuel ([Exercice]), pas de filtre mois".format(code))

        elif cat == 'fixable':
            new_query, fields = inject_month_filter(query)
            new_params = ensure_datedebut_in_params(params_str)

            print("[FIX]     {}".format(code))
            print("          Champ(s) date : {}".format(fields))

            if DRY_RUN:
                where_idx = new_query.upper().find("WHERE")
                if where_idx >= 0:
                    snippet = new_query[where_idx:where_idx+350].strip()
                    for line in snippet.split('\n')[:8]:
                        print("          {}".format(line))
            else:
                cur.execute(
                    "UPDATE APP_DataSources_Templates SET query_template=?, parameters=? WHERE code=?",
                    (new_query, new_params, code)
                )
                print("          -> {} ligne(s) mise(s) a jour".format(cur.rowcount))

            updated.append(code)
            print()

        else:  # unknown
            unknown.append(code)
            print("[SKIP]    {} - pattern YEAR(@dateFin) non standard (verif manuelle)".format(code))

    conn.close()

    # Résumé
    print()
    print("=" * 70)
    print("  RESUME")
    print("=" * 70)
    print("  Corrige(s)   : {}".format(len(updated)))
    print("  Deja OK      : {}".format(len(ok)))
    print("  Exclure(s)   : {} (rapports comptables annuels)".format(len(excluded)))
    print("  Inconnu(s)   : {}".format(len(unknown)))

    if updated:
        print()
        print("  DataSources mis a jour :")
        for c in updated:
            print("    + {}".format(c))

    if unknown:
        print()
        print("  A verifier manuellement :")
        for c in unknown:
            print("    ? {}".format(c))

    if excluded:
        print()
        print("  Exclus (logique metier - annuel par exercice) :")
        for c in excluded:
            print("    - {}".format(c))

    print()
    if DRY_RUN:
        print("  Relancez sans --dry-run pour appliquer.")
    elif updated:
        print("  [OK] Correction appliquee. Actualisez les dashboards.")
    else:
        print("  Rien a corriger.")


if __name__ == "__main__":
    run()
