"""
Migration : chiffre APP_ETL_Agents.sage_password au repos dans chaque base client.

Le backend chiffre déjà les nouvelles écritures (préfixe `$sec1$`, voir
`app/services/secret_crypto.py`) et déchiffre transparemment à la lecture ; ce script
convertit les valeurs déjà en base, restées en clair.

Idempotent : les valeurs déjà préfixées `$sec1$` sont ignorées. Aucune valeur vide
n'est touchée. Mode simulation par défaut — rien n'est écrit sans `--apply`.

Usage :
    python scripts/encrypt_etl_agent_secrets.py                 # simulation (toutes les bases)
    python scripts/encrypt_etl_agent_secrets.py --apply         # écrit
    python scripts/encrypt_etl_agent_secrets.py --dwh ALEAFOOD --apply

Les credentials de la base centrale sont lus dans `backend/.env`
(DB_SERVER / DB_NAME / DB_USER / DB_PASSWORD) — jamais en dur ici.

IMPORTANT : si `OPTIBOARD_SECRETS_AES_KEY` est définie côté serveur, elle doit l'être
à l'identique pour ce script, sinon les valeurs seront chiffrées avec une autre clé
que celle utilisée au déchiffrement (l'agent recevrait alors un mot de passe vide).
"""
import os
import sys
import argparse
from pathlib import Path

# Rendre `app.` importable quel que soit le répertoire d'appel.
_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

import pyodbc  # noqa: E402
from app.services.secret_crypto import enc_secret, is_encrypted  # noqa: E402

DRIVER = "{ODBC Driver 17 for SQL Server}"


def load_env() -> dict:
    env = {}
    env_path = _BACKEND / ".env"
    if not env_path.exists():
        sys.exit(f"ERREUR: {env_path} introuvable — impossible de résoudre la base centrale.")
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"')
    for required in ("DB_SERVER", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        if not env.get(required):
            sys.exit(f"ERREUR: {required} absent de {env_path}")
    return env


def connect(server: str, database: str, user: str, password: str, timeout: int = 20):
    return pyodbc.connect(
        f"DRIVER={DRIVER};SERVER={server};DATABASE={database};UID={user};PWD={password};"
        f"TrustServerCertificate=yes;",
        timeout=timeout,
    )


def list_tenants(env: dict, only_dwh: str = None) -> list:
    """Résout (dwh_code, serveur, base, user, password) pour chaque client actif.

    Même résolution que le backend (`APP_ClientDB` complété par `APP_DWH`) : en
    multi-tenant la base d'un DWH peut vivre sur un autre serveur SQL.
    """
    sql = """
        SELECT c.dwh_code, c.db_name,
               COALESCE(c.db_server,   d.serveur_optiboard, d.serveur_dwh)   AS db_server,
               COALESCE(c.db_user,     d.user_optiboard,    d.user_dwh)      AS db_user,
               COALESCE(c.db_password, d.password_optiboard, d.password_dwh) AS db_password
        FROM APP_ClientDB c
        LEFT JOIN APP_DWH d ON d.code = c.dwh_code
        WHERE c.actif = 1
    """
    params = ()
    if only_dwh:
        sql += " AND UPPER(c.dwh_code) = UPPER(?)"
        params = (only_dwh,)

    with connect(env["DB_SERVER"], env["DB_NAME"], env["DB_USER"], env["DB_PASSWORD"]) as conn:
        rows = conn.cursor().execute(sql, params).fetchall()

    tenants = []
    for r in rows:
        tenants.append({
            "dwh_code": r.dwh_code,
            "db_name": r.db_name,
            "db_server": r.db_server or env["DB_SERVER"],
            "db_user": r.db_user or env["DB_USER"],
            "db_password": r.db_password or env["DB_PASSWORD"],
        })
    return tenants


def process(tenant: dict, apply_changes: bool) -> tuple:
    """Retourne (nb_chiffres, nb_deja_chiffres, nb_vides)."""
    done = already = empty = 0
    with connect(tenant["db_server"], tenant["db_name"],
                 tenant["db_user"], tenant["db_password"]) as conn:
        cur = conn.cursor()
        cur.execute("""
            IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES
                           WHERE TABLE_NAME = 'APP_ETL_Agents')
                SELECT 0 AS ok ELSE SELECT 1 AS ok
        """)
        if not cur.fetchone()[0]:
            print(f"  (pas de table APP_ETL_Agents — ignoré)")
            return (0, 0, 0)

        rows = cur.execute("SELECT agent_id, sage_password FROM APP_ETL_Agents").fetchall()
        for agent_id, pwd in rows:
            if not pwd:
                empty += 1
                continue
            if is_encrypted(pwd):
                already += 1
                continue
            encrypted = enc_secret(pwd)
            if encrypted == pwd:
                # enc_secret retombe sur le plaintext si le chiffrement échoue :
                # ne pas compter ça comme un succès.
                print(f"  !! {agent_id} : chiffrement impossible, valeur laissée en clair")
                continue
            if apply_changes:
                cur.execute(
                    "UPDATE APP_ETL_Agents SET sage_password = ?, updated_at = GETDATE() "
                    "WHERE agent_id = ?",
                    (encrypted, agent_id),
                )
            done += 1
            print(f"  {'chiffré' if apply_changes else 'à chiffrer'} : {agent_id}")
        if apply_changes:
            conn.commit()
    return (done, already, empty)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="écrit réellement (sinon simulation)")
    ap.add_argument("--dwh", help="limiter à un code DWH")
    args = ap.parse_args()

    env = load_env()
    if not os.environ.get("OPTIBOARD_SECRETS_AES_KEY"):
        print("! OPTIBOARD_SECRETS_AES_KEY non définie : chiffrement avec la clé de repli.\n"
              "  Définissez-la ici ET côté serveur pour une vraie protection.\n")

    tenants = list_tenants(env, args.dwh)
    if not tenants:
        sys.exit("Aucun client actif trouvé dans APP_ClientDB.")

    print(f"{'== APPLICATION' if args.apply else '== SIMULATION (aucune écriture)'} — "
          f"{len(tenants)} base(s) client\n")
    totals = [0, 0, 0]
    for t in tenants:
        print(f"[{t['dwh_code']}] {t['db_name']} @ {t['db_server']}")
        try:
            done, already, empty = process(t, args.apply)
        except Exception as e:
            print(f"  ERREUR : {e}")
            continue
        totals = [totals[0] + done, totals[1] + already, totals[2] + empty]
        print(f"  -> {done} à chiffrer | {already} déjà chiffrés | {empty} vides")

    verb = "chiffrés" if args.apply else "à chiffrer"
    print(f"\nTotal : {totals[0]} {verb}, {totals[1]} déjà chiffrés, {totals[2]} vides")
    if not args.apply and totals[0]:
        print("Relancez avec --apply pour écrire.")


if __name__ == "__main__":
    main()
