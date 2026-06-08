"""
Export OptiBoard_SaaS → fichiers SQL versionnables sur GitHub
=============================================================
Usage :
  python export_db.py                  → export complet
  python export_db.py --tables menus   → export d'une seule table

Génère dans backend/sql/exports/ :
  - schema_central.sql     → CREATE TABLE de toutes les tables
  - data_menus.sql         → INSERT des menus maîtres
  - data_gridviews.sql     → INSERT des gridviews templates
  - data_pivots.sql        → INSERT des pivots templates
  - data_dashboards.sql    → INSERT des dashboards templates
  - data_datasources.sql   → INSERT des datasources templates
  - data_users.sql         → INSERT des utilisateurs (sans mots de passe)
  - data_dwh.sql           → INSERT des clients DWH (sans mots de passe)
"""

import pyodbc
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# ── Connexion (lue depuis .env si dispo) ─────────────────────────────────────
def _get_env():
    env = {}
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

env = _get_env()

SERVER   = env.get("DB_SERVER",   "kasoft.selfip.net")
DATABASE = env.get("DB_NAME",     "OptiBoard_SaaS")
USER     = env.get("DB_USER",     "sa")
PASSWORD = env.get("DB_PASSWORD", "")

CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};DATABASE={DATABASE};"
    f"UID={USER};PWD={PASSWORD};"
    f"TrustServerCertificate=yes;"
)

OUTPUT_DIR = Path(__file__).parent / "exports"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Tables à exporter (schéma + données) ─────────────────────────────────────
TABLES_DATA = [
    {
        "name":  "menus",
        "table": "APP_Menus",
        "order": "ordre, id",
        "exclude_cols": [],          # aucune colonne exclue
    },
    {
        "name":  "gridviews",
        "table": "APP_GridViews_Templates",
        "order": "nom",
        "exclude_cols": [],
    },
    {
        "name":  "pivots",
        "table": "APP_Pivots_Templates",
        "order": "nom",
        "exclude_cols": [],
    },
    {
        "name":  "dashboards",
        "table": "APP_Dashboards_Templates",
        "order": "nom",
        "exclude_cols": [],
    },
    {
        "name":  "datasources",
        "table": "APP_DataSources_Templates",
        "order": "nom",
        "exclude_cols": [],
    },
    {
        "name":  "users",
        "table": "APP_Users",
        "order": "id",
        # Exclure les mots de passe pour ne pas les versionner sur GitHub
        "exclude_cols": ["password_hash", "mot_de_passe", "password"],
    },
    {
        "name":  "dwh",
        "table": "APP_DWH",
        "order": "code",
        # Exclure les credentials des bases clients
        "exclude_cols": ["password_dwh", "user_dwh", "password_optiboard", "user_optiboard"],
    },
    {
        "name":  "roles",
        "table": "APP_Roles",
        "order": "id",
        "exclude_cols": [],
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def escape_sql(val):
    """Échappe une valeur pour un INSERT SQL."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return str(val)
    if isinstance(val, datetime):
        return f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'"
    # String : échapper les apostrophes
    s = str(val).replace("'", "''")
    return f"N'{s}'"


def get_columns(cursor, table_name, exclude_cols=None):
    """Retourne la liste des colonnes d'une table."""
    exclude_cols = [c.lower() for c in (exclude_cols or [])]
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
        (table_name,)
    )
    return [row[0] for row in cursor.fetchall()
            if row[0].lower() not in exclude_cols]


def table_exists(cursor, table_name):
    cursor.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?",
        (table_name,)
    )
    return cursor.fetchone()[0] > 0


def export_data(cursor, table_cfg):
    """Génère les instructions INSERT pour une table."""
    table  = table_cfg["table"]
    name   = table_cfg["name"]
    order  = table_cfg.get("order", "id")
    excl   = table_cfg.get("exclude_cols", [])

    if not table_exists(cursor, table):
        print(f"  [SKIP] Table {table} absente dans la base")
        return

    cols = get_columns(cursor, table, excl)
    if not cols:
        print(f"  [SKIP] Table {table} : aucune colonne")
        return

    cols_str = ", ".join(f"[{c}]" for c in cols)
    cursor.execute(f"SELECT {cols_str} FROM [{table}] ORDER BY {order}")
    rows = cursor.fetchall()

    out_path = OUTPUT_DIR / f"data_{name}.sql"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"-- ============================================================\n")
        f.write(f"-- Export : {table}\n")
        f.write(f"-- Génère le : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- Lignes    : {len(rows)}\n")
        f.write(f"-- ============================================================\n\n")
        f.write(f"SET IDENTITY_INSERT [{table}] ON;\n")
        f.write(f"GO\n\n")

        # Vider la table avant de réinsérer (pour un export propre)
        f.write(f"-- Vider la table avant import\n")
        f.write(f"DELETE FROM [{table}];\n")
        f.write(f"GO\n\n")

        for row in rows:
            values = ", ".join(escape_sql(v) for v in row)
            f.write(
                f"INSERT INTO [{table}] ({cols_str})\n"
                f"VALUES ({values});\n"
            )

        f.write(f"\nSET IDENTITY_INSERT [{table}] OFF;\n")
        f.write(f"GO\n")

    print(f"  ✓ {table} → {out_path.name}  ({len(rows)} lignes)")


def export_schema(cursor):
    """Génère un fichier avec les noms et colonnes de toutes les tables."""
    out_path = OUTPUT_DIR / "schema_central.sql"
    cursor.execute(
        """SELECT t.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE,
                  c.CHARACTER_MAXIMUM_LENGTH, c.IS_NULLABLE, c.COLUMN_DEFAULT
           FROM INFORMATION_SCHEMA.TABLES t
           JOIN INFORMATION_SCHEMA.COLUMNS c ON c.TABLE_NAME = t.TABLE_NAME
           WHERE t.TABLE_TYPE = 'BASE TABLE'
             AND t.TABLE_NAME NOT LIKE 'sys%'
             AND t.TABLE_NAME NOT LIKE 'MS%'
           ORDER BY t.TABLE_NAME, c.ORDINAL_POSITION"""
    )
    rows = cursor.fetchall()

    current_table = None
    lines = [
        f"-- Schema OptiBoard_SaaS\n",
        f"-- Exporté le : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"-- Serveur    : {SERVER}\n\n",
    ]

    for row in rows:
        tbl, col, dtype, maxlen, nullable, default = row
        if tbl != current_table:
            if current_table is not None:
                lines.append(");\nGO\n\n")
            lines.append(f"-- Table : {tbl}\n")
            lines.append(f"IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{tbl}' AND xtype='U')\n")
            lines.append(f"CREATE TABLE [{tbl}] (\n")
            current_table = tbl
        else:
            lines[-1] = lines[-1].rstrip() + ",\n"

        length = f"({maxlen})" if maxlen and maxlen != -1 else ("(MAX)" if maxlen == -1 else "")
        null_str = "NULL" if nullable == "YES" else "NOT NULL"
        default_str = f" DEFAULT {default}" if default else ""
        lines.append(f"    [{col}] {dtype.upper()}{length} {null_str}{default_str}\n")

    if current_table:
        lines.append(");\nGO\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  ✓ Schéma → {out_path.name}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Export OptiBoard_SaaS → SQL")
    parser.add_argument("--tables", nargs="*", help="Limiter à certaines tables (ex: menus gridviews)")
    args = parser.parse_args()

    filter_tables = args.tables or []

    print(f"\n{'='*55}")
    print(f"  Export OptiBoard_SaaS → GitHub")
    print(f"  Serveur : {SERVER} / Base : {DATABASE}")
    print(f"  Dossier : {OUTPUT_DIR}")
    print(f"{'='*55}\n")

    try:
        conn   = pyodbc.connect(CONN_STR, timeout=15)
        cursor = conn.cursor()
        print("✓ Connexion SQL Server OK\n")
    except Exception as e:
        print(f"✗ Connexion échouée : {e}")
        sys.exit(1)

    # Export schéma
    if not filter_tables:
        print("── Schéma ──────────────────────────────────")
        export_schema(cursor)

    # Export données
    print("\n── Données ─────────────────────────────────")
    for tbl_cfg in TABLES_DATA:
        if filter_tables and tbl_cfg["name"] not in filter_tables:
            continue
        export_data(cursor, tbl_cfg)

    conn.close()

    print(f"\n✓ Export terminé → {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
