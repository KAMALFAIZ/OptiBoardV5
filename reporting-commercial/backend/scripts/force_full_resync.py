# -*- coding: utf-8 -*-
"""
Force un rechargement COMPLET d'une table ETL, puis la remet en incremental.

Motif
-----
Une table synchronisee en `incremental` sur une colonne d'horodatage ne rattrape
jamais son historique : si la table cible est videe ou recreee, seules les lignes
modifiees APRES cet instant reviennent. Les lignes anciennes, dont l'horodatage
source est anterieur, ne repassent plus jamais le filtre.

Cas constate le 2026-09-08 sur ALEAFOOD :
    Entete_des_ventes            546 lignes (2026-07-31 -> 2026-09-07)
    Imputation_Factures_Ventes     2 lignes
    Lignes_des_ventes        573 373 lignes (2019 -> 2026)   <- saine
Consequences mesurees : historique documents tronque, imputations de reglements
inexploitables, informations libres d'en-tete inaccessibles (leur cle de jointure
est le cbMarq de l'en-tete), et filtre de souche impossible sur les etats tonnage.

Utilisation
-----------
    python scripts/force_full_resync.py                      # etat des lieux
    python scripts/force_full_resync.py --full --apply       # passe en full
    python scripts/force_full_resync.py --incremental --apply  # remet en incremental

    --table "Entetes des ventes"   cible une autre table (defaut : celle-ci)

PRECAUTIONS — a lire avant --apply
----------------------------------
1. ETL_Tables_Config est PARTAGEE par tous les tenants. Passer une table en `full`
   declenche son rechargement complet chez CHAQUE agent actif, pas seulement
   ALEAFOOD. Sur Entete_des_ventes cela represente environ 300 000 lignes par
   societe, transitant par le tunnel Sage. A lancer hors heures ouvrees.
2. Ne PAS oublier `--incremental --apply` une fois le rattrapage constate, sinon
   la table est integralement rechargee a chaque cycle (toutes les 5 minutes).
3. Sans agent en fonctionnement, ce script ne produit aucun effet : il ne fait que
   changer une consigne que l'agent viendra lire. Verifier d'abord le heartbeat
   (APP_ETL_Agents_Monitoring.last_heartbeat).
4. Verifier apres coup :
       SELECT COUNT(*), MIN([Date]), MAX([Date]) FROM [Entete_des_ventes]
   Le comptage doit se rapprocher de celui de Lignes_des_ventes en nombre de
   documents distincts.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import central_cursor

DEFAULT_TABLE = u"Entêtes des ventes"


def etat_des_lieux(cur, table):
    cur.execute(
        "SELECT config_id, table_name, target_table, sync_type, timestamp_column, "
        "       is_active, enabled, updated_at "
        "FROM ETL_Tables_Config WHERE table_name = ?", (table,))
    row = cur.fetchone()
    if not row:
        print("Table introuvable dans ETL_Tables_Config : %r" % table)
        return None
    cols = [d[0] for d in cur.description]
    d = dict(zip(cols, row))
    print("Config ETL centrale")
    for k in cols:
        print("   %-18s %s" % (k, d[k]))
    return d

def etat_agents(cur):
    cur.execute(
        "SELECT dwh_code, statut, last_heartbeat, "
        "       DATEDIFF(minute, last_heartbeat, GETDATE()) AS anciennete_min "
        "FROM APP_ETL_Agents_Monitoring ORDER BY dwh_code")
    print("\nAgents ETL")
    for dwh, statut, hb, age in cur.fetchall():
        alerte = ""
        if age is None:
            alerte = "  <- jamais vu"
        elif age > 60:
            alerte = "  <- HORS LIGNE depuis %d h" % (age // 60)
        print("   %-12s %-8s dernier heartbeat %s%s" % (dwh, statut, str(hb)[:19], alerte))


def basculer(cur, table, sync_type):
    cur.execute(
        "UPDATE ETL_Tables_Config SET sync_type = ?, updated_at = GETDATE() "
        "WHERE table_name = ?", (sync_type, table))
    print("\nsync_type -> %r pour %r (%d ligne modifiee)" % (sync_type, table, cur.rowcount))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default=DEFAULT_TABLE)
    ap.add_argument("--full", action="store_true", help="passer la table en rechargement complet")
    ap.add_argument("--incremental", action="store_true", help="revenir en incremental")
    ap.add_argument("--apply", action="store_true", help="ecrire reellement (sinon simulation)")
    args = ap.parse_args()

    if args.full and args.incremental:
        ap.error("--full et --incremental sont exclusifs")

    with central_cursor() as cur:
        conf = etat_des_lieux(cur, args.table)
        etat_agents(cur)
        if not conf:
            return
        if not (args.full or args.incremental):
            print("\n(etat des lieux seulement — ajouter --full ou --incremental)")
            return
        cible = "full" if args.full else "incremental"
        if conf["sync_type"] == cible:
            print("\nDeja en %r : rien a faire." % cible)
            return
        if not args.apply:
            print("\nSIMULATION — passerait sync_type de %r a %r. "
                  "Relancer avec --apply pour ecrire." % (conf["sync_type"], cible))
            return
        basculer(cur, args.table, cible)
        if cible == "full":
            print("Penser a repasser en incremental une fois le rattrapage constate.")


if __name__ == "__main__":
    main()
