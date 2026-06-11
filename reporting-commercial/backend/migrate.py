#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate.py — Runner de migrations SQL versionnees pour OptiBoard.

Cible : base CENTRALE (OptiBoard_SaaS), connexion via app.database_unified.
Source : app/sql/migrations/*.sql (UNIQUEMENT ce repertoire — les schemas
001-003 de app/sql/ sont l'initialisation faite par setup.py, hors perimetre).

Usage :
    python migrate.py              Applique les migrations pendantes
    python migrate.py --dry-run    Liste ce qui serait fait, sans rien executer
    python migrate.py --baseline   Enregistre les migrations pendantes comme
                                   deja appliquees SANS les executer (pour les
                                   installations existantes ou le SQL a deja
                                   ete passe a la main)

Fonctionnement :
- Les fichiers sont appliques dans l'ordre lexicographique de leur nom
  (d'ou la convention NNN_description.sql).
- Tracking dans la table dbo.APP_Migrations de la base centrale
  (name PK, hash SHA-256, applied_at). Creee automatiquement si absente.
- Le hash est calcule sur le contenu UTF-8 avec fins de ligne normalisees
  (CRLF -> LF) pour etre stable entre Windows et Linux.
- Une migration deja appliquee dont le hash a change => ERREUR et arret :
  il est interdit de modifier une migration appliquee ; creer une nouvelle
  migration a la place.
- Execution : le script est decoupe sur les lignes 'GO' (separateur de batch
  T-SQL : insensible a la casse, seul sur sa ligne, eventuellement suivi d'un
  nombre — le compteur de repetition est ignore, traite comme simple
  separateur). Les batchs sont executes sequentiellement sur la MEME connexion
  (autocommit=False) ; commit unique apres succes de TOUS les batchs du
  fichier, rollback du fichier entier si un batch echoue.
  LIMITE : certaines instructions SQL Server ne peuvent pas s'executer dans
  une transaction (CREATE/ALTER DATABASE, BACKUP, ...) — voir
  docs/MIGRATIONS.md.

Exit code : 0 si tout est OK, 1 en cas d'erreur.
"""

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BACKEND_DIR / "app" / "sql" / "migrations"

# Permet de lancer le script depuis n'importe quel repertoire courant
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ligne 'GO' T-SQL : seule sur sa ligne, insensible a la casse,
# eventuellement suivie d'un nombre (GO 5)
GO_LINE_RE = re.compile(r"^\s*GO(?:\s+\d+)?\s*$", re.IGNORECASE)

TRACKING_TABLE_DDL = """
IF OBJECT_ID('dbo.APP_Migrations', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.APP_Migrations (
        name        NVARCHAR(255) NOT NULL PRIMARY KEY,
        hash        NVARCHAR(64)  NOT NULL,
        applied_at  DATETIME      NOT NULL DEFAULT GETDATE()
    );
END
"""


# =====================================================
# Lecture / hash / decoupage des fichiers
# =====================================================

def read_migration(path: Path) -> str:
    """Lit un fichier .sql en UTF-8 (BOM tolere) et normalise CRLF -> LF."""
    text = path.read_bytes().decode("utf-8-sig")
    return text.replace("\r\n", "\n")


def compute_hash(normalized_text: str) -> str:
    """SHA-256 du contenu normalise (stable Windows/Linux)."""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


def split_batches(sql_text: str) -> list:
    """Decoupe un script T-SQL en batchs sur les lignes GO.

    Les batchs vides (ou ne contenant que du blanc) sont ignores.
    """
    batches, current = [], []
    for line in sql_text.split("\n"):
        if GO_LINE_RE.match(line):
            batch = "\n".join(current)
            if batch.strip():
                batches.append(batch)
            current = []
        else:
            current.append(line)
    batch = "\n".join(current)
    if batch.strip():
        batches.append(batch)
    return batches


# =====================================================
# Acces base centrale
# =====================================================

def open_central_connection():
    """Ouvre une connexion centrale en mode transactionnel (autocommit=False).

    Le timeout requete par defaut (SQL_QUERY_TIMEOUT=60s) est leve : une
    migration (CREATE INDEX volumineux...) peut legitimement durer plus
    longtemps. Surcharger via MIGRATION_QUERY_TIMEOUT si besoin (0 = illimite).
    """
    from app.database_unified import get_central_connection
    conn = get_central_connection()
    conn.autocommit = False
    try:
        conn.timeout = int(os.environ.get("MIGRATION_QUERY_TIMEOUT", "0") or 0)
    except Exception:
        pass
    return conn


def tracking_table_exists(conn) -> bool:
    row = conn.cursor().execute(
        "SELECT OBJECT_ID('dbo.APP_Migrations', 'U')"
    ).fetchone()
    return row is not None and row[0] is not None


def ensure_tracking_table(conn) -> None:
    cur = conn.cursor()
    cur.execute(TRACKING_TABLE_DDL)
    conn.commit()


def load_applied(conn) -> dict:
    """Retourne {name: hash} des migrations deja enregistrees."""
    cur = conn.cursor()
    cur.execute("SELECT name, hash FROM dbo.APP_Migrations")
    return {row[0]: row[1] for row in cur.fetchall()}


def record_migration(conn, name: str, file_hash: str) -> None:
    """Enregistre la migration dans APP_Migrations (sans commit)."""
    conn.cursor().execute(
        "INSERT INTO dbo.APP_Migrations (name, hash) VALUES (?, ?)",
        name, file_hash,
    )


def apply_migration(conn, name: str, sql_text: str, file_hash: str) -> int:
    """Execute tous les batchs du fichier puis enregistre la migration.

    Commit unique si tout reussit (l'INSERT de tracking fait partie de la
    meme transaction). Rollback du fichier entier si un batch echoue.
    Retourne le nombre de batchs executes.
    """
    batches = split_batches(sql_text)
    cur = conn.cursor()
    for i, batch in enumerate(batches, 1):
        try:
            cur.execute(batch)
            # Consomme tous les result sets : les erreurs d'instructions
            # situees apres un SELECT dans le meme batch ne remontent
            # qu'au parcours des result sets suivants.
            while cur.nextset():
                pass
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            raise RuntimeError(
                f"echec au batch {i}/{len(batches)} : {exc}"
            ) from exc
    record_migration(conn, name, file_hash)
    conn.commit()
    return len(batches)


# =====================================================
# Programme principal
# =====================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Runner de migrations SQL versionnees (base centrale OptiBoard).",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true",
        help="liste ce qui serait applique/skippe/en erreur sans rien executer",
    )
    mode.add_argument(
        "--baseline", action="store_true",
        help="enregistre les migrations pendantes dans APP_Migrations SANS les "
             "executer (installations existantes ou le SQL a deja ete passe)",
    )
    return parser


def main() -> int:
    # Evite un crash UnicodeEncodeError sur les consoles Windows cp850/cp1252
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass

    args = build_parser().parse_args()
    mode = "dry-run" if args.dry_run else ("baseline" if args.baseline else "apply")

    if not MIGRATIONS_DIR.is_dir():
        print(f"[ERROR]    Repertoire des migrations introuvable : {MIGRATIONS_DIR}")
        return 1

    files = sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: p.name)
    if not files:
        print(f"Aucune migration trouvee dans {MIGRATIONS_DIR} — rien a faire.")
        return 0

    # Import tardif : message clair si l'environnement n'est pas pret
    try:
        from app.database_unified import DatabaseNotConfiguredError
    except Exception as exc:
        print(f"[ERROR]    Import de app.database_unified impossible : {exc}")
        return 1

    try:
        conn = open_central_connection()
    except DatabaseNotConfiguredError as exc:
        print(f"[ERROR]    Base centrale non configuree : {exc}")
        return 1
    except Exception as exc:
        print(f"[ERROR]    Connexion a la base centrale impossible : {exc}")
        return 1

    try:
        from app.config_multitenant import get_central_settings
        s = get_central_settings()
        target = f"{s._effective_server} / {s._effective_name}"
    except Exception:
        target = "(base centrale)"

    print(f"Migrations : {MIGRATIONS_DIR}")
    print(f"Cible      : {target}")
    print(f"Mode       : {mode}")
    print("-" * 72)

    counts = {"applied": 0, "skip": 0, "baseline": 0, "pending": 0, "error": 0}

    try:
        if args.dry_run:
            # Lecture seule : si la table de tracking n'existe pas encore,
            # on ne la cree pas — on considere qu'aucune migration n'est appliquee.
            applied = load_applied(conn) if tracking_table_exists(conn) else {}
        else:
            ensure_tracking_table(conn)
            applied = load_applied(conn)

        for path in files:
            name = path.name
            sql_text = read_migration(path)
            file_hash = compute_hash(sql_text)

            # --- Deja enregistree ---
            if name in applied:
                if applied[name] == file_hash:
                    print(f"[SKIP]     {name} (deja appliquee)")
                    counts["skip"] += 1
                    continue
                counts["error"] += 1
                print(
                    f"[ERROR]    {name} : le fichier a ete MODIFIE apres son "
                    f"application (hash enregistre {applied[name][:12]}..., "
                    f"hash actuel {file_hash[:12]}...).\n"
                    f"           Modifier une migration appliquee est interdit : "
                    f"creez une NOUVELLE migration (ex: NNN_fix_{name[4:] if len(name) > 4 else name}) "
                    f"avec les correctifs."
                )
                if args.dry_run:
                    continue  # en dry-run on liste tout, l'erreur reste fatale a la fin
                break  # apply/baseline : arret immediat

            # --- Pendante ---
            if args.dry_run:
                nb = len(split_batches(sql_text))
                print(f"[PENDING]  {name} (serait appliquee - {nb} batch(s))")
                counts["pending"] += 1
            elif args.baseline:
                record_migration(conn, name, file_hash)
                conn.commit()
                print(f"[BASELINE] {name} (enregistree sans execution)")
                counts["baseline"] += 1
            else:
                t0 = time.time()
                try:
                    nb = apply_migration(conn, name, sql_text, file_hash)
                except Exception as exc:
                    counts["error"] += 1
                    print(f"[ERROR]    {name} : {exc}")
                    print("           Rollback du fichier effectue — arret.")
                    break
                print(f"[APPLIED]  {name} ({nb} batch(s), {time.time() - t0:.2f}s)")
                counts["applied"] += 1
    finally:
        try:
            conn.close()
        except Exception:
            pass

    print("-" * 72)
    summary = []
    if counts["applied"]:
        summary.append(f"{counts['applied']} appliquee(s)")
    if counts["baseline"]:
        summary.append(f"{counts['baseline']} baselinee(s)")
    if counts["pending"]:
        summary.append(f"{counts['pending']} en attente")
    if counts["skip"]:
        summary.append(f"{counts['skip']} deja appliquee(s)")
    if counts["error"]:
        summary.append(f"{counts['error']} erreur(s)")
    print("Resume     : " + (", ".join(summary) if summary else "rien a faire"))

    if counts["error"]:
        print("Statut     : ECHEC")
        return 1
    print("Statut     : OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
