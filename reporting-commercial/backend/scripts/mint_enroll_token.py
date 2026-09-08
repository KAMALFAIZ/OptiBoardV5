"""
Emet un jeton d'enrolement a usage unique pour un agent ETL.
================================================================

Equivalent hors-ligne de POST /api/admin/etl/agents/{agent_id}/enroll-token,
utile quand aucune session admin n'est disponible (poste serveur, maintenance).

    python scripts/mint_enroll_token.py --list
    python scripts/mint_enroll_token.py --dwh ALEAFOOD --agent-id <uuid>
    python scripts/mint_enroll_token.py --dwh ALEAFOOD --agent-id <uuid> --ttl 120

Le jeton s'echange ensuite UNE SEULE FOIS par l'agent :

    POST {SERVER_PUBLIC_URL}/api/agents/enroll   {"token": "<jeton>"}
    -> { agent_id, api_key, dwh_code }

ATTENTION : l'echange REGENERE la cle API de l'agent. Ne pas enroler un agent
qui fonctionne deja (sa cle actuelle serait invalidee jusqu'au redeploiement
de la nouvelle). A reserver aux agents sans cle ou dont la cle est perdue.

Prerequis : la base CLIENT du DWH doit etre joignable (voir
scripts/fix_client_db_routing_loopback.sql si db_server pointe sur 127.0.0.1).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import execute_central, client_cursor  # noqa: E402


def list_agents() -> int:
    """Affiche les agents connus et l'etat de leur cle, sans rien modifier."""
    rows = execute_central(
        "SELECT agent_id, dwh_code, nom, statut, last_heartbeat "
        "FROM APP_ETL_Agents_Monitoring ORDER BY dwh_code, nom",
        use_cache=False,
    )
    if not rows:
        print("Aucun agent en monitoring central.")
        return 0
    print(f"{'DWH':<12} {'AGENT_ID':<38} {'NOM':<26} {'STATUT':<10} DERNIER HEARTBEAT")
    print("-" * 110)
    for r in rows:
        hb = r["last_heartbeat"] or "jamais"
        print(f"{r['dwh_code']:<12} {str(r['agent_id']):<38} {str(r['nom']):<26} "
              f"{str(r['statut']):<10} {hb}")
    return 0


def mint(dwh: str, agent_id: str, ttl: int) -> int:
    # Verifier que l'agent existe bien dans la base CLIENT (source de verite).
    try:
        with client_cursor(dwh) as cur:
            cur.execute(
                "SELECT nom, is_active, api_key_prefix, last_heartbeat "
                "FROM APP_ETL_Agents WHERE agent_id = ?",
                (agent_id,),
            )
            row = cur.fetchone()
    except Exception as e:
        print(f"[ERREUR] Base client '{dwh}' injoignable : {str(e)[:200]}")
        print("         Verifier APP_ClientDB.db_server (cf. "
              "scripts/fix_client_db_routing_loopback.sql).")
        return 2

    if not row:
        print(f"[ERREUR] Agent '{agent_id}' introuvable dans la base client {dwh}.")
        return 3

    nom, is_active, prefix, hb = row
    print(f"Agent   : {nom}")
    print(f"DWH     : {dwh}")
    print(f"Actif   : {is_active}   prefix cle actuelle : {prefix}")
    print(f"Heartbeat : {hb or 'jamais'}")
    if hb is not None:
        print("\n[AVERTISSEMENT] Cet agent a deja communique avec le serveur : il")
        print("                possede probablement une cle fonctionnelle.")
        print("                L'enrolement INVALIDERA cette cle.")
        if input("Continuer malgre tout ? (oui/non) ").strip().lower() != "oui":
            print("Abandon.")
            return 1

    from app.routes.etl_enroll import mint_enroll_token
    minted = mint_enroll_token(dwh, agent_id, ttl)

    print("\n" + "=" * 64)
    print("JETON D'ENROLEMENT (usage unique, a copier maintenant)")
    print("=" * 64)
    print(minted["enroll_token"])
    print(f"\nExpire le : {minted['expires_at']}")
    print("\nCote agent :")
    print('  POST {SERVER_PUBLIC_URL}/api/agents/enroll  {"token": "<ci-dessus>"}')
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", action="store_true", help="lister les agents connus")
    p.add_argument("--dwh", help="code DWH (ex: ALEAFOOD)")
    p.add_argument("--agent-id", help="identifiant de l'agent")
    p.add_argument("--ttl", type=int, default=None,
                   help="duree de validite en minutes (defaut : 1440)")
    a = p.parse_args()

    if a.list:
        return list_agents()
    if not a.dwh or not a.agent_id:
        p.error("--dwh et --agent-id sont requis (ou utilisez --list)")
    return mint(a.dwh, a.agent_id, a.ttl)


if __name__ == "__main__":
    sys.exit(main())
