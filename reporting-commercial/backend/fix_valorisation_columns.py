"""
FIX Méthode de valorisation — Marge Globale et toutes les datasources CA
Remplace les anciennes options (CMUP/DPA-Vente/DPR-Vente) par les vraies colonnes
de Lignes_des_ventes : Prix de revient, CMUP, Dernier Prix d'achat, Prix d'achat, Coût standard
"""
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8')
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database_unified import get_central_connection

# ─────────────────────────────────────────────────────────────
# Nouveaux paramètres Valorisation
# ─────────────────────────────────────────────────────────────
NEW_OPTIONS   = ["Prix de revient", "CMUP", "Dernier Prix d'achat", "Prix d'achat", "Coût standard"]
NEW_DEFAULT   = "Prix de revient"

# ─────────────────────────────────────────────────────────────
# Regex pour le vieux CASE @Valorisation (n'importe quelle indentation)
# ─────────────────────────────────────────────────────────────
OLD_CASE_RE = re.compile(
    r"CASE @Valorisation\s+"
    r"WHEN 'CMUP' THEN l\.CMUP\s+"
    r"WHEN 'CMUP' THEN l\.\[CMUP\]\s+"
    r"WHEN 'DPA-Vente' THEN ms\.\[DPA-Vente\]\s+"
    r"WHEN 'DPA-Période' THEN ms\.\[DPA-Période\]\s+"
    r"WHEN 'DPR-Vente' THEN ms\.\[DPR-Vente\]\s+"
    r"ELSE 0\s+"
    r"END",
    re.IGNORECASE
)

def build_new_case(indent="                        "):
    return (
        f"CASE @Valorisation\n"
        f"{indent}    WHEN 'Prix de revient'      THEN l.[Prix de revient]\n"
        f"{indent}    WHEN 'CMUP'                 THEN l.[CMUP]\n"
        f"{indent}    WHEN 'Dernier Prix d''achat' THEN l.[Dernier Prix d''achat]\n"
        f"{indent}    WHEN 'Prix d''achat'         THEN l.[Prix d''achat]\n"
        f"{indent}    WHEN 'Coût standard'         THEN l.[Coût standard]\n"
        f"{indent}    ELSE 0\n"
        f"{indent}END"
    )

# ─────────────────────────────────────────────────────────────
# Supprimer le LEFT JOIN Mouvement_stock et les colonnes DPA/DPR
# ─────────────────────────────────────────────────────────────
MS_JOIN_RE = re.compile(
    r"\s*LEFT JOIN Mouvement_stock AS ms\s+"
    r"ON l\.societe = ms\.societe AND l\.\[N° interne\] = ms\.\[N° interne\]",
    re.IGNORECASE
)

# Colonnes DPA/DPR dans SELECT (DS_CA_MARGE_DYNAMIQUE uniquement)
DPA_SELECT_RE = re.compile(
    r",?\s*ISNULL\(ms\.\[DPA-Période\],\s*0\) AS \[DPA-Période\],?\s*"
    r"ISNULL\(ms\.\[DPA-Vente\],\s*0\) AS \[DPA-Vente\],?\s*"
    r"ISNULL\(ms\.\[DPR-Vente\],\s*0\) AS \[DPR-Vente\],?\s*",
    re.IGNORECASE
)
# Aussi l.CMUP seul (doublon) dans SELECT
OLD_CMUP_DUP_RE = re.compile(r",?\s*l\.CMUP,\s*\n", re.IGNORECASE)

# ─────────────────────────────────────────────────────────────
# Datasources à corriger
# ─────────────────────────────────────────────────────────────
CODES = [
    'DS_CA_MARGE_DYNAMIQUE',
    'DS_CA_AGREGE_CLIENT',
    'DS_CA_AGREGE_ARTICLE',
    'DS_CA_AGREGE_CATALOGUE',
    'DS_CA_AGREGE_REPRESENTANT',
    'DS_CA_PAR_MOIS_DYNAMIQUE',
    'DS_CA_DETAIL_COMPLET',
]

conn = get_central_connection()
cur  = conn.cursor()

for code in CODES:
    cur.execute("SELECT id, query_template, parameters FROM APP_DataSources_Templates WHERE code=?", (code,))
    row = cur.fetchone()
    if not row:
        print(f"  [SKIP] {code} — introuvable")
        continue

    ds_id, query, params_raw = row
    new_query = query or ''
    params = json.loads(params_raw) if params_raw else []

    # ── 1. Détecter l'indentation réelle du CASE dans cette requête
    m = OLD_CASE_RE.search(new_query)
    if m:
        # Récupérer l'indentation de la ligne CASE
        line_start = new_query.rfind('\n', 0, m.start()) + 1
        raw_line   = new_query[line_start:m.start()]
        indent     = len(raw_line) - len(raw_line.lstrip())
        indent_str = ' ' * indent
        new_case   = build_new_case(indent_str)
        new_query  = OLD_CASE_RE.sub(new_case, new_query)
        print(f"  [{code}] CASE @Valorisation mis à jour")
    else:
        print(f"  [{code}] CASE @Valorisation non trouvé (déjà mis à jour ?)")

    # ── 2. Supprimer LEFT JOIN Mouvement_stock
    if MS_JOIN_RE.search(new_query):
        new_query = MS_JOIN_RE.sub('', new_query)
        print(f"  [{code}] LEFT JOIN Mouvement_stock supprimé")

    # ── 3. Supprimer colonnes DPA/DPR dans SELECT (DS_CA_MARGE_DYNAMIQUE)
    if DPA_SELECT_RE.search(new_query):
        new_query = DPA_SELECT_RE.sub('\n                ', new_query)
        print(f"  [{code}] Colonnes DPA/DPR supprimées du SELECT")

    # ── 4. Supprimer doublon l.CMUP dans SELECT
    if OLD_CMUP_DUP_RE.search(new_query):
        new_query = OLD_CMUP_DUP_RE.sub('\n', new_query)
        print(f"  [{code}] Doublon l.CMUP supprimé")

    # ── 5. Mettre à jour les paramètres Valorisation
    changed_params = False
    for p in params:
        if p.get('name') == 'Valorisation':
            p['options']  = NEW_OPTIONS
            p['default']  = NEW_DEFAULT
            changed_params = True
        # Garder label lisible
        if p.get('name') == 'Valorisation' and not p.get('label'):
            p['label'] = 'Méthode de valorisation'

    if changed_params:
        params_raw_new = json.dumps(params, ensure_ascii=False)
        print(f"  [{code}] Paramètres mis à jour : options={NEW_OPTIONS}")
    else:
        params_raw_new = params_raw

    # ── 6. Sauvegarder
    cur.execute(
        "UPDATE APP_DataSources_Templates SET query_template=?, parameters=? WHERE id=?",
        (new_query, params_raw_new, ds_id)
    )
    print(f"  [{code}] ✓ Sauvegardé (id={ds_id})")

conn.commit()
conn.close()
print("\n[DONE] Toutes les datasources marge ont été mises à jour.")
