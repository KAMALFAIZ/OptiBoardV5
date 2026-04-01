"""
Service d'ingestion de donnees pour les agents ETL distants
Gere l'insertion/mise a jour des donnees recues des agents
"""
import json
import logging
import traceback
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

from app.database_unified import DWHConnectionPool

logger = logging.getLogger(__name__)

# Activer les logs de ce module
logging.getLogger(__name__).setLevel(logging.DEBUG)

def log_ingestion(msg: str):
    """Log immediat vers stdout, fichier et flush"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[INGESTION] {timestamp} - {msg}"
    print(log_line, flush=True)
    sys.stdout.flush()
    # Aussi ecrire dans un fichier pour debug
    try:
        import os
        log_file = os.path.join(os.path.dirname(__file__), '..', '..', 'ingestion_debug.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    except:
        pass


class DataIngestionService:
    """
    Service pour ingerer les donnees envoyees par les agents ETL distants.
    Utilise le pattern UPSERT (MERGE) pour inserer ou mettre a jour les donnees.
    """

    def __init__(self, dwh_code: str):
        """
        Initialise le service d'ingestion.

        Args:
            dwh_code: Le code du DWH cible
        """
        self.dwh_code = dwh_code
        self.pool = DWHConnectionPool()

    async def ingest_batch(
        self,
        data: List[Dict[str, Any]],
        target_table: str,
        societe_code: str,
        primary_key_columns: List[str],
        column_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Ingere un batch de donnees dans le DWH.

        Args:
            data: Liste de dictionnaires contenant les donnees
            target_table: Nom de la table cible
            societe_code: Code de la societe (pour la colonne Societe)
            primary_key_columns: Liste des colonnes de cle primaire
            column_mapping: Mapping optionnel des colonnes source -> cible

        Returns:
            Dictionnaire avec les statistiques d'ingestion
        """
        log_ingestion(f"========== DEBUT INGEST_BATCH ==========")
        log_ingestion(f"Table: {target_table}, Societe: {societe_code}, Rows: {len(data) if data else 0}")
        log_ingestion(f"PK columns recues: {primary_key_columns}")

        if not data:
            log_ingestion("Aucune donnee - retour immediat")
            return {
                'rows_received': 0,
                'rows_inserted': 0,
                'rows_updated': 0,
                'rows_failed': 0,
                'message': 'Aucune donnee a ingerer'
            }

        rows_received = len(data)
        rows_inserted = 0
        rows_updated = 0
        rows_failed = 0
        errors = []

        try:
            # Convertir en DataFrame pour faciliter le traitement
            df = pd.DataFrame(data)
            log_ingestion(f"DataFrame cree avec {len(df)} lignes et {len(df.columns)} colonnes")
            log_ingestion(f"Colonnes du DataFrame: {list(df.columns)[:10]}...")

            # Appliquer le mapping de colonnes si fourni
            if column_mapping:
                df = df.rename(columns=column_mapping)

            # Ajouter la colonne Societe si pas presente
            if 'Societe' not in df.columns:
                df.insert(0, 'Societe', societe_code)
            else:
                df['Societe'] = societe_code

            # Ajouter les colonnes ETL metadata
            df['_etl_timestamp'] = datetime.now()
            df['_etl_source'] = 'agent_push'

            # S'assurer que Societe est dans les cles primaires
            # Normaliser les noms de cles primaires (enlever les crochets)
            pk_normalized_set = {self._normalize_column_name(pk) for pk in primary_key_columns}
            if 'Societe' not in pk_normalized_set:
                primary_key_columns = ['Societe'] + primary_key_columns

            log_ingestion(f"Cles primaires finales: {primary_key_columns}")
            log_ingestion(f"Colonnes finales: {list(df.columns)}")

            # Obtenir une connexion au DWH
            log_ingestion(f"Connexion au DWH: {self.dwh_code}")
            conn = self.pool.get_connection(self.dwh_code)
            try:
                cursor = conn.cursor()

                # Log la base de donnees utilisee
                cursor.execute("SELECT DB_NAME() as db_name")
                db_name = cursor.fetchone()[0]
                log_ingestion(f"Base de donnees cible: {db_name}")

                # Verifier/creer la table si necessaire
                await self._ensure_table_exists(cursor, target_table, df)

                # Effectuer le MERGE (UPSERT)
                result = await self._upsert_data(
                    cursor, target_table, df, primary_key_columns
                )

                rows_inserted = result['inserted']
                rows_updated = result['updated']
                rows_failed = result['failed']
                errors = result.get('errors', [])

                conn.commit()
                log_ingestion(f"Commit effectue - inserted={rows_inserted}, updated={rows_updated}, failed={rows_failed}")
            finally:
                conn.close()

        except Exception as e:
            error_detail = f"ERREUR GLOBALE: {str(e)}\n{traceback.format_exc()}"
            log_ingestion(error_detail)
            logger.error(f"Erreur lors de l'ingestion dans {target_table}: {str(e)}")
            rows_failed = rows_received
            errors.append(str(e))

        log_ingestion(f"========== FIN INGEST_BATCH: {rows_inserted} inseres, {rows_updated} maj, {rows_failed} echecs ==========")

        return {
            'rows_received': rows_received,
            'rows_inserted': rows_inserted,
            'rows_updated': rows_updated,
            'rows_failed': rows_failed,
            'message': f"Ingestion terminee: {rows_inserted} inseres, {rows_updated} mis a jour, {rows_failed} echecs",
            'errors': errors if errors else None
        }

    async def _ensure_table_exists(self, cursor, table_name: str, df: pd.DataFrame):
        """
        Verifie si la table existe et la cree si necessaire.
        """
        # Verifier si la table existe dans la base actuelle (avec schema dbo)
        check_query = """
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = ? AND TABLE_SCHEMA = 'dbo' AND TABLE_CATALOG = DB_NAME()
        """
        cursor.execute(check_query, (table_name,))
        result = cursor.fetchone()

        if result and result[0] > 0:
            log_ingestion(f"Table {table_name} existe deja")
            # Verifier les colonnes existantes vs nouvelles
            cursor.execute(f"""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ? AND TABLE_SCHEMA = 'dbo'
            """, (table_name,))
            existing_cols = {row[0] for row in cursor.fetchall()}
            df_cols = set(df.columns)
            missing_cols = df_cols - existing_cols
            if missing_cols:
                log_ingestion(f"Colonnes manquantes dans la table: {missing_cols}")
                # Ajouter les colonnes manquantes
                for col in missing_cols:
                    dtype = str(df[col].dtype)
                    sql_type = self._get_sql_type(col, dtype)
                    alter_query = f"ALTER TABLE [dbo].[{table_name}] ADD [{col}] {sql_type}"
                    log_ingestion(f"Ajout colonne: {alter_query}")
                    try:
                        cursor.execute(alter_query)
                        cursor.connection.commit()
                    except Exception as e:
                        log_ingestion(f"Erreur ajout colonne {col}: {e}")
            return  # La table existe

        # Creer la table
        log_ingestion(f"Creation de la table {table_name} dans la base courante")
        columns_def = self._generate_column_definitions(df)

        create_query = f"""
            CREATE TABLE [dbo].[{table_name}] (
                {columns_def}
            )
        """
        log_ingestion(f"CREATE TABLE query:\n{create_query}")
        cursor.execute(create_query)
        cursor.connection.commit()
        log_ingestion(f"Table {table_name} creee avec succes")

    def _get_sql_type(self, col: str, dtype: str) -> str:
        """
        Determine le type SQL pour une colonne.
        """
        type_mapping = {
            'int64': 'BIGINT',
            'int32': 'INT',
            'float64': 'FLOAT',
            'float32': 'FLOAT',
            'bool': 'BIT',
            'datetime64[ns]': 'DATETIME',
            'object': 'NVARCHAR(MAX)',
        }

        sql_type = type_mapping.get(dtype, 'NVARCHAR(MAX)')

        # Cas speciaux
        col_lower = col.lower()
        if col_lower == 'societe':
            sql_type = 'VARCHAR(50)'
        elif col_lower in ('cbmarq', 'id', 'code interne'):
            sql_type = 'BIGINT'
        elif col.startswith('_etl_'):
            if 'timestamp' in col:
                sql_type = 'DATETIME'
            else:
                sql_type = 'NVARCHAR(200)'

        return sql_type

    def _generate_column_definitions(self, df: pd.DataFrame) -> str:
        """
        Genere les definitions de colonnes SQL a partir d'un DataFrame.
        """
        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            sql_type = self._get_sql_type(col, dtype)
            columns.append(f"[{col}] {sql_type}")

        return ',\n                '.join(columns)

    async def _upsert_data(
        self,
        cursor,
        table_name: str,
        df: pd.DataFrame,
        primary_key_columns: List[str]
    ) -> Dict[str, int]:
        """
        Effectue un UPSERT (MERGE) des donnees.
        """
        inserted = 0
        updated = 0
        failed = 0
        errors = []

        # Obtenir les colonnes de la table cible
        columns = df.columns.tolist()

        # Normaliser les noms de colonnes des cles primaires pour la comparaison
        pk_normalized = {self._normalize_column_name(pk) for pk in primary_key_columns}

        # Colonnes non-cle pour l'UPDATE (comparaison normalisee)
        non_key_columns = [c for c in columns if self._normalize_column_name(c) not in pk_normalized]

        # Construire la clause MERGE
        merge_query = self._build_merge_query(table_name, columns, primary_key_columns, non_key_columns)

        # Traiter par lots de 1000 lignes
        batch_size = 1000
        first_row_logged = False

        log_ingestion(f"Debut upsert pour table {table_name}")
        log_ingestion(f"Colonnes ({len(columns)}): {columns[:5]}...")
        log_ingestion(f"PKs: {primary_key_columns}")
        log_ingestion(f"Non-PKs count: {len(non_key_columns)}")

        for start_idx in range(0, len(df), batch_size):
            batch_df = df.iloc[start_idx:start_idx + batch_size]
            log_ingestion(f"Traitement batch {start_idx} - {start_idx + len(batch_df)}")

            for row_idx, (_, row) in enumerate(batch_df.iterrows()):
                try:
                    # Preparer les valeurs
                    values = []
                    for col in columns:
                        val = row[col]
                        if pd.isna(val):
                            values.append(None)
                        elif isinstance(val, datetime):
                            values.append(val)
                        else:
                            values.append(val)

                    # Log la premiere ligne pour debug
                    log_this_row = not first_row_logged
                    if log_this_row:
                        log_ingestion(f"=== PREMIERE LIGNE DEBUG ===")
                        log_ingestion(f"Nombre de colonnes: {len(columns)}")
                        log_ingestion(f"Nombre de valeurs: {len(values)}")
                        log_ingestion(f"Colonnes: {columns[:10]}...")
                        log_ingestion(f"Valeurs: {values[:10]}...")
                        log_ingestion(f"Types valeurs: {[type(v).__name__ for v in values[:10]]}...")
                        first_row_logged = True

                    # Construire la requete d'insertion simple avec ON CONFLICT
                    # Utiliser une approche INSERT/UPDATE separee pour compatibilite
                    result = await self._insert_or_update_row(
                        cursor, table_name, columns, values,
                        primary_key_columns, non_key_columns,
                        log_first_row=log_this_row
                    )

                    if result == 'inserted':
                        inserted += 1
                    elif result == 'updated':
                        updated += 1

                except Exception as e:
                    failed += 1
                    error_str = str(e)
                    if len(errors) < 10:  # Limiter le nombre d'erreurs stockees
                        errors.append(error_str)
                    # Log plus de details pour les premieres erreurs
                    if failed <= 5:
                        log_ingestion(f"ERROR ligne {start_idx + row_idx}: {error_str}")
                        log_ingestion(f"ERROR Traceback: {traceback.format_exc()}")

        log_ingestion(f"Resultat upsert: {inserted} inseres, {updated} mis a jour, {failed} echecs")

        return {
            'inserted': inserted,
            'updated': updated,
            'failed': failed,
            'errors': errors
        }

    def _normalize_column_name(self, col_name: str) -> str:
        """
        Normalise un nom de colonne en retirant les crochets et les espaces.
        '[Code interne]' -> 'Code interne'
        'Societe' -> 'Societe'
        ' [Code interne] ' -> 'Code interne'
        """
        # D'abord enlever les espaces
        col_name = col_name.strip()
        # Ensuite enlever les crochets
        if col_name.startswith('[') and col_name.endswith(']'):
            return col_name[1:-1]
        return col_name

    def _find_column_index(self, columns: List[str], pk_col: str) -> int:
        """
        Trouve l'index d'une colonne en tenant compte des crochets.
        Cherche 'Code interne' ou '[Code interne]' dans la liste.
        """
        # Normaliser le nom recherche
        pk_normalized = self._normalize_column_name(pk_col).lower()

        # Chercher dans les colonnes (normalisees aussi)
        for idx, col in enumerate(columns):
            col_normalized = self._normalize_column_name(col).lower()
            if col_normalized == pk_normalized:
                return idx

        # Si pas trouve, lever une erreur explicite
        raise ValueError(f"Colonne '{pk_col}' (normalise: '{pk_normalized}') non trouvee dans les colonnes disponibles: {columns}")

    async def _insert_or_update_row(
        self,
        cursor,
        table_name: str,
        columns: List[str],
        values: List[Any],
        primary_key_columns: List[str],
        non_key_columns: List[str],
        log_first_row: bool = False
    ) -> str:
        """
        Insere ou met a jour une ligne individuellement.
        Retourne 'inserted' ou 'updated'.
        """
        try:
            # Construire la condition WHERE pour les cles primaires
            where_conditions = []
            where_values = []

            if log_first_row:
                log_ingestion(f"Colonnes disponibles: {columns}")
                log_ingestion(f"Cles primaires a chercher: {primary_key_columns}")

            for pk_col in primary_key_columns:
                # Utiliser la methode de recherche qui gere les crochets
                col_idx = self._find_column_index(columns, pk_col)
                # Normaliser le nom pour le SQL (avec crochets)
                pk_normalized = self._normalize_column_name(pk_col)
                where_conditions.append(f"[{pk_normalized}] = ?")
                pk_value = values[col_idx]
                where_values.append(pk_value)

                if log_first_row:
                    log_ingestion(f"PK '{pk_col}' -> index {col_idx} -> valeur: {pk_value}")

            where_clause = ' AND '.join(where_conditions)

            # Verifier si la ligne existe
            check_query = f"SELECT COUNT(*) FROM [{table_name}] WHERE {where_clause}"

            if log_first_row:
                log_ingestion(f"Check query: {check_query}")
                log_ingestion(f"Check values: {where_values}")

            cursor.execute(check_query, where_values)
            exists = cursor.fetchone()[0] > 0

            if exists:
                # DELETE puis INSERT (au lieu de UPDATE)
                delete_query = f"DELETE FROM [{table_name}] WHERE {where_clause}"
                cursor.execute(delete_query, where_values)

                # INSERT la nouvelle ligne
                cols_str = ', '.join([f"[{col}]" for col in columns])
                placeholders = ', '.join(['?' for _ in columns])
                insert_query = f"INSERT INTO [{table_name}] ({cols_str}) VALUES ({placeholders})"

                if log_first_row:
                    log_ingestion(f"Update INSERT query: {insert_query[:200]}...")

                cursor.execute(insert_query, values)
                return 'updated'
            else:
                # INSERT
                cols_str = ', '.join([f"[{col}]" for col in columns])
                placeholders = ', '.join(['?' for _ in columns])
                insert_query = f"INSERT INTO [{table_name}] ({cols_str}) VALUES ({placeholders})"

                if log_first_row:
                    log_ingestion(f"INSERT query: {insert_query[:200]}...")
                    log_ingestion(f"INSERT values types: {[type(v).__name__ for v in values[:5]]}...")

                cursor.execute(insert_query, values)
                return 'inserted'

        except Exception as e:
            # Re-raise avec plus de contexte
            error_msg = f"Erreur insertion dans {table_name}: {str(e)}"
            log_ingestion(f"ERROR: {error_msg}")
            log_ingestion(f"ERROR Traceback: {traceback.format_exc()}")
            raise Exception(error_msg) from e

    def _build_merge_query(
        self,
        table_name: str,
        columns: List[str],
        primary_key_columns: List[str],
        non_key_columns: List[str]
    ) -> str:
        """
        Construit une requete MERGE SQL Server.
        Note: Non utilisee actuellement car traitement ligne par ligne.
        """
        cols_str = ', '.join([f"[{col}]" for col in columns])
        source_cols = ', '.join([f"s.[{col}]" for col in columns])

        # Condition de jointure
        join_conditions = ' AND '.join([
            f"t.[{col}] = s.[{col}]" for col in primary_key_columns
        ])

        # Clause UPDATE
        update_set = ', '.join([
            f"t.[{col}] = s.[{col}]" for col in non_key_columns
        ]) if non_key_columns else ''

        merge_query = f"""
            MERGE [{table_name}] AS t
            USING (VALUES ({', '.join(['?' for _ in columns])})) AS s ({cols_str})
            ON ({join_conditions})
            WHEN MATCHED THEN
                UPDATE SET {update_set}
            WHEN NOT MATCHED THEN
                INSERT ({cols_str})
                VALUES ({source_cols});
        """

        return merge_query


class BulkIngestionService:
    """
    Service pour l'ingestion en masse avec staging table.
    A utiliser pour les gros volumes (>100k lignes).
    """

    def __init__(self, dwh_code: str):
        self.dwh_code = dwh_code
        self.pool = DWHConnectionPool()

    async def bulk_ingest(
        self,
        data: List[Dict[str, Any]],
        target_table: str,
        societe_code: str,
        primary_key_columns: List[str],
        truncate_first: bool = False
    ) -> Dict[str, Any]:
        """
        Ingestion en masse via une table de staging.

        Args:
            data: Liste de dictionnaires
            target_table: Table cible
            societe_code: Code societe
            primary_key_columns: Colonnes de cle primaire
            truncate_first: Si True, vide la table pour cette societe avant insert

        Returns:
            Statistiques d'ingestion
        """
        if not data:
            return {'rows_received': 0, 'rows_inserted': 0, 'message': 'Aucune donnee'}

        staging_table = f"_staging_{target_table}_{societe_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            df = pd.DataFrame(data)

            if 'Societe' not in df.columns:
                df.insert(0, 'Societe', societe_code)

            df['_etl_timestamp'] = datetime.now()

            conn = self.pool.get_connection(self.dwh_code)
            try:
                cursor = conn.cursor()

                # Creer la table de staging
                ingestion_service = DataIngestionService(self.dwh_code)
                await ingestion_service._ensure_table_exists(cursor, staging_table, df)

                # Bulk insert dans staging
                columns = df.columns.tolist()
                cols_str = ', '.join([f"[{col}]" for col in columns])
                placeholders = ', '.join(['?' for _ in columns])

                insert_query = f"INSERT INTO [{staging_table}] ({cols_str}) VALUES ({placeholders})"

                rows_inserted = 0
                for _, row in df.iterrows():
                    values = [None if pd.isna(v) else v for v in row.tolist()]
                    cursor.execute(insert_query, values)
                    rows_inserted += 1

                # Si truncate_first, supprimer les donnees existantes pour cette societe
                if truncate_first:
                    delete_query = f"DELETE FROM [{target_table}] WHERE Societe = ?"
                    cursor.execute(delete_query, (societe_code,))

                # MERGE depuis staging vers table cible
                merge_query = f"""
                    MERGE [{target_table}] AS t
                    USING [{staging_table}] AS s
                    ON ({' AND '.join([f"t.[{pk}] = s.[{pk}]" for pk in primary_key_columns])})
                    WHEN MATCHED THEN
                        UPDATE SET {', '.join([f"t.[{c}] = s.[{c}]" for c in columns if c not in primary_key_columns])}
                    WHEN NOT MATCHED THEN
                        INSERT ({cols_str})
                        VALUES ({', '.join([f"s.[{c}]" for c in columns])});
                """
                cursor.execute(merge_query)

                # Supprimer la table de staging
                cursor.execute(f"DROP TABLE [{staging_table}]")

                conn.commit()

                return {
                    'rows_received': len(data),
                    'rows_inserted': rows_inserted,
                    'rows_updated': 0,  # Non distingue avec MERGE
                    'rows_failed': 0,
                    'message': f"Bulk ingestion terminee: {rows_inserted} lignes"
                }
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Erreur bulk ingestion: {str(e)}")
            # Nettoyer la table de staging en cas d'erreur
            try:
                conn = self.pool.get_connection(self.dwh_code)
                try:
                    cursor = conn.cursor()
                    cursor.execute(f"DROP TABLE IF EXISTS [{staging_table}]")
                    conn.commit()
                finally:
                    conn.close()
            except:
                pass

            return {
                'rows_received': len(data),
                'rows_inserted': 0,
                'rows_updated': 0,
                'rows_failed': len(data),
                'message': f"Erreur: {str(e)}",
                'errors': [str(e)]
            }
