using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using SageETLAgent.Logging;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Ecrit les donnees directement dans le DWH (mode SQL-to-SQL)
    /// Supporte TRUNCATE+INSERT et MERGE (upsert)
    /// OPTIMISE: BatchSize augmente, connexion persistante, options turbo
    /// </summary>
    public class DwhWriter : IDisposable
    {
        private readonly string _connectionString;
        private SqlConnection? _persistentConnection;
        private readonly SyncLogger _logger = SyncLogger.Instance;
        private readonly string _agentName;

        // Configuration performance
        public int TurboBatchSize { get; set; } = 50000;  // Augmente de 5000 a 50000
        public int MergeBatchSize { get; set; } = 5000;   // Augmente de 1000 a 5000
        public bool UsePersistentConnection { get; set; } = true;

        public DwhWriter(string server, string database, string username, string password, string? agentName = null)
        {
            _agentName = agentName ?? "";
            // Utiliser SQL Auth si un username est fourni (meme si le password est vide)
            // Utiliser Windows Auth uniquement si le username est vide ET le serveur est local
            string auth;
            if (!string.IsNullOrWhiteSpace(username))
                auth = $"User Id={username};Password={password ?? ""}";
            else if (IsLocalServer(server))
                auth = "Integrated Security=True;Trusted_Connection=True";
            else
                auth = $"User Id={username};Password={password ?? ""}";
            _connectionString = $"Server={server};Database={database};{auth};" +
                              $"TrustServerCertificate=True;Connection Timeout=60;" +
                              $"Packet Size=32768;Application Name=SageETL_Turbo";
        }

        /// <summary>
        /// Retourne true si le serveur est local (., localhost, (local), tcp:localhost, 127.0.0.1)
        /// </summary>
        private static bool IsLocalServer(string server)
        {
            if (string.IsNullOrWhiteSpace(server)) return false;
            var s = server.Trim().ToLowerInvariant();
            return s == "." || s == "localhost" || s == "(local)" || s == "127.0.0.1"
                || s.StartsWith("tcp:localhost") || s.StartsWith("tcp:127.0.0.1")
                || s.StartsWith(".\\") || s.StartsWith("localhost\\");
        }

        /// <summary>
        /// Obtient une connexion (persistante ou nouvelle) avec reconnexion automatique
        /// </summary>
        private async Task<SqlConnection> GetConnectionAsync(CancellationToken ct = default)
        {
            if (UsePersistentConnection)
            {
                // Verifier si la connexion est valide
                if (_persistentConnection != null && _persistentConnection.State == System.Data.ConnectionState.Open)
                {
                    // Test rapide de la connexion
                    try
                    {
                        using var cmd = new SqlCommand("SELECT 1", _persistentConnection);
                        cmd.CommandTimeout = 5;
                        await cmd.ExecuteScalarAsync(ct);
                        return _persistentConnection;
                    }
                    catch (Exception ex)
                    {
                        // Connexion morte, on va la recreer
                        _logger.Debug(LogCategory.CONNEXION, "Connexion DWH persistante morte, recreation...", _agentName);
                        _persistentConnection?.Dispose();
                        _persistentConnection = null;
                    }
                }

                // Creer nouvelle connexion avec retry
                return await CreateConnectionWithRetryAsync(ct, persistent: true);
            }

            return await CreateConnectionWithRetryAsync(ct, persistent: false);
        }

        /// <summary>
        /// Cree une connexion avec retry en cas d'echec
        /// </summary>
        private async Task<SqlConnection> CreateConnectionWithRetryAsync(CancellationToken ct, bool persistent, int maxRetries = 3)
        {
            Exception? lastException = null;

            for (int attempt = 1; attempt <= maxRetries; attempt++)
            {
                try
                {
                    var conn = new SqlConnection(_connectionString);
                    await conn.OpenAsync(ct);

                    if (persistent)
                    {
                        _persistentConnection = conn;
                    }

                    return conn;
                }
                catch (Exception ex) when (attempt < maxRetries && IsTransientError(ex))
                {
                    lastException = ex;
                    // Attendre avant retry (backoff exponentiel)
                    await Task.Delay(1000 * attempt, ct);
                }
            }

            throw lastException ?? new Exception("Impossible de se connecter au DWH apres plusieurs tentatives");
        }

        /// <summary>
        /// Verifie si l'erreur est temporaire (connexion, reseau)
        /// </summary>
        private bool IsTransientError(Exception ex)
        {
            var message = ex.Message.ToLower();
            return message.Contains("communication link failure") ||
                   message.Contains("connection") ||
                   message.Contains("timeout") ||
                   message.Contains("network") ||
                   message.Contains("08s01") ||
                   message.Contains("tcp provider") ||
                   message.Contains("broken");
        }

        /// <summary>
        /// Verifie si l'erreur est un deadlock SQL Server (code 1205)
        /// Messages FR: "bloquée sur les ressources verrou", "victime"
        /// Messages EN: "deadlock victim", "transaction was deadlocked"
        /// </summary>
        private bool IsDeadlockError(Exception ex)
        {
            var message = ex.Message;
            if (ex is SqlException sqlEx && sqlEx.Number == 1205)
                return true;
            return message.Contains("victime", StringComparison.OrdinalIgnoreCase) ||
                   message.Contains("deadlock", StringComparison.OrdinalIgnoreCase) ||
                   message.Contains("bloquée", StringComparison.OrdinalIgnoreCase) ||
                   message.Contains("bloquee", StringComparison.OrdinalIgnoreCase) ||
                   message.Contains("réexécutez", StringComparison.OrdinalIgnoreCase) ||
                   message.Contains("reexecutez", StringComparison.OrdinalIgnoreCase) ||
                   message.Contains("1205", StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        /// Force la reconnexion
        /// </summary>
        public void ResetConnection()
        {
            _persistentConnection?.Dispose();
            _persistentConnection = null;
        }

        #region Connexion

        /// <summary>
        /// Teste la connexion au DWH
        /// </summary>
        public async Task<(bool Success, string Message)> TestConnectionAsync()
        {
            try
            {
                using var conn = new SqlConnection(_connectionString);
                await conn.OpenAsync();

                using var cmd = new SqlCommand("SELECT DB_NAME() AS CurrentDB", conn);
                var dbName = await cmd.ExecuteScalarAsync();

                return (true, $"Connecte a {dbName}");
            }
            catch (Exception ex)
            {
                return (false, ex.Message);
            }
        }

        #endregion

        #region Ecriture Full (TRUNCATE + INSERT)

        /// <summary>
        /// Ecrit les donnees dans une table du DWH (mode TRUNCATE + INSERT)
        /// OPTIMISE: BatchSize turbo, streaming pour gros volumes
        /// </summary>
        public async Task<int> WriteTableDataAsync(
            string tableName,
            List<Dictionary<string, object?>> data,
            bool truncateFirst = true,
            IProgress<int>? progress = null,
            CancellationToken cancellationToken = default)
        {
            if (!data.Any()) return 0;

            var conn = await GetConnectionAsync(cancellationToken);
            var ownsConnection = !UsePersistentConnection;

            try
            {
                // Creer la table si elle n'existe pas
                await EnsureTableExistsAsync(conn, tableName, data.First(), cancellationToken);

                // Truncate si demande
                if (truncateFirst)
                {
                    await TruncateTableAsync(conn, tableName, cancellationToken);
                }

                // Bulk insert via SqlBulkCopy avec options turbo
                var dataTable = ConvertToDataTable(tableName, data);

                using var bulkCopy = new SqlBulkCopy(conn, SqlBulkCopyOptions.TableLock | SqlBulkCopyOptions.UseInternalTransaction, null)
                {
                    DestinationTableName = $"[{tableName}]",
                    BatchSize = TurboBatchSize,  // 50000 au lieu de 5000
                    BulkCopyTimeout = 600,       // 10 minutes pour gros volumes
                    EnableStreaming = true       // Streaming pour memoire optimisee
                };

                // Mapper les colonnes
                foreach (DataColumn col in dataTable.Columns)
                {
                    bulkCopy.ColumnMappings.Add(col.ColumnName, col.ColumnName);
                }

                // Notification de progression
                bulkCopy.NotifyAfter = 10000;
                bulkCopy.SqlRowsCopied += (s, e) => progress?.Report((int)e.RowsCopied);

                await bulkCopy.WriteToServerAsync(dataTable, cancellationToken);

                progress?.Report(data.Count);
                return data.Count;
            }
            finally
            {
                if (ownsConnection)
                    conn.Dispose();
            }
        }

        /// <summary>
        /// Truncate ou DELETE une table
        /// </summary>
        private async Task TruncateTableAsync(
            SqlConnection conn,
            string tableName,
            CancellationToken ct)
        {
            try
            {
                using var truncateCmd = new SqlCommand($"TRUNCATE TABLE [{tableName}]", conn);
                await truncateCmd.ExecuteNonQueryAsync(ct);
            }
            catch (Exception ex)
            {
                // Si TRUNCATE echoue (FK), essayer DELETE
                _logger.Warn(LogCategory.CHARGEMENT, $"TRUNCATE echoue, fallback DELETE: {ex.Message}", _agentName, tableName);
                using var deleteCmd = new SqlCommand($"DELETE FROM [{tableName}]", conn);
                await deleteCmd.ExecuteNonQueryAsync(ct);
            }
        }

        /// <summary>
        /// Ecrit les donnees en mode DELETE societe + INSERT (sans TRUNCATE global)
        /// Utilise comme fallback quand MERGE echoue au niveau du service appelant
        /// </summary>
        public async Task<int> WriteTableDataForSocieteAsync(
            string tableName,
            List<Dictionary<string, object?>> data,
            string societeCode,
            IProgress<int>? progress = null,
            CancellationToken cancellationToken = default)
        {
            if (!data.Any()) return 0;

            var conn = await GetConnectionAsync(cancellationToken);
            var ownsConnection = !UsePersistentConnection;

            try
            {
                // Ajouter societe
                var dataWithSociete = AddSocieteColumn(data, societeCode);

                // Creer la table si elle n'existe pas
                await EnsureTableExistsAsync(conn, tableName, dataWithSociete.First(), cancellationToken);
                await EnsureSocieteColumnExistsAsync(conn, tableName, cancellationToken);
                await EnsureTargetColumnsExistAsync(conn, tableName, dataWithSociete.First(), cancellationToken);

                // DELETE par societe (pas TRUNCATE global pour ne pas affecter les autres societes)
                var deleteSql = $"DELETE FROM [{tableName}] WHERE [societe] = @societe";
                using (var deleteCmd = new SqlCommand(deleteSql, conn))
                {
                    deleteCmd.Parameters.AddWithValue("@societe", societeCode);
                    deleteCmd.CommandTimeout = 120;
                    await deleteCmd.ExecuteNonQueryAsync(cancellationToken);
                }

                // Bulk insert via SqlBulkCopy
                var dataTable = ConvertToDataTable(tableName, dataWithSociete);

                using var bulkCopy = new SqlBulkCopy(conn, SqlBulkCopyOptions.TableLock | SqlBulkCopyOptions.UseInternalTransaction, null)
                {
                    DestinationTableName = $"[{tableName}]",
                    BatchSize = TurboBatchSize,
                    BulkCopyTimeout = 600,
                    EnableStreaming = true
                };

                foreach (DataColumn col in dataTable.Columns)
                {
                    bulkCopy.ColumnMappings.Add(col.ColumnName, col.ColumnName);
                }

                bulkCopy.NotifyAfter = 10000;
                bulkCopy.SqlRowsCopied += (s, e) => progress?.Report((int)e.RowsCopied);

                await bulkCopy.WriteToServerAsync(dataTable, cancellationToken);

                progress?.Report(data.Count);
                return data.Count;
            }
            finally
            {
                if (ownsConnection)
                    conn.Dispose();
            }
        }

        #endregion

        #region Upsert (MERGE)

        /// <summary>
        /// Upsert les donnees (INSERT ou UPDATE selon la cle primaire)
        /// </summary>
        public async Task<(int Inserted, int Updated)> UpsertTableDataAsync(
            string tableName,
            List<Dictionary<string, object?>> data,
            List<string> primaryKeyColumns,
            string societeCode,
            IProgress<int>? progress = null,
            CancellationToken cancellationToken = default)
        {
            if (!data.Any() || !primaryKeyColumns.Any())
                return (0, 0);

            var conn = await GetConnectionAsync(cancellationToken);
            var ownsConnection = !UsePersistentConnection;

            try
            {
                // Ajouter la colonne societe AVANT EnsureTableExists
                var dataWithSociete = AddSocieteColumn(data, societeCode);

                // Assurer que societe est dans les PKs
                var pksWithSociete = EnsureSocieteInPrimaryKey(primaryKeyColumns);

                // Creer la table si elle n'existe pas (avec societe dans le sample)
                await EnsureTableExistsAsync(conn, tableName, dataWithSociete.First(), cancellationToken);

                // Si la table existait deja sans colonne societe, l'ajouter
                await EnsureSocieteColumnExistsAsync(conn, tableName, cancellationToken);

                // Nettoyer les lignes orphelines (societe IS NULL) qui causent des doublons
                // Ces lignes proviennent d'anciens syncs (Python agent) sans colonne societe
                try
                {
                    var cleanNullSql = $"DELETE FROM [{tableName}] WHERE [societe] IS NULL";
                    using var cleanCmd = new SqlCommand(cleanNullSql, conn);
                    cleanCmd.CommandTimeout = 60;
                    var cleanedRows = await cleanCmd.ExecuteNonQueryAsync(cancellationToken);
                    if (cleanedRows > 0)
                    {
                        _logger.Info(LogCategory.CHARGEMENT, $"Nettoyage: {cleanedRows} lignes orphelines (societe=NULL) supprimees", _agentName, tableName);
                    }
                }
                catch (Exception ex) { _logger.Debug(LogCategory.CHARGEMENT, $"Nettoyage societe=NULL non applicable (colonne absente)", _agentName, tableName); }

                // Dedupliquer par PK pour eviter l'erreur MERGE "UPDATE same row more than once"
                var cleanPKs = pksWithSociete.Select(CleanColumnName).ToList();
                var deduped = DeduplicateByPrimaryKey(dataWithSociete, cleanPKs);

            int totalInserted = 0;
            int totalUpdated = 0;

            // Traiter par batch de 5000 (augmente de 1000)
            int batchSize = MergeBatchSize;
            for (int i = 0; i < deduped.Count; i += batchSize)
            {
                var batch = deduped.Skip(i).Take(batchSize).ToList();

                var (inserted, updated) = await MergeBatchAsync(
                    conn,
                    tableName,
                    batch,
                    pksWithSociete,
                    cancellationToken);

                totalInserted += inserted;
                totalUpdated += updated;

                progress?.Report(i + batch.Count);
            }

            return (totalInserted, totalUpdated);
            }
            finally
            {
                if (ownsConnection)
                    conn.Dispose();
            }
        }

        /// <summary>
        /// Execute un MERGE pour un batch de donnees
        /// Retry automatique sur deadlock (max 3 tentatives, backoff 500ms/1s/2s)
        /// </summary>
        private async Task<(int Inserted, int Updated)> MergeBatchAsync(
            SqlConnection conn,
            string tableName,
            List<Dictionary<string, object?>> batch,
            List<string> primaryKeyColumns,
            CancellationToken ct)
        {
            if (!batch.Any()) return (0, 0);

            const int maxDeadlockRetries = 3;
            for (int deadlockAttempt = 1; deadlockAttempt <= maxDeadlockRetries; deadlockAttempt++)
            {
                try
                {
                    return await MergeBatchInternalAsync(conn, tableName, batch, primaryKeyColumns, ct);
                }
                catch (Exception ex) when (IsDeadlockError(ex) && deadlockAttempt < maxDeadlockRetries)
                {
                    var delay = 500 * deadlockAttempt; // 500ms, 1000ms
                    _logger.Warn(LogCategory.CHARGEMENT,
                        $"Deadlock detecte (tentative {deadlockAttempt}/{maxDeadlockRetries}), retry dans {delay}ms...",
                        _agentName, tableName);
                    await Task.Delay(delay, ct);
                }
            }
            // Derniere tentative sans catch deadlock
            return await MergeBatchInternalAsync(conn, tableName, batch, primaryKeyColumns, ct);
        }

        private async Task<(int Inserted, int Updated)> MergeBatchInternalAsync(
            SqlConnection conn,
            string tableName,
            List<Dictionary<string, object?>> batch,
            List<string> primaryKeyColumns,
            CancellationToken ct)
        {
            if (!batch.Any()) return (0, 0);

            var columns = batch.First().Keys.ToList();
            var cleanColumns = columns.Select(CleanColumnName).ToList();

            // Creer une table temporaire
            var tempTableName = $"#temp_{Guid.NewGuid():N}";

            // Essayer d'abord avec le schema de la table cible (types compatibles)
            // puis fallback sur l'inference depuis les donnees
            try
            {
                var createTempSql = await BuildTempTableFromTargetSchemaAsync(conn, tempTableName, tableName, columns, batch.First(), ct);
                using (var cmd = new SqlCommand(createTempSql, conn))
                {
                    await cmd.ExecuteNonQueryAsync(ct);
                }
            }
            catch (Exception ex)
            {
                // Fallback: creer la table temp basee sur les donnees
                _logger.Debug(LogCategory.CHARGEMENT, "Schema cible indisponible, fallback inference", _agentName, tableName);
                var createTempSql = BuildCreateTableSql(tempTableName, batch.First());
                using (var cmd = new SqlCommand(createTempSql, conn))
                {
                    await cmd.ExecuteNonQueryAsync(ct);
                }
            }

            // Bulk insert dans la table temp
            var dataTable = ConvertToDataTable(tempTableName, batch);
            using (var bulkCopy = new SqlBulkCopy(conn)
            {
                DestinationTableName = tempTableName,
                BatchSize = batch.Count,
                BulkCopyTimeout = 60
            })
            {
                foreach (DataColumn col in dataTable.Columns)
                {
                    bulkCopy.ColumnMappings.Add(col.ColumnName, col.ColumnName);
                }
                await bulkCopy.WriteToServerAsync(dataTable, ct);
            }

            // S'assurer que la table cible a toutes les colonnes necessaires
            await EnsureTargetColumnsExistAsync(conn, tableName, batch.First(), ct);

            // Verifier que toutes les colonnes PK existent dans les donnees (evite 2 erreurs SQL inutiles)
            var cleanPKsCheck = primaryKeyColumns.Select(CleanColumnName).ToList();
            var missingPKs = cleanPKsCheck
                .Where(pk => !cleanColumns.Any(c => string.Equals(c, pk, StringComparison.OrdinalIgnoreCase)))
                .ToList();
            if (missingPKs.Any())
                throw new InvalidOperationException(
                    $"Colonnes PK absentes dans les donnees source ({string.Join(", ", missingPKs)}). " +
                    $"Verifiez que l'alias SQL correspond exactement au nom de la cle primaire configuree.");

            // Construire et executer le MERGE avec fallback TRUNCATE+INSERT
            var mergeSql = BuildMergeSql(tableName, tempTableName, cleanColumns, primaryKeyColumns);
            int inserted = 0;
            int updated = 0;

            try
            {
                using var mergeCmd = new SqlCommand(mergeSql, conn);
                mergeCmd.CommandTimeout = 120;

                // MERGE avec OUTPUT $action retourne une ligne par action (INSERT/UPDATE)
                using var reader = await mergeCmd.ExecuteReaderAsync(ct);
                while (await reader.ReadAsync(ct))
                {
                    var action = reader.GetString(0);
                    if (action == "INSERT") inserted++;
                    else if (action == "UPDATE") updated++;
                }
            }
            catch (Exception ex) when (!IsTransientError(ex))
            {
                // === FALLBACK MERGE → TRUNCATE+INSERT (comme Python agent-etl) ===
                // Si MERGE echoue (erreur non-connexion), basculer sur DELETE+INSERT
                // Plus robuste pour les tables avec schemas complexes ou PK instables

                // Construire les colonnes pour INSERT
                var insertCols = string.Join(", ", cleanColumns.Select(c => $"[{c}]"));

                try
                {
                    // Etape 1: DELETE les lignes existantes qui matchent les PKs de la temp table
                    var cleanPKsForDelete = primaryKeyColumns.Select(CleanColumnName).ToList();
                    var deleteJoin = string.Join(" AND ",
                        cleanPKsForDelete.Select(pk => $"target.[{pk}] = source.[{pk}]"));

                    var deleteSql = $@"DELETE target FROM [{tableName}] AS target
                        WHERE EXISTS (
                            SELECT 1 FROM {tempTableName} AS source
                            WHERE {deleteJoin}
                        )";

                    using (var deleteCmd = new SqlCommand(deleteSql, conn))
                    {
                        deleteCmd.CommandTimeout = 120;
                        await deleteCmd.ExecuteNonQueryAsync(ct);
                    }

                    // Etape 2: INSERT depuis la table temporaire
                    var insertSql = $@"INSERT INTO [{tableName}] ({insertCols})
                        SELECT {insertCols} FROM {tempTableName}";

                    using (var insertCmd = new SqlCommand(insertSql, conn))
                    {
                        insertCmd.CommandTimeout = 120;
                        inserted = await insertCmd.ExecuteNonQueryAsync(ct);
                    }
                }
                catch (Exception fallbackEx) when (IsTransientError(fallbackEx))
                {
                    // Erreur de connexion pendant le fallback → propager
                    throw;
                }
                catch (Exception fallbackEx)
                {
                    // Le fallback a aussi echoue, propager l'erreur originale enrichie
                    throw new Exception($"MERGE echoue: {ex.Message} | Fallback DELETE+INSERT echoue: {fallbackEx.Message}", ex);
                }
            }

            // Nettoyer la table temp
            try
            {
                using (var dropCmd = new SqlCommand($"DROP TABLE {tempTableName}", conn))
                {
                    await dropCmd.ExecuteNonQueryAsync(ct);
                }
            }
            catch (Exception ex)
            {
                // Ignorer erreur de nettoyage temp table (sera nettoyee a la fin de session)
                _logger.Debug(LogCategory.CHARGEMENT, "Nettoyage table temporaire echoue (auto-nettoyage prevu)", _agentName);
            }

            return (inserted, updated);
        }

        /// <summary>
        /// Nettoie un nom de colonne en supprimant les crochets existants
        /// pour eviter le double-crochetage [[ ]]
        /// </summary>
        private string CleanColumnName(string columnName)
        {
            return columnName.Trim().Trim('[', ']').Trim('"');
        }

        /// <summary>
        /// Construit la requete MERGE
        /// </summary>
        private string BuildMergeSql(
            string targetTable,
            string sourceTable,
            List<string> columns,
            List<string> primaryKeyColumns)
        {
            var sb = new StringBuilder();

            // Nettoyer les noms de colonnes pour eviter le double-crochetage
            var cleanColumns = columns.Select(CleanColumnName).ToList();
            var cleanPKs = primaryKeyColumns.Select(CleanColumnName).ToList();

            // MERGE INTO target
            sb.AppendLine($"MERGE INTO [{targetTable}] AS target");
            sb.AppendLine($"USING {sourceTable} AS source");

            // ON (pk match)
            var onConditions = cleanPKs
                .Select(pk => $"target.[{pk}] = source.[{pk}]")
                .ToList();
            sb.AppendLine($"ON ({string.Join(" AND ", onConditions)})");

            // WHEN MATCHED THEN UPDATE
            var updateColumns = cleanColumns
                .Where(c => !cleanPKs.Contains(c, StringComparer.OrdinalIgnoreCase))
                .Select(c => $"[{c}] = source.[{c}]")
                .ToList();

            if (updateColumns.Any())
            {
                sb.AppendLine("WHEN MATCHED THEN UPDATE SET");
                sb.AppendLine($"    {string.Join(",\n    ", updateColumns)}");
            }

            // WHEN NOT MATCHED THEN INSERT
            var insertColumns = cleanColumns.Select(c => $"[{c}]").ToList();
            var insertValues = cleanColumns.Select(c => $"source.[{c}]").ToList();

            sb.AppendLine("WHEN NOT MATCHED THEN INSERT");
            sb.AppendLine($"    ({string.Join(", ", insertColumns)})");
            sb.AppendLine($"VALUES ({string.Join(", ", insertValues)})");

            // OUTPUT pour compter INSERT vs UPDATE
            sb.AppendLine("OUTPUT $action;");

            return sb.ToString();
        }

        #endregion

        #region Pointage

        /// <summary>
        /// Compte les lignes d'une table DWH filtrees par societe
        /// </summary>
        public async Task<int> CountRowsForSocieteAsync(
            string tableName,
            string societeCode,
            CancellationToken cancellationToken = default)
        {
            using var conn = new SqlConnection(_connectionString);
            await conn.OpenAsync(cancellationToken);

            using var cmd = new SqlCommand(
                $"SELECT COUNT(*) FROM [{tableName}] WHERE [societe] = @societe", conn);
            cmd.Parameters.AddWithValue("@societe", societeCode);
            cmd.CommandTimeout = 120;

            var result = await cmd.ExecuteScalarAsync(cancellationToken);
            return Convert.ToInt32(result);
        }

        #endregion

        #region Detection Suppressions

        /// <summary>
        /// Supprime les enregistrements orphelins (present dans DWH mais pas dans source)
        /// </summary>
        public async Task<int> DeleteOrphansAsync(
            string tableName,
            List<string> primaryKeyColumns,
            List<object> sourceIds,
            string societeCode,
            CancellationToken cancellationToken = default)
        {
            if (!sourceIds.Any() || !primaryKeyColumns.Any())
                return 0;

            const int maxRetries = 3;
            for (int attempt = 1; attempt <= maxRetries; attempt++)
            {
                try
                {
                    using var conn = new SqlConnection(_connectionString);
                    await conn.OpenAsync(cancellationToken);

                    var existingIds = await GetExistingIdsInternalAsync(conn, tableName, primaryKeyColumns, societeCode, cancellationToken);

                    var sourceIdSet = new HashSet<string>(sourceIds.Select(id => SerializeId(id)));
                    var orphanIds = existingIds.Where(id => !sourceIdSet.Contains(id)).ToList();

                    if (!orphanIds.Any())
                        return 0;

                    int totalDeleted = 0;
                    const int batchSize = 100;
                    for (int i = 0; i < orphanIds.Count; i += batchSize)
                    {
                        var batch = orphanIds.Skip(i).Take(batchSize).ToList();
                        totalDeleted += await DeleteBatchAsync(conn, tableName, primaryKeyColumns, batch, societeCode, cancellationToken);
                    }
                    return totalDeleted;
                }
                catch (Exception ex) when (IsDeadlockError(ex) && attempt < maxRetries)
                {
                    var delay = 300 * attempt;
                    _logger.Debug(LogCategory.DETECTION, $"Deadlock detection suppressions (tentative {attempt}/{maxRetries}), retry dans {delay}ms", _agentName, tableName);
                    await Task.Delay(delay, cancellationToken);
                }
            }
            return 0;
        }

        /// <summary>
        /// Obtient les IDs existants dans la destination
        /// </summary>
        public async Task<HashSet<string>> GetExistingIdsAsync(
            string tableName,
            List<string> primaryKeyColumns,
            string societeCode,
            CancellationToken cancellationToken = default)
        {
            using var conn = new SqlConnection(_connectionString);
            await conn.OpenAsync(cancellationToken);

            return await GetExistingIdsInternalAsync(conn, tableName, primaryKeyColumns, societeCode, cancellationToken);
        }

        private async Task<HashSet<string>> GetExistingIdsInternalAsync(
            SqlConnection conn,
            string tableName,
            List<string> primaryKeyColumns,
            string societeCode,
            CancellationToken ct)
        {
            var ids = new HashSet<string>();

            var cleanPKs = primaryKeyColumns.Select(CleanColumnName).ToList();
            var pkCols = string.Join(", ", cleanPKs.Select(pk => $"[{pk}]"));
            var query = $"SELECT {pkCols} FROM [{tableName}] WHERE [societe] = @societe";

            using var cmd = new SqlCommand(query, conn);
            cmd.Parameters.AddWithValue("@societe", societeCode);
            cmd.CommandTimeout = 120;

            try
            {
                using var reader = await cmd.ExecuteReaderAsync(ct);

                while (await reader.ReadAsync(ct))
                {
                    if (primaryKeyColumns.Count == 1)
                    {
                        var value = reader[0];
                        ids.Add(SerializeValue(value));
                    }
                    else
                    {
                        var values = new List<string>();
                        for (int i = 0; i < primaryKeyColumns.Count; i++)
                        {
                            values.Add(SerializeValue(reader[i]));
                        }
                        ids.Add(string.Join("|", values));
                    }
                }
            }
            catch (Exception ex)
            {
                // Table ou colonne n'existe pas
                _logger.Debug(LogCategory.DETECTION, "Table/colonne inexistante pour IDs", _agentName, tableName);
            }

            return ids;
        }

        private async Task<int> DeleteBatchAsync(
            SqlConnection conn,
            string tableName,
            List<string> primaryKeyColumns,
            List<string> orphanIds,
            string societeCode,
            CancellationToken ct)
        {
            var cleanPKs = primaryKeyColumns.Select(CleanColumnName).ToList();
            var conditions = new List<string>();

            foreach (var serializedId in orphanIds)
            {
                if (cleanPKs.Count == 1)
                {
                    conditions.Add($"[{cleanPKs[0]}] = '{EscapeSql(serializedId)}'");
                }
                else
                {
                    var values = serializedId.Split('|');
                    var pkConditions = new List<string>();
                    for (int i = 0; i < cleanPKs.Count && i < values.Length; i++)
                    {
                        pkConditions.Add($"[{cleanPKs[i]}] = '{EscapeSql(values[i])}'");
                    }
                    conditions.Add($"({string.Join(" AND ", pkConditions)})");
                }
            }

            var query = $"DELETE FROM [{tableName}] WHERE [societe] = @societe AND ({string.Join(" OR ", conditions)})";

            using var cmd = new SqlCommand(query, conn);
            cmd.Parameters.AddWithValue("@societe", societeCode);
            cmd.CommandTimeout = 60;

            return await cmd.ExecuteNonQueryAsync(ct);
        }

        private string SerializeId(object id)
        {
            if (id is IEnumerable<object> list)
            {
                return string.Join("|", list.Select(SerializeValue));
            }
            return SerializeValue(id);
        }

        private string SerializeValue(object value)
        {
            if (value == null || value == DBNull.Value)
                return "";

            return value switch
            {
                DateTime dt => dt.ToString("yyyy-MM-ddTHH:mm:ss"),
                byte[] bytes => Convert.ToBase64String(bytes),
                _ => value.ToString() ?? ""
            };
        }

        private string EscapeSql(string value)
        {
            return value.Replace("'", "''");
        }

        #endregion

        #region Helpers

        /// <summary>
        /// Cree la table si elle n'existe pas
        /// </summary>
        private async Task EnsureTableExistsAsync(
            SqlConnection conn,
            string tableName,
            Dictionary<string, object?> sampleRow,
            CancellationToken cancellationToken)
        {
            // Utiliser IF NOT EXISTS atomique pour eviter la race condition
            // (3 agents peuvent verifier en meme temps → tous voient "n'existe pas" → 2 echouent)
            var columns = new List<string>();
            foreach (var kvp in sampleRow)
            {
                var sqlType = GetSqlType(kvp.Value);
                columns.Add($"[{CleanColumnName(kvp.Key)}] {sqlType}");
            }
            var colsDef = string.Join(", ", columns);

            var createIfNotExistsSql = $@"
                IF NOT EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_NAME = @tableName
                )
                BEGIN
                    CREATE TABLE [{tableName}] ({colsDef})
                END";

            try
            {
                using var cmd = new SqlCommand(createIfNotExistsSql, conn);
                cmd.Parameters.AddWithValue("@tableName", tableName);
                cmd.CommandTimeout = 30;
                await cmd.ExecuteNonQueryAsync(cancellationToken);
            }
            catch (Exception ex) when (
                (ex is SqlException sqlEx2714 && sqlEx2714.Number == 2714) ||
                ex.Message.Contains("Il existe déjà un objet", StringComparison.OrdinalIgnoreCase) ||
                ex.Message.Contains("already an object named", StringComparison.OrdinalIgnoreCase))
            {
                // Une autre connexion a cree la table entre le IF NOT EXISTS et le CREATE → ignorer
                _logger.Debug(LogCategory.CHARGEMENT, $"Table {tableName} creee par un autre agent (race condition), OK", _agentName);
            }
        }

        private string BuildCreateTableSql(string tableName, Dictionary<string, object?> sampleRow)
        {
            var columns = new List<string>();
            foreach (var kvp in sampleRow)
            {
                var sqlType = GetSqlType(kvp.Value);
                columns.Add($"[{CleanColumnName(kvp.Key)}] {sqlType}");
            }
            return $"CREATE TABLE [{tableName}] ({string.Join(", ", columns)})";
        }

        /// <summary>
        /// Cree la table temp basee sur le schema de la table cible DWH
        /// Cela evite les problemes de types (ex: nvarchar infer au lieu de datetime)
        /// Fallback sur l'inference si la table cible n'existe pas encore
        /// </summary>
        private async Task<string> BuildTempTableFromTargetSchemaAsync(
            SqlConnection conn,
            string tempTableName,
            string targetTableName,
            List<string> dataColumns,
            Dictionary<string, object?> sampleRow,
            CancellationToken ct)
        {
            // Recuperer le schema de la table cible
            var targetSchema = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

            var schemaQuery = @"
                SELECT COLUMN_NAME,
                       DATA_TYPE + CASE
                           WHEN DATA_TYPE IN ('nvarchar','varchar','nchar','char') THEN
                               '(' + CASE WHEN CHARACTER_MAXIMUM_LENGTH = -1 THEN 'MAX'
                                     ELSE CAST(CHARACTER_MAXIMUM_LENGTH AS VARCHAR) END + ')'
                           WHEN DATA_TYPE IN ('decimal','numeric') THEN
                               '(' + CAST(NUMERIC_PRECISION AS VARCHAR) + ',' + CAST(NUMERIC_SCALE AS VARCHAR) + ')'
                           ELSE ''
                       END AS FULL_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = @tableName";

            try
            {
                using var cmd = new SqlCommand(schemaQuery, conn);
                cmd.Parameters.AddWithValue("@tableName", targetTableName);
                cmd.CommandTimeout = 30;

                using var reader = await cmd.ExecuteReaderAsync(ct);
                while (await reader.ReadAsync(ct))
                {
                    targetSchema[reader.GetString(0)] = reader.GetString(1);
                }
            }
            catch (Exception ex)
            {
                // Table cible n'existe pas encore, fallback
                _logger.Debug(LogCategory.CHARGEMENT, "Schema cible introuvable, fallback inference", _agentName, targetTableName);
            }

            // Construire le CREATE TABLE temp
            var columns = new List<string>();
            foreach (var key in dataColumns)
            {
                var cleanKey = CleanColumnName(key);

                if (targetSchema.TryGetValue(cleanKey, out var targetType))
                {
                    // Utiliser le type de la table cible
                    columns.Add($"[{cleanKey}] {targetType} NULL");
                }
                else
                {
                    // Colonne pas dans la cible (ex: societe ajoutee dynamiquement), inferer
                    var sqlType = sampleRow.TryGetValue(key, out var val) ? GetSqlType(val) : "NVARCHAR(MAX) NULL";
                    columns.Add($"[{cleanKey}] {sqlType}");
                }
            }

            return $"CREATE TABLE {tempTableName} ({string.Join(", ", columns)})";
        }

        /// <summary>
        /// Determine le type SQL a partir de la valeur
        /// </summary>
        private string GetSqlType(object? value)
        {
            if (value == null) return "NVARCHAR(MAX) NULL";

            return value switch
            {
                int => "INT NULL",
                long => "BIGINT NULL",
                short => "SMALLINT NULL",
                decimal => "DECIMAL(18,4) NULL",
                double => "FLOAT NULL",
                float => "REAL NULL",
                bool => "BIT NULL",
                DateTime => "DATETIME NULL",
                Guid => "UNIQUEIDENTIFIER NULL",
                byte[] => "VARBINARY(MAX) NULL",
                string s when s.Length <= 100 => "NVARCHAR(255) NULL",
                string s when s.Length <= 500 => "NVARCHAR(500) NULL",
                string s when s.Length <= 4000 => "NVARCHAR(4000) NULL",
                _ => "NVARCHAR(MAX) NULL"
            };
        }

        /// <summary>
        /// Convertit les donnees en DataTable pour SqlBulkCopy
        /// </summary>
        private DataTable ConvertToDataTable(string tableName, List<Dictionary<string, object?>> data)
        {
            var dt = new DataTable(tableName);

            if (!data.Any()) return dt;

            // Creer les colonnes a partir du premier element (noms nettoyes)
            var sample = data.First();
            var keyToClean = new Dictionary<string, string>();
            foreach (var key in sample.Keys)
            {
                var cleanKey = CleanColumnName(key);
                keyToClean[key] = cleanKey;

                var value = sample[key];
                var type = value?.GetType() ?? typeof(string);

                // Pour les types nullable, obtenir le type sous-jacent
                var underlyingType = Nullable.GetUnderlyingType(type) ?? type;

                dt.Columns.Add(cleanKey, underlyingType);
            }

            // Ajouter les lignes
            foreach (var row in data)
            {
                var dataRow = dt.NewRow();
                foreach (var key in row.Keys)
                {
                    var cleanKey = keyToClean.TryGetValue(key, out var ck) ? ck : CleanColumnName(key);
                    dataRow[cleanKey] = row[key] ?? DBNull.Value;
                }
                dt.Rows.Add(dataRow);
            }

            return dt;
        }

        /// <summary>
        /// S'assure que toutes les colonnes des donnees existent dans la table cible DWH
        /// Ajoute les colonnes manquantes avec un type par defaut
        /// </summary>
        private async Task EnsureTargetColumnsExistAsync(
            SqlConnection conn,
            string tableName,
            Dictionary<string, object?> sampleRow,
            CancellationToken ct)
        {
            // Recuperer les colonnes existantes
            var existingColumns = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var checkQuery = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = @tableName";

            try
            {
                using var checkCmd = new SqlCommand(checkQuery, conn);
                checkCmd.Parameters.AddWithValue("@tableName", tableName);
                using var reader = await checkCmd.ExecuteReaderAsync(ct);
                while (await reader.ReadAsync(ct))
                {
                    existingColumns.Add(reader.GetString(0));
                }
            }
            catch (Exception ex)
            {
                _logger.Debug(LogCategory.CHARGEMENT, "Lecture colonnes existantes echouee", _agentName, tableName);
                return; // Table n'existe pas
            }

            // Ajouter les colonnes manquantes
            foreach (var kvp in sampleRow)
            {
                var cleanKey = CleanColumnName(kvp.Key);
                if (!existingColumns.Contains(cleanKey))
                {
                    var sqlType = GetSqlType(kvp.Value);
                    try
                    {
                        var alterSql = $"ALTER TABLE [{tableName}] ADD [{cleanKey}] {sqlType}";
                        using var alterCmd = new SqlCommand(alterSql, conn);
                        await alterCmd.ExecuteNonQueryAsync(ct);
                    }
                    catch (Exception ex)
                    {
                        // Colonne existe peut-etre deja (race condition), ignorer
                        _logger.Debug(LogCategory.CHARGEMENT, "ALTER TABLE echoue (race condition probable)", _agentName, tableName);
                    }
                }
            }
        }

        /// <summary>
        /// S'assure que la colonne societe existe dans la table DWH
        /// (gere le cas ou la table a ete creee par WriteTableDataAsync sans societe)
        /// </summary>
        private async Task EnsureSocieteColumnExistsAsync(
            SqlConnection conn,
            string tableName,
            CancellationToken ct)
        {
            var checkQuery = @"
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = @tableName AND COLUMN_NAME = 'societe'";

            using var checkCmd = new SqlCommand(checkQuery, conn);
            checkCmd.Parameters.AddWithValue("@tableName", tableName);
            var exists = (int)await checkCmd.ExecuteScalarAsync(ct) > 0;

            if (!exists)
            {
                var alterSql = $"ALTER TABLE [{tableName}] ADD [societe] NVARCHAR(50) NULL";
                using var alterCmd = new SqlCommand(alterSql, conn);
                await alterCmd.ExecuteNonQueryAsync(ct);
            }
        }

        /// <summary>
        /// Ajoute la colonne societe aux donnees
        /// </summary>
        private List<Dictionary<string, object?>> AddSocieteColumn(
            List<Dictionary<string, object?>> data,
            string societeCode)
        {
            if (!data.Any())
                return data;

            // Verifier si societe existe deja
            if (data.First().ContainsKey("societe"))
                return data;

            // Ajouter societe a chaque ligne
            foreach (var row in data)
            {
                row["societe"] = societeCode;
            }

            return data;
        }

        /// <summary>
        /// Deduplique les donnees par cle primaire (garde la derniere occurrence)
        /// Evite l'erreur MERGE "UPDATE/DELETE the same row more than once"
        /// </summary>
        private List<Dictionary<string, object?>> DeduplicateByPrimaryKey(
            List<Dictionary<string, object?>> data,
            List<string> primaryKeyColumns)
        {
            if (!data.Any() || !primaryKeyColumns.Any())
                return data;

            var seen = new Dictionary<string, Dictionary<string, object?>>(StringComparer.OrdinalIgnoreCase);

            foreach (var row in data)
            {
                // Construire la cle composite
                var keyParts = new List<string>();
                foreach (var pk in primaryKeyColumns)
                {
                    // Chercher la valeur par nom exact ou par nom nettoye
                    object? val = null;
                    if (row.TryGetValue(pk, out val) || row.TryGetValue($"[{pk}]", out val))
                    {
                        keyParts.Add(val?.ToString() ?? "");
                    }
                    else
                    {
                        // Chercher case-insensitive
                        var matchKey = row.Keys.FirstOrDefault(k =>
                            CleanColumnName(k).Equals(pk, StringComparison.OrdinalIgnoreCase));
                        if (matchKey != null)
                            keyParts.Add(row[matchKey]?.ToString() ?? "");
                        else
                            keyParts.Add("");
                    }
                }
                var compositeKey = string.Join("|", keyParts);
                seen[compositeKey] = row; // Derniere occurrence gagne
            }

            return seen.Values.ToList();
        }

        /// <summary>
        /// S'assure que societe est dans les cles primaires
        /// </summary>
        private List<string> EnsureSocieteInPrimaryKey(List<string> primaryKeyColumns)
        {
            if (primaryKeyColumns.Contains("societe", StringComparer.OrdinalIgnoreCase))
                return primaryKeyColumns;

            var result = new List<string> { "societe" };
            result.AddRange(primaryKeyColumns);
            return result;
        }

        public void Dispose()
        {
            _persistentConnection?.Dispose();
            _persistentConnection = null;
        }

        #endregion
    }
}
