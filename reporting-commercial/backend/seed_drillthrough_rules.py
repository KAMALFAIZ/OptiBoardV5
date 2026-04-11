"""
Seed script — Règles drill-through métier pour OptiBoard
=========================================================
Insère un ensemble complet de règles de navigation inter-rapports
basées sur la logique métier ERP commercial (Sage-like).

Usage:
    python seed_drillthrough_rules.py [--dry-run] [--skip-dynamic]

Options:
    --dry-run       Affiche les règles sans les insérer
    --skip-dynamic  Ne recherche pas les rapports dynamiques (GridView/Dashboard/Pivot)
    --reset         Supprime toutes les règles existantes avant d'insérer

Architecture des règles:
    - Fixed → Fixed  : pages singletons (pas d'ID)
    - Dynamic → Fixed: GridView/Dashboard/Pivot → pages fixes
    - Fixed → Dynamic: pages fixes → GridView/Dashboard/Pivot
    - Dynamic → Dyn. : entre GridViews/Dashboards/Pivots
"""

import sys
import json
import pyodbc
from typing import List, Dict, Optional, Tuple

# ── Connexion ──────────────────────────────────────────────────────────────────

CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;"
    "PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

# ── Règles fixes (Fixed → Fixed) ───────────────────────────────────────────────
# Format: (nom, source_type, source_column, target_type, target_filter_field, label)

FIXED_TO_FIXED_RULES: List[Tuple] = [

    # ── DIMENSION CLIENT ───────────────────────────────────────────────────────

    # Ventes (page ventes) → Fiche Client
    ("Ventes → Fiche Client",
     "ventes", "code_client",
     "fiche_client", "CT_Num",
     "Voir la fiche client"),

    # Ventes → Liste des ventes filtrée par client
    ("Ventes → Liste Ventes (Client)",
     "ventes", "code_client",
     "liste_ventes", "client",
     "Voir toutes les ventes du client"),

    # Ventes → Recouvrement client
    ("Ventes → Recouvrement Client",
     "ventes", "code_client",
     "recouvrement", "client",
     "Voir le recouvrement du client"),

    # Liste Ventes → Fiche Client
    ("Liste Ventes → Fiche Client",
     "liste_ventes", "client",
     "fiche_client", "CT_Num",
     "Voir la fiche client"),

    # Liste Ventes → Recouvrement
    ("Liste Ventes → Recouvrement",
     "liste_ventes", "client",
     "recouvrement", "client",
     "Voir le recouvrement"),

    # Liste Ventes → Analyse CA & Créances
    ("Liste Ventes → Analyse CA/Créances",
     "liste_ventes", "client",
     "analyse_ca_creances", "client",
     "Voir l'analyse CA & créances"),

    # Recouvrement → Fiche Client
    ("Recouvrement → Fiche Client",
     "recouvrement", "client",
     "fiche_client", "CT_Num",
     "Voir la fiche client"),

    # Recouvrement → Liste des ventes
    ("Recouvrement → Liste Ventes",
     "recouvrement", "client",
     "liste_ventes", "client",
     "Voir les ventes du client"),

    # Recouvrement → Analyse CA & Créances
    ("Recouvrement → Analyse CA/Créances",
     "recouvrement", "client",
     "analyse_ca_creances", "client",
     "Voir l'analyse CA & créances"),

    # Analyse CA & Créances → Fiche Client
    ("Analyse CA/Créances → Fiche Client",
     "analyse_ca_creances", "client",
     "fiche_client", "CT_Num",
     "Voir la fiche client"),

    # Analyse CA & Créances → Liste Ventes
    ("Analyse CA/Créances → Liste Ventes",
     "analyse_ca_creances", "client",
     "liste_ventes", "client",
     "Voir toutes les ventes"),

    # Analyse CA & Créances → Recouvrement
    ("Analyse CA/Créances → Recouvrement",
     "analyse_ca_creances", "client",
     "recouvrement", "client",
     "Voir le recouvrement"),

    # ── DIMENSION COMMERCIAL ───────────────────────────────────────────────────

    # Ventes → Analyse CA & Créances (par commercial)
    ("Ventes → CA Commercial",
     "ventes", "commercial",
     "analyse_ca_creances", "commercial",
     "Voir le CA du commercial"),

    # Ventes → Liste Ventes (par commercial)
    ("Ventes → Liste Ventes (Commercial)",
     "ventes", "commercial",
     "liste_ventes", "commercial",
     "Voir les ventes du commercial"),

    # Recouvrement → Liste Ventes (par commercial)
    ("Recouvrement → Ventes Commercial",
     "recouvrement", "commercial",
     "liste_ventes", "commercial",
     "Voir les ventes du commercial"),

    # Recouvrement → Analyse CA (par commercial)
    ("Recouvrement → CA Commercial",
     "recouvrement", "commercial",
     "analyse_ca_creances", "commercial",
     "Voir l'analyse CA du commercial"),

    # Analyse CA Créances → Liste Ventes (par commercial)
    ("Analyse CA/Créances → Liste Ventes (Commercial)",
     "analyse_ca_creances", "commercial",
     "liste_ventes", "commercial",
     "Voir les ventes du commercial"),

    # ── DIMENSION ARTICLE / GAMME ──────────────────────────────────────────────

    # Ventes → Stocks (par article)
    ("Ventes → Stock Article",
     "ventes", "code_article",
     "stocks", "code_article",
     "Voir le stock de l'article"),

    # Ventes → Liste Ventes (par article)
    ("Ventes → Liste Ventes (Article)",
     "ventes", "code_article",
     "liste_ventes", "code_article",
     "Voir toutes les ventes de l'article"),

    # Ventes → Stocks (par gamme)
    ("Ventes → Stocks (Gamme)",
     "ventes", "gamme",
     "stocks", "gamme",
     "Voir les stocks de la gamme"),

    # Stocks → Liste Ventes (par article)
    ("Stocks → Liste Ventes (Article)",
     "stocks", "code_article",
     "liste_ventes", "code_article",
     "Voir les ventes de l'article"),

    # Stocks → Liste Ventes (par gamme)
    ("Stocks → Liste Ventes (Gamme)",
     "stocks", "gamme",
     "liste_ventes", "gamme",
     "Voir les ventes de la gamme"),

    # Liste Ventes → Stocks (par article)
    ("Liste Ventes → Stock Article",
     "liste_ventes", "code_article",
     "stocks", "code_article",
     "Voir le stock de l'article"),

    # ── DIMENSION FOURNISSEUR ──────────────────────────────────────────────────

    # Stocks → Fiche Fournisseur
    ("Stocks → Fiche Fournisseur",
     "stocks", "code_fournisseur",
     "fiche_fournisseur", "CT_Num",
     "Voir la fiche fournisseur"),

    # Ventes → Fiche Fournisseur (pour les achats/retours)
    ("Ventes → Fiche Fournisseur",
     "ventes", "code_fournisseur",
     "fiche_fournisseur", "CT_Num",
     "Voir la fiche fournisseur"),

    # Liste Ventes → Fiche Fournisseur
    ("Liste Ventes → Fiche Fournisseur",
     "liste_ventes", "fournisseur",
     "fiche_fournisseur", "CT_Num",
     "Voir la fiche fournisseur"),

    # ── COMPTABILITÉ ──────────────────────────────────────────────────────────

    # Comptabilité → Fiche Client (par tiers)
    ("Comptabilité → Fiche Client",
     "comptabilite", "tiers",
     "fiche_client", "CT_Num",
     "Voir la fiche client"),

    # Comptabilité → Fiche Fournisseur (par tiers)
    ("Comptabilité → Fiche Fournisseur",
     "comptabilite", "tiers",
     "fiche_fournisseur", "CT_Num",
     "Voir la fiche fournisseur"),

    # Comptabilité → Liste Ventes (par tiers)
    ("Comptabilité → Liste Ventes",
     "comptabilite", "tiers",
     "liste_ventes", "client",
     "Voir les ventes du tiers"),

    # Comptabilité → Recouvrement (par tiers)
    ("Comptabilité → Recouvrement",
     "comptabilite", "tiers",
     "recouvrement", "client",
     "Voir le recouvrement du tiers"),

    # ── FICHE CLIENT → autres pages ───────────────────────────────────────────

    # Fiche Client → Liste Ventes
    ("Fiche Client → Liste Ventes",
     "fiche_client", "CT_Num",
     "liste_ventes", "client",
     "Voir toutes les ventes"),

    # Fiche Client → Recouvrement
    ("Fiche Client → Recouvrement",
     "fiche_client", "CT_Num",
     "recouvrement", "client",
     "Voir le recouvrement"),

    # Fiche Client → Analyse CA & Créances
    ("Fiche Client → Analyse CA/Créances",
     "fiche_client", "CT_Num",
     "analyse_ca_creances", "client",
     "Voir l'analyse CA & créances"),

    # Fiche Client → Comptabilité (balance tiers)
    ("Fiche Client → Comptabilité",
     "fiche_client", "CT_Num",
     "comptabilite", "tiers",
     "Voir les écritures comptables"),

    # ── FICHE FOURNISSEUR → autres pages ──────────────────────────────────────

    # Fiche Fournisseur → Stocks
    ("Fiche Fournisseur → Stocks",
     "fiche_fournisseur", "CT_Num",
     "stocks", "code_fournisseur",
     "Voir les stocks du fournisseur"),

    # Fiche Fournisseur → Comptabilité
    ("Fiche Fournisseur → Comptabilité",
     "fiche_fournisseur", "CT_Num",
     "comptabilite", "tiers",
     "Voir les écritures comptables"),
]

# ── Colonnes pilotes pour détection automatique dans les rapports dynamiques ───
# Si un rapport dynamique (GridView/Dashboard/Pivot) contient ces colonnes,
# les règles correspondantes sont créées automatiquement.

DYNAMIC_COLUMN_RULES = [
    # (source_column, target_type, target_id, target_filter_field, label_template)
    # target_id = 0 → page fixe
    ("client",          "fiche_client",        0, "CT_Num",        "Voir la fiche client"),
    ("code_client",     "fiche_client",        0, "CT_Num",        "Voir la fiche client"),
    ("CT_Num",          "fiche_client",        0, "CT_Num",        "Voir la fiche client"),
    ("nom_client",      "fiche_client",        0, "CT_Num",        "Voir la fiche client"),

    ("client",          "liste_ventes",        0, "client",        "Voir les ventes du client"),
    ("code_client",     "liste_ventes",        0, "client",        "Voir les ventes du client"),

    ("client",          "recouvrement",        0, "client",        "Voir le recouvrement"),
    ("code_client",     "recouvrement",        0, "client",        "Voir le recouvrement"),

    ("fournisseur",     "fiche_fournisseur",   0, "CT_Num",        "Voir la fiche fournisseur"),
    ("code_fournisseur","fiche_fournisseur",   0, "CT_Num",        "Voir la fiche fournisseur"),

    ("code_article",    "stocks",              0, "code_article",  "Voir le stock"),
    ("code_article",    "liste_ventes",        0, "code_article",  "Voir les ventes de l'article"),

    ("gamme",           "stocks",              0, "gamme",         "Voir les stocks de la gamme"),
    ("gamme",           "liste_ventes",        0, "gamme",         "Voir les ventes de la gamme"),

    ("commercial",      "analyse_ca_creances", 0, "commercial",    "Voir le CA du commercial"),
    ("commercial",      "liste_ventes",        0, "commercial",    "Voir les ventes du commercial"),
]


# ── Utilitaires ────────────────────────────────────────────────────────────────

def get_connection():
    return pyodbc.connect(CONN_STRING)


def init_table(cur):
    cur.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_DrillThrough')
    CREATE TABLE APP_DrillThrough (
        id                  INT IDENTITY(1,1) PRIMARY KEY,
        nom                 NVARCHAR(255)   NOT NULL,
        source_type         NVARCHAR(50)    NOT NULL,
        source_id           INT             NOT NULL,
        source_column       NVARCHAR(255)   NOT NULL,
        target_type         NVARCHAR(50)    NOT NULL,
        target_id           INT             NOT NULL,
        target_filter_field NVARCHAR(255)   NOT NULL,
        label               NVARCHAR(255),
        is_active           BIT             NOT NULL DEFAULT 1,
        created_at          DATETIME        DEFAULT GETDATE(),
        updated_at          DATETIME        DEFAULT GETDATE()
    )
    """)


def rule_exists(cur, source_type, source_id, source_column, target_type, target_id) -> bool:
    cur.execute("""
        SELECT 1 FROM APP_DrillThrough
        WHERE source_type=? AND source_id=? AND source_column=?
          AND target_type=? AND target_id=?
    """, (source_type, source_id, source_column, target_type, target_id))
    return cur.fetchone() is not None


def insert_rule(cur, nom, source_type, source_id, source_column,
                target_type, target_id, target_filter_field, label):
    cur.execute("""
        INSERT INTO APP_DrillThrough
            (nom, source_type, source_id, source_column,
             target_type, target_id, target_filter_field, label, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (nom, source_type, source_id, source_column,
          target_type, target_id, target_filter_field, label or nom))


def get_dynamic_reports(cur) -> Dict[str, List[Dict]]:
    """Récupère tous les rapports dynamiques avec leur configuration de colonnes."""
    result = {"gridview": [], "dashboard": [], "pivot": []}

    # GridViews
    cur.execute("SELECT id, nom, columns_config FROM APP_GridViews")
    for row in cur.fetchall():
        cols = []
        if row[2]:
            try:
                cfg = json.loads(row[2])
                cols = [c.get("field", "") for c in cfg if c.get("field")]
            except Exception:
                pass
        result["gridview"].append({"id": row[0], "nom": row[1], "columns": cols})

    # Dashboards — pas de colonnes directes, on note juste leur existence
    cur.execute("SELECT id, nom FROM APP_Dashboards")
    for row in cur.fetchall():
        result["dashboard"].append({"id": row[0], "nom": row[1], "columns": []})

    # Pivots
    try:
        cur.execute("SELECT id, nom, config FROM APP_Pivots")
        for row in cur.fetchall():
            cols = []
            if row[2]:
                try:
                    cfg = json.loads(row[2])
                    # Colonnes lignes + colonnes valeurs
                    rows_cfg   = cfg.get("rows",   [])
                    values_cfg = cfg.get("values", [])
                    cols = [c.get("field", "") for c in rows_cfg + values_cfg if c.get("field")]
                except Exception:
                    pass
            result["pivot"].append({"id": row[0], "nom": row[1], "columns": cols})
    except Exception:
        pass  # APP_Pivots peut ne pas exister

    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    dry_run      = "--dry-run"      in sys.argv
    skip_dynamic = "--skip-dynamic" in sys.argv
    do_reset     = "--reset"        in sys.argv

    print("=" * 60)
    print("  OptiBoard — Seed Drill-Through Rules")
    print("=" * 60)
    if dry_run:
        print("  MODE DRY-RUN : aucune écriture en base\n")

    conn = get_connection()
    cur  = conn.cursor()

    init_table(cur)
    conn.commit()

    if do_reset:
        count_before = cur.execute("SELECT COUNT(*) FROM APP_DrillThrough").fetchone()[0]
        if not dry_run:
            cur.execute("DELETE FROM APP_DrillThrough")
            conn.commit()
        print(f"  RESET : {count_before} règle(s) supprimée(s)\n")

    inserted = 0
    skipped  = 0

    # ── 1. Règles Fixed → Fixed ─────────────────────────────────────────────
    print("── Règles Fixed → Fixed ──────────────────────────────────────────")
    for (nom, src_type, src_col, tgt_type, tgt_field, label) in FIXED_TO_FIXED_RULES:
        exists = rule_exists(cur, src_type, 0, src_col, tgt_type, 0)
        if exists:
            print(f"  SKIP  {nom}")
            skipped += 1
        else:
            print(f"  ADD   {nom}")
            if not dry_run:
                insert_rule(cur, nom, src_type, 0, src_col, tgt_type, 0, tgt_field, label)
            inserted += 1

    # ── 2. Règles Dynamic → Fixed (auto-détection par colonnes) ────────────
    if not skip_dynamic:
        print("\n── Règles Dynamic → Fixed (auto-détection) ───────────────────")
        dynamic = get_dynamic_reports(cur)

        for rtype, reports in dynamic.items():
            for report in reports:
                rid   = report["id"]
                rnom  = report["nom"]
                rcols = set(report["columns"])

                for (src_col, tgt_type, tgt_id, tgt_field, label_tpl) in DYNAMIC_COLUMN_RULES:
                    if src_col not in rcols:
                        continue

                    nom = f"{rnom} ({src_col}) → {tgt_type.replace('_', ' ').title()}"
                    exists = rule_exists(cur, rtype, rid, src_col, tgt_type, tgt_id)
                    if exists:
                        print(f"  SKIP  [{rtype}:{rid}] {nom}")
                        skipped += 1
                    else:
                        print(f"  ADD   [{rtype}:{rid}] {nom}")
                        if not dry_run:
                            insert_rule(cur, nom, rtype, rid, src_col,
                                        tgt_type, tgt_id, tgt_field, label_tpl)
                        inserted += 1

    if not dry_run:
        conn.commit()

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print(f"  Résultat : {inserted} règle(s) ajoutée(s), {skipped} déjà présente(s)")
    print("=" * 60)


if __name__ == "__main__":
    main()
