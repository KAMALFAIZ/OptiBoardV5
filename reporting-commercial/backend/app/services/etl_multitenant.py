"""
Service ETL Multi-Tenant pour OptiBoard
=======================================
Synchronisation des donnees Sage vers DWH pour chaque client
"""

import pyodbc
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

from ..database_unified import (
    execute_central as execute_central_query,
    write_central as execute_central_write,
    execute_dwh_query,
    execute_dwh_write,
    dwh_pool
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ETL_MultiTenant")


# =====================================================
# CONFIGURATION DES TABLES A SYNCHRONISER
# =====================================================

ETL_TABLE_CONFIG = {
    "Clients": {
        "sage_table": "F_COMPTET",
        "sage_query": """
            SELECT
                '{societe_code}' as societe_code,
                CT_Num as code_client,
                CT_Intitule as nom,
                CT_Adresse as adresse,
                CT_Ville as ville,
                CT_CodePostal as code_postal,
                CT_Pays as pays,
                CT_Telephone as telephone,
                CT_Email as email,
                CT_Classement as categorie,
                CO_No as commercial_code,
                CT_Encours as encours_autorise,
                N_ModeRegl as mode_reglement,
                CT_DateCreate as date_creation_sage
            FROM F_COMPTET
            WHERE CT_Type = 0
        """,
        "dwh_table": "Clients",
        "key_columns": ["societe_code", "code_client"],
        "watermark_column": None,  # Full sync
    },

    "Entete_Ventes": {
        "sage_table": "F_DOCENTETE",
        "sage_query": """
            SELECT
                '{societe_code}' as societe_code,
                DO_Piece as numero_piece,
                DO_Type as type_document,
                DO_Date as date_piece,
                DO_Tiers as code_client,
                DO_TotalHT as montant_ht,
                DO_TotalTVA as montant_tva,
                DO_TotalTTC as montant_ttc,
                CO_No as commercial_code
            FROM F_DOCENTETE
            WHERE DO_Type IN (6, 7)  -- Factures et avoirs
            {where_clause}
        """,
        "dwh_table": "Entete_Ventes",
        "key_columns": ["societe_code", "numero_piece", "type_document"],
        "watermark_column": "DO_Date",
    },

    "Lignes_Ventes": {
        "sage_table": "F_DOCLIGNE",
        "sage_query": """
            SELECT
                '{societe_code}' as societe_code,
                e.DO_Piece as numero_piece,
                e.DO_Type as type_document,
                l.DL_Ligne as numero_ligne,
                e.DO_Date as date_piece,
                l.AR_Ref as code_article,
                l.DL_Design as designation,
                a.FA_CodeFamille as famille,
                e.DO_Tiers as code_client,
                c.CT_Intitule as nom_client,
                l.DL_Qte as quantite,
                l.DL_PrixUnitaire as prix_unitaire,
                l.DL_Remise01REM_Valeur as taux_remise,
                l.DL_MontantHT as montant_ht,
                l.DL_MontantTTC as montant_ttc,
                l.DL_PAMP as cout_revient,
                (l.DL_MontantHT - (l.DL_Qte * l.DL_PAMP)) as marge,
                l.cbModification as cb_modification
            FROM F_DOCLIGNE l
            INNER JOIN F_DOCENTETE e ON l.DO_Piece = e.DO_Piece AND l.DO_Type = e.DO_Type
            LEFT JOIN F_ARTICLE a ON l.AR_Ref = a.AR_Ref
            LEFT JOIN F_COMPTET c ON e.DO_Tiers = c.CT_Num
            WHERE e.DO_Type IN (6, 7)
            {where_clause}
        """,
        "dwh_table": "Lignes_Ventes",
        "key_columns": ["societe_code", "numero_piece", "type_document", "numero_ligne"],
        "watermark_column": "l.cbModification",
        "watermark_type": "binary",  # cbModification est un timestamp binaire
    },

    "Articles": {
        "sage_table": "F_ARTICLE",
        "sage_query": """
            SELECT
                '{societe_code}' as societe_code,
                AR_Ref as code_article,
                AR_Design as designation,
                FA_CodeFamille as famille,
                AR_PrixVen as prix_vente,
                AR_PrixAch as prix_achat,
                AR_UniteVen as unite_vente,
                AR_UnitePoids as unite_stock,
                AR_DateCreate as date_creation_sage
            FROM F_ARTICLE
            WHERE AR_Sommeil = 0
        """,
        "dwh_table": "Articles",
        "key_columns": ["societe_code", "code_article"],
        "watermark_column": None,
    },

    "Stock": {
        "sage_table": "F_ARTSTOCK",
        "sage_query": """
            SELECT
                '{societe_code}' as societe_code,
                s.AR_Ref as code_article,
                a.AR_Design as designation,
                a.FA_CodeFamille as famille,
                s.DE_No as code_depot,
                s.AS_QteSto as quantite_stock,
                s.AS_QteRes as quantite_reservee,
                s.AS_QteCom as quantite_commandee,
                s.AS_CMUP as prix_moyen_pondere,
                (s.AS_QteSto * s.AS_CMUP) as valeur_stock,
                s.AS_DateDMvt as date_dernier_mouvement
            FROM F_ARTSTOCK s
            INNER JOIN F_ARTICLE a ON s.AR_Ref = a.AR_Ref
        """,
        "dwh_table": "Stock",
        "key_columns": ["societe_code", "code_article", "code_depot"],
        "watermark_column": None,
    },
}


# =====================================================
# CLASSE ETL MANAGER
# =====================================================

class ETLMultiTenantManager:
    """Gestionnaire ETL multi-tenant"""

    def __init__(self):
        self.max_workers = 3  # Nombre de syncs paralleles
        self.batch_size = 5000  # Taille des lots pour fast_executemany (optimise)
        self.use_fast_executemany = True  # Utiliser fast_executemany (77x plus rapide)

    def get_sage_connection(self, societe_config: Dict[str, Any]) -> pyodbc.Connection:
        """Cree une connexion vers une base Sage"""
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={societe_config['serveur_sage']};"
            f"DATABASE={societe_config['base_sage']};"
            f"UID={societe_config['user_sage']};"
            f"PWD={societe_config['password_sage']};"
            f"TrustServerCertificate=yes"
        )
        return pyodbc.connect(conn_str)

    def get_dwh_connection(self, dwh_code: str) -> pyodbc.Connection:
        """Cree une connexion vers un DWH"""
        return dwh_pool.get_connection(dwh_code)

    def get_watermark(self, dwh_code: str, societe_code: str, table_name: str) -> Optional[str]:
        """Recupere le watermark pour un sync incremental"""
        try:
            result = execute_dwh_query(
                dwh_code,
                """SELECT watermark_value FROM ETL_Watermarks
                   WHERE societe_code = ? AND table_name = ?""",
                (societe_code, table_name),
                use_cache=False
            )
            return result[0]["watermark_value"] if result else None
        except:
            return None

    def set_watermark(self, dwh_code: str, societe_code: str, table_name: str, value: str):
        """Met a jour le watermark"""
        try:
            execute_dwh_write(
                dwh_code,
                """MERGE ETL_Watermarks AS target
                   USING (SELECT ? as societe_code, ? as table_name) AS source
                   ON target.societe_code = source.societe_code AND target.table_name = source.table_name
                   WHEN MATCHED THEN UPDATE SET watermark_value = ?, last_sync = GETDATE()
                   WHEN NOT MATCHED THEN INSERT (societe_code, table_name, watermark_column, watermark_value, last_sync)
                        VALUES (?, ?, 'date', ?, GETDATE());""",
                (societe_code, table_name, value, societe_code, table_name, value)
            )
        except Exception as e:
            logger.warning(f"Erreur mise a jour watermark: {e}")

    def log_sync(
        self,
        dwh_code: str,
        societe_code: str,
        table_name: str,
        sync_type: str,
        status: str,
        rows_extracted: int = 0,
        rows_inserted: int = 0,
        rows_updated: int = 0,
        error_message: str = None,
        started_at: datetime = None,
        completed_at: datetime = None
    ):
        """Enregistre le log de sync"""
        try:
            execute_dwh_write(
                dwh_code,
                """INSERT INTO ETL_SyncLog
                   (societe_code, table_name, sync_type, status, rows_extracted,
                    rows_inserted, rows_updated, error_message, started_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (societe_code, table_name, sync_type, status, rows_extracted,
                 rows_inserted, rows_updated, error_message, started_at, completed_at)
            )
        except Exception as e:
            logger.warning(f"Erreur log sync: {e}")

    def sync_table(
        self,
        dwh_code: str,
        societe_config: Dict[str, Any],
        table_name: str,
        sync_type: str = "incremental"
    ) -> Dict[str, Any]:
        """
        Synchronise une table pour une societe

        OPTIMISE avec fast_executemany (77x plus rapide que executemany standard):
        - Mode 'full': TRUNCATE + BULK INSERT avec fast_executemany
        - Mode 'incremental': Table staging + MERGE optimise
        """
        societe_code = societe_config["code_societe"]
        config = ETL_TABLE_CONFIG.get(table_name)

        if not config:
            return {"success": False, "error": f"Table {table_name} non configuree"}

        started_at = datetime.now()
        result = {
            "table": table_name,
            "societe": societe_code,
            "sync_type": sync_type,
            "rows_extracted": 0,
            "rows_inserted": 0,
            "rows_updated": 0,
            "success": False,
            "method": "fast_executemany"
        }

        sage_conn = None
        dwh_conn = None

        try:
            # Construire la clause WHERE pour sync incremental
            where_clause = ""
            if sync_type == "incremental" and config.get("watermark_column"):
                watermark = self.get_watermark(dwh_code, societe_code, table_name)
                if watermark:
                    wm_col = config['watermark_column']
                    wm_type = config.get('watermark_type', 'date')

                    if wm_type == 'binary':
                        # cbModification est un timestamp binaire (ROWVERSION)
                        # Format: 0x... en hexadecimal
                        where_clause = f"AND {wm_col} > {watermark}"
                    else:
                        # Date ou autre type standard
                        where_clause = f"AND {wm_col} > '{watermark}'"

            # Construire la requete
            query = config["sage_query"].format(
                societe_code=societe_code,
                where_clause=where_clause
            )

            # Extraire les donnees depuis Sage
            sage_conn = self.get_sage_connection(societe_config)
            cursor = sage_conn.cursor()
            cursor.execute(query)

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            result["rows_extracted"] = len(rows)

            cursor.close()
            sage_conn.close()
            sage_conn = None

            if not rows:
                result["success"] = True
                result["message"] = "Aucune nouvelle donnee"
                self.log_sync(dwh_code, societe_code, table_name, sync_type, "success",
                             started_at=started_at, completed_at=datetime.now())
                return result

            # Connexion DWH avec fast_executemany
            dwh_conn = self.get_dwh_connection(dwh_code)
            dwh_conn.autocommit = False
            dwh_cursor = dwh_conn.cursor()

            # ACTIVER fast_executemany pour des performances optimales
            dwh_cursor.fast_executemany = self.use_fast_executemany

            key_cols = config["key_columns"]
            all_cols = columns
            dwh_table = config['dwh_table']

            # Convertir les rows en liste de tuples
            data_tuples = [tuple(row) for row in rows]

            if sync_type == "full":
                # ==============================================
                # MODE FULL: TRUNCATE + BULK INSERT (le plus rapide)
                # ==============================================

                # Supprimer les donnees existantes pour cette societe
                delete_sql = f"DELETE FROM {dwh_table} WHERE societe_code = ?"
                dwh_cursor.execute(delete_sql, (societe_code,))

                # BULK INSERT avec fast_executemany
                placeholders = ", ".join(["?" for _ in all_cols])
                insert_sql = f"INSERT INTO {dwh_table} ({', '.join(all_cols)}) VALUES ({placeholders})"

                # Inserer par lots
                for i in range(0, len(data_tuples), self.batch_size):
                    batch = data_tuples[i:i + self.batch_size]
                    dwh_cursor.executemany(insert_sql, batch)
                    result["rows_inserted"] += len(batch)

                dwh_conn.commit()

            else:
                # ==============================================
                # MODE INCREMENTAL: Staging table + MERGE
                # ==============================================

                staging_table = f"#staging_{dwh_table}_{societe_code.replace('-', '_')}"

                # Creer table temporaire de staging
                col_defs = []
                for col in all_cols:
                    # Types generiques pour staging
                    col_defs.append(f"[{col}] NVARCHAR(MAX)")

                create_staging = f"CREATE TABLE {staging_table} ({', '.join(col_defs)})"
                dwh_cursor.execute(create_staging)

                # BULK INSERT dans staging avec fast_executemany
                placeholders = ", ".join(["?" for _ in all_cols])
                insert_staging = f"INSERT INTO {staging_table} ({', '.join(all_cols)}) VALUES ({placeholders})"

                # Convertir tout en string pour la table staging NVARCHAR
                data_as_strings = []
                for row in data_tuples:
                    str_row = tuple(str(v) if v is not None else None for v in row)
                    data_as_strings.append(str_row)

                for i in range(0, len(data_as_strings), self.batch_size):
                    batch = data_as_strings[i:i + self.batch_size]
                    dwh_cursor.executemany(insert_staging, batch)

                # MERGE depuis staging vers table cible
                non_key_cols = [c for c in all_cols if c not in key_cols]
                key_conditions = " AND ".join([f"target.[{k}] = source.[{k}]" for k in key_cols])

                if non_key_cols:
                    update_set = ", ".join([f"target.[{c}] = source.[{c}]" for c in non_key_cols])
                    merge_sql = f"""
                        MERGE {dwh_table} AS target
                        USING {staging_table} AS source
                        ON {key_conditions}
                        WHEN MATCHED THEN UPDATE SET {update_set}
                        WHEN NOT MATCHED THEN INSERT ({', '.join(all_cols)})
                             VALUES ({', '.join([f'source.[{c}]' for c in all_cols])});
                    """
                else:
                    # Pas de colonnes a mettre a jour (que des cles)
                    merge_sql = f"""
                        MERGE {dwh_table} AS target
                        USING {staging_table} AS source
                        ON {key_conditions}
                        WHEN NOT MATCHED THEN INSERT ({', '.join(all_cols)})
                             VALUES ({', '.join([f'source.[{c}]' for c in all_cols])});
                    """

                dwh_cursor.execute(merge_sql)
                affected = dwh_cursor.rowcount
                result["rows_inserted"] = affected

                # Supprimer la table staging
                dwh_cursor.execute(f"DROP TABLE {staging_table}")

                dwh_conn.commit()

            dwh_cursor.close()
            dwh_conn.close()
            dwh_conn = None

            # Mettre a jour le watermark si incremental
            if config.get("watermark_column"):
                wm_col = config["watermark_column"]
                wm_type = config.get("watermark_type", "date")

                # Trouver la colonne watermark dans les resultats
                # Le nom peut etre un alias (cb_modification) ou le nom complet (l.cbModification)
                wm_col_name = wm_col.split('.')[-1]  # Prendre apres le dernier point
                # Chercher la colonne correspondante (insensible a la casse)
                wm_index = None
                for i, col in enumerate(columns):
                    if col.lower() == wm_col_name.lower() or col.lower() == 'cb_modification':
                        wm_index = i
                        break

                if wm_index is not None:
                    valid_values = [r[wm_index] for r in rows if r[wm_index] is not None]
                    if valid_values:
                        max_value = max(valid_values)

                        # Formater selon le type
                        if wm_type == 'binary' and isinstance(max_value, bytes):
                            # Convertir bytes en format hexadecimal SQL Server
                            wm_str = '0x' + max_value.hex().upper()
                        else:
                            wm_str = str(max_value)

                        self.set_watermark(dwh_code, societe_code, table_name, wm_str)

            duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)
            rows_per_sec = int(result["rows_extracted"] / max(duration_ms / 1000, 0.001))

            result["success"] = True
            result["duration_ms"] = duration_ms
            result["rows_per_sec"] = rows_per_sec
            result["message"] = f"Sync reussi: {result['rows_extracted']} extraits, {result['rows_inserted']} inseres/maj ({rows_per_sec} rows/sec)"

            self.log_sync(
                dwh_code, societe_code, table_name, sync_type, "success",
                rows_extracted=result["rows_extracted"],
                rows_inserted=result["rows_inserted"],
                started_at=started_at,
                completed_at=datetime.now()
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erreur sync {table_name} pour {societe_code}: {error_msg}")
            logger.error(traceback.format_exc())

            result["success"] = False
            result["error"] = error_msg

            self.log_sync(
                dwh_code, societe_code, table_name, sync_type, "error",
                error_message=error_msg,
                started_at=started_at,
                completed_at=datetime.now()
            )

        finally:
            # Fermer les connexions proprement
            if sage_conn:
                try:
                    sage_conn.close()
                except:
                    pass
            if dwh_conn:
                try:
                    dwh_conn.close()
                except:
                    pass

        return result

    def sync_societe(
        self,
        dwh_code: str,
        societe_config: Dict[str, Any],
        tables: List[str] = None,
        sync_type: str = "incremental"
    ) -> Dict[str, Any]:
        """Synchronise toutes les tables pour une societe"""
        societe_code = societe_config["code_societe"]
        tables = tables or list(ETL_TABLE_CONFIG.keys())

        logger.info(f"Debut sync {societe_code} -> {dwh_code} ({len(tables)} tables)")

        results = {
            "societe": societe_code,
            "dwh": dwh_code,
            "sync_type": sync_type,
            "tables": {},
            "success": True,
            "started_at": datetime.now().isoformat()
        }

        for table in tables:
            table_result = self.sync_table(dwh_code, societe_config, table, sync_type)
            results["tables"][table] = table_result
            if not table_result.get("success"):
                results["success"] = False

        results["completed_at"] = datetime.now().isoformat()

        # Mettre a jour le statut dans APP_DWH_Sources
        status = "success" if results["success"] else "error"
        execute_central_write(
            """UPDATE APP_DWH_Sources
               SET last_sync = GETDATE(), last_sync_status = ?
               WHERE dwh_code = ? AND code_societe = ?""",
            (status, dwh_code, societe_code)
        )

        logger.info(f"Fin sync {societe_code}: {'OK' if results['success'] else 'ERREUR'}")

        return results

    def sync_dwh(
        self,
        dwh_code: str,
        tables: List[str] = None,
        sync_type: str = "incremental",
        parallel: bool = True
    ) -> Dict[str, Any]:
        """Synchronise toutes les societes d'un DWH"""
        # Recuperer les societes du DWH
        societes = execute_central_query(
            """SELECT code_societe, nom_societe, serveur_sage, base_sage,
                      user_sage, password_sage, etl_mode
               FROM APP_DWH_Sources
               WHERE dwh_code = ? AND etl_enabled = 1 AND actif = 1""",
            (dwh_code,),
            use_cache=False
        )

        if not societes:
            return {"success": False, "error": "Aucune societe active pour ce DWH"}

        logger.info(f"Sync DWH {dwh_code}: {len(societes)} societes")

        results = {
            "dwh": dwh_code,
            "sync_type": sync_type,
            "societes": {},
            "success": True,
            "started_at": datetime.now().isoformat()
        }

        if parallel and len(societes) > 1:
            # Sync parallele
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        self.sync_societe,
                        dwh_code,
                        dict(societe),
                        tables,
                        societe.get("etl_mode", sync_type)
                    ): societe["code_societe"]
                    for societe in societes
                }

                for future in as_completed(futures):
                    societe_code = futures[future]
                    try:
                        result = future.result()
                        results["societes"][societe_code] = result
                        if not result.get("success"):
                            results["success"] = False
                    except Exception as e:
                        results["societes"][societe_code] = {"success": False, "error": str(e)}
                        results["success"] = False
        else:
            # Sync sequentiel
            for societe in societes:
                result = self.sync_societe(
                    dwh_code,
                    dict(societe),
                    tables,
                    societe.get("etl_mode", sync_type)
                )
                results["societes"][societe["code_societe"]] = result
                if not result.get("success"):
                    results["success"] = False

        results["completed_at"] = datetime.now().isoformat()
        return results

    def sync_all_dwh(
        self,
        tables: List[str] = None,
        sync_type: str = "incremental"
    ) -> Dict[str, Any]:
        """Synchronise tous les DWH actifs"""
        dwh_list = execute_central_query(
            "SELECT code FROM APP_DWH WHERE actif = 1",
            use_cache=False
        )

        results = {
            "dwh_list": {},
            "success": True,
            "started_at": datetime.now().isoformat()
        }

        for dwh in dwh_list:
            dwh_code = dwh["code"]
            result = self.sync_dwh(dwh_code, tables, sync_type, parallel=True)
            results["dwh_list"][dwh_code] = result
            if not result.get("success"):
                results["success"] = False

        results["completed_at"] = datetime.now().isoformat()
        return results


# Instance globale
etl_manager = ETLMultiTenantManager()


# =====================================================
# FONCTIONS UTILITAIRES
# =====================================================

def run_sync_societe(dwh_code: str, societe_code: str, sync_type: str = "incremental") -> Dict[str, Any]:
    """Lance un sync pour une societe specifique"""
    societe = execute_central_query(
        """SELECT code_societe, nom_societe, serveur_sage, base_sage,
                  user_sage, password_sage, etl_mode
           FROM APP_DWH_Sources
           WHERE dwh_code = ? AND code_societe = ?""",
        (dwh_code, societe_code),
        use_cache=False
    )

    if not societe:
        return {"success": False, "error": "Societe non trouvee"}

    return etl_manager.sync_societe(dwh_code, dict(societe[0]), sync_type=sync_type)


def run_sync_dwh(dwh_code: str, sync_type: str = "incremental") -> Dict[str, Any]:
    """Lance un sync pour un DWH complet"""
    return etl_manager.sync_dwh(dwh_code, sync_type=sync_type)


def run_sync_all(sync_type: str = "incremental") -> Dict[str, Any]:
    """Lance un sync pour tous les DWH"""
    return etl_manager.sync_all_dwh(sync_type=sync_type)
