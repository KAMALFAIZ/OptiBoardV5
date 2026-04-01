using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Service de synchronisation continue
    /// Orchestre le heartbeat, les commandes et la synchronisation basee sur les intervalles
    /// </summary>
    public class ContinuousSyncService : IDisposable
    {
        private readonly string _serverUrl;
        private readonly AgentProfile _agent;
        private readonly SyncLogger _logger = SyncLogger.Instance;

        // Services
        private ApiClient? _apiClient;
        private HeartbeatService? _heartbeatService;
        private CommandProcessor? _commandProcessor;
        private SyncScheduler? _syncScheduler;
        private ConnectionManager? _connectionManager;
        private IncrementalSyncEngine? _incrementalEngine;
        private DeleteDetectionService? _deleteDetectionService;

        // State
        private readonly SyncState _syncState;
        private List<TableConfig> _tables = new();
        private CancellationTokenSource? _cts;
        private Task? _syncLoopTask;

        /// <summary>
        /// Intervalle de verification des tables (defaut: 15 secondes pour reactivite)
        /// Verifie toutes les 15s quelles tables ont atteint leur intervalle individuel
        /// </summary>
        public int SyncCheckIntervalMs { get; set; } = 15000;

        /// <summary>
        /// Nombre de tables a synchroniser en parallele (defaut: 3)
        /// </summary>
        public int MaxParallelTables { get; set; } = 3;

        /// <summary>
        /// Activer la sync parallele des tables
        /// </summary>
        public bool EnableParallelSync { get; set; } = true;

        /// <summary>
        /// Indique si le service est en cours d'execution
        /// </summary>
        public bool IsRunning => _syncLoopTask != null && !_syncLoopTask.IsCompleted;

        /// <summary>
        /// Indique si le service est en pause
        /// </summary>
        public bool IsPaused => _syncState.IsPaused;

        /// <summary>
        /// Etat actuel de la synchronisation
        /// </summary>
        public SyncState State => _syncState;

        #region Events

        /// <summary>
        /// Progression de la synchronisation
        /// </summary>
        public event EventHandler<SyncProgressEvent>? ProgressChanged;

        /// <summary>
        /// Evenement de log
        /// </summary>
        public event EventHandler<string>? LogMessage;

        /// <summary>
        /// Synchronisation d'un agent terminee
        /// </summary>
        public event EventHandler<AgentSyncResult>? SyncCompleted;

        /// <summary>
        /// Heartbeat envoye
        /// </summary>
        public event EventHandler? HeartbeatSent;

        /// <summary>
        /// Erreur survenue
        /// </summary>
        public event EventHandler<string>? ErrorOccurred;

        #endregion

        public ContinuousSyncService(string serverUrl, AgentProfile agent)
        {
            _serverUrl = serverUrl;
            _agent = agent;
            _syncState = new SyncState
            {
                AgentId = agent.AgentId,
                AgentName = agent.Name
            };
        }

        /// <summary>
        /// Demarre le service de synchronisation continue
        /// </summary>
        public async Task StartAsync()
        {
            if (IsRunning)
            {
                Log("Service deja en cours");
                return;
            }

            Log($"Demarrage service continu pour {_agent.Name}...");

            // Initialiser les services
            InitializeServices();

            // Charger la configuration des tables
            await LoadTablesConfigAsync();

            // Demarrer le heartbeat
            _heartbeatService?.Start();

            // Demarrer la boucle de sync
            _cts = new CancellationTokenSource();
            _syncLoopTask = SyncLoopAsync(_cts.Token);

            Log("Service continu demarre");
        }

        /// <summary>
        /// Arrete le service
        /// </summary>
        public async Task StopAsync()
        {
            if (!IsRunning)
                return;

            Log("Arret du service continu...");

            // Arreter la boucle de sync
            _cts?.Cancel();

            try
            {
                if (_syncLoopTask != null)
                {
                    await _syncLoopTask.WaitAsync(TimeSpan.FromSeconds(30));
                }
            }
            catch (OperationCanceledException) { }
            catch (TimeoutException)
            {
                Log("Timeout arret boucle sync");
            }

            // Arreter le heartbeat
            if (_heartbeatService != null)
            {
                await _heartbeatService.StopAsync();
            }

            // Cleanup
            CleanupServices();

            Log("Service continu arrete");
        }

        /// <summary>
        /// Met en pause la synchronisation (heartbeat continue)
        /// </summary>
        public void Pause()
        {
            if (_syncState.IsPaused)
                return;

            Log("Mise en pause");
            _syncState.IsPaused = true;
            _syncState.Status = "paused";
        }

        /// <summary>
        /// Reprend la synchronisation
        /// </summary>
        public void Resume()
        {
            if (!_syncState.IsPaused)
                return;

            Log("Reprise");
            _syncState.IsPaused = false;
            _syncState.Status = "active";
        }

        /// <summary>
        /// Force une synchronisation immediate de toutes les tables
        /// </summary>
        public void TriggerSyncNow()
        {
            Log("Sync immediate declenchee");
            foreach (var table in _tables)
            {
                table.SyncNow = true;
            }
        }

        /// <summary>
        /// Force une synchronisation d'une table specifique
        /// </summary>
        public void TriggerTableSync(string tableName)
        {
            var table = _tables.FirstOrDefault(t =>
                t.TableName.Equals(tableName, StringComparison.OrdinalIgnoreCase));

            if (table != null)
            {
                Log($"Sync table {tableName} declenchee");
                table.SyncNow = true;
            }
        }

        /// <summary>
        /// Force une resynchronisation complete (reset des timestamps)
        /// </summary>
        public void TriggerForceFullSync(string? tableName = null)
        {
            if (string.IsNullOrEmpty(tableName))
            {
                Log("Force full sync: TOUTES les tables");
                _syncScheduler?.ResetAllTables();
                foreach (var table in _tables)
                {
                    table.ForceFullReload = true;
                }
            }
            else
            {
                Log($"Force full sync: {tableName}");
                _syncScheduler?.ResetTableSync(tableName);
                var table = _tables.FirstOrDefault(t =>
                    t.TableName.Equals(tableName, StringComparison.OrdinalIgnoreCase));
                if (table != null)
                {
                    table.ForceFullReload = true;
                }
            }
        }

        /// <summary>
        /// Recharge la configuration des tables
        /// </summary>
        public async Task ReloadConfigAsync()
        {
            Log("Rechargement configuration...");
            await LoadTablesConfigAsync();
            Log($"Configuration rechargee: {_tables.Count} tables");
        }

        #region Private Methods

        private void InitializeServices()
        {
            _apiClient = new ApiClient(_serverUrl, _agent.DwhCode);
            _syncScheduler = new SyncScheduler();
            _connectionManager = new ConnectionManager();
            _incrementalEngine = new IncrementalSyncEngine();
            _deleteDetectionService = new DeleteDetectionService(_apiClient);

            // Command processor
            _commandProcessor = new CommandProcessor(_apiClient, _syncState);
            _commandProcessor.SyncNowRequested += (s, e) => TriggerSyncNow();
            _commandProcessor.SyncTableRequested += (s, tableName) => TriggerTableSync(tableName);
            _commandProcessor.PauseRequested += (s, e) => Pause();
            _commandProcessor.ResumeRequested += (s, e) => Resume();
            _commandProcessor.ReloadConfigRequested += async (s, e) => await ReloadConfigAsync();
            _commandProcessor.ForceFullSyncRequested += (s, tableName) => TriggerForceFullSync(tableName);
            // Heartbeat service
            _heartbeatService = new HeartbeatService(_apiClient, _syncState, _agent.AgentId, _agent.ApiKey);
            _heartbeatService.IntervalMs = _agent.SyncIntervalSeconds > 0
                ? Math.Min(30000, _agent.SyncIntervalSeconds * 1000 / 10)
                : 30000;
            _heartbeatService.CommandReceived += OnCommandReceived;
            _heartbeatService.HeartbeatSent += (s, e) => HeartbeatSent?.Invoke(this, EventArgs.Empty);
            _heartbeatService.HeartbeatError += (s, msg) => _logger.Error(LogCategory.COMMUNICATION, $"Heartbeat erreur: {msg}", agentName: _agent.Name);

            // Note: les services logguent directement via SyncLogger.Instance
            // Plus besoin de cablage LogMessage += (s, msg) => Log(msg)
        }

        private void CleanupServices()
        {
            _apiClient?.Dispose();
            _heartbeatService?.Dispose();
            _cts?.Dispose();

            _apiClient = null;
            _heartbeatService = null;
            _commandProcessor = null;
            _syncScheduler = null;
            _connectionManager = null;
            _incrementalEngine = null;
            _deleteDetectionService = null;
            _cts = null;
        }

        private async Task LoadTablesConfigAsync()
        {
            try
            {
                if (_apiClient == null) return;

                _tables = await _apiClient.GetTablesAsync(_agent.AgentId, _agent.ApiKey);

                if (!_tables.Any())
                {
                    _logger.Error(LogCategory.COMMUNICATION, "Aucune table retournee par le serveur. Verifiez la configuration.", agentName: _agent.Name);
                    return;
                }

                // Importer les dates de derniere sync
                _syncScheduler?.ImportLastSyncDates(_tables);

                Log($"Tables chargees: {_tables.Count}");
            }
            catch (Exception ex)
            {
                _logger.Error(LogCategory.COMMUNICATION, $"Chargement tables echoue: {ex.Message}", ex, _agent.Name);
            }
        }

        private async Task SyncLoopAsync(CancellationToken ct)
        {
            // Attendre un peu avant la premiere sync
            await Task.Delay(5000, ct);

            while (!ct.IsCancellationRequested)
            {
                if (!_syncState.IsPaused)
                {
                    try
                    {
                        await RunSyncCycleAsync(ct);
                        _connectionManager?.ResetErrors();
                    }
                    catch (OperationCanceledException)
                    {
                        break;
                    }
                    catch (Exception ex)
                    {
                        _connectionManager?.IncrementErrors();
                        _logger.Error(LogCategory.ORCHESTRATION, $"Erreur cycle sync: {ex.Message}", ex, _agent.Name);
                        ErrorOccurred?.Invoke(this, ex.Message);

                        // Backoff si trop d'erreurs
                        if (_connectionManager?.ShouldApplyBackoff() == true)
                        {
                            await _connectionManager.WaitBackoffIfNeededAsync(ct);
                        }
                    }
                }

                // Attendre avant le prochain cycle
                try
                {
                    await Task.Delay(SyncCheckIntervalMs, ct);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }
        }

        private async Task RunSyncCycleAsync(CancellationToken ct)
        {
            if (_syncScheduler == null || !_tables.Any())
                return;

            // Obtenir les tables a synchroniser
            var tablesToSync = _syncScheduler.GetTablesToSync(_tables);

            if (!tablesToSync.Any())
                return;

            Log($"Debut cycle: {tablesToSync.Count} table(s) a synchroniser" +
                (EnableParallelSync ? $" (parallele x{MaxParallelTables})" : " (sequentiel)"));
            _syncState.Status = "syncing";

            var result = new AgentSyncResult
            {
                AgentId = _agent.AgentId,
                AgentName = _agent.Name,
                TablesTotal = tablesToSync.Count
            };

            var sw = System.Diagnostics.Stopwatch.StartNew();

            if (EnableParallelSync && tablesToSync.Count > 1)
            {
                // Mode PARALLELE: synchroniser plusieurs tables en meme temps
                await SyncTablesParallelAsync(tablesToSync, result, ct);
            }
            else
            {
                // Mode SEQUENTIEL: synchroniser une table a la fois
                await SyncTablesSequentialAsync(tablesToSync, result, ct);
            }

            sw.Stop();
            result.DurationSeconds = sw.Elapsed.TotalSeconds;
            result.Success = result.TablesSuccess == result.TablesTotal;

            _syncState.Status = "active";
            _syncState.CurrentTask = null;
            _syncState.LastSync = DateTime.Now;

            Log($"Cycle termine: {result.TablesSuccess}/{result.TablesTotal} tables, {result.TotalRows:N0} lignes en {result.DurationSeconds:F1}s");

            SyncCompleted?.Invoke(this, result);
        }

        private async Task<TableSyncResult> SyncTableAsync(
            TableConfig table,
            int tableIndex,
            int totalTables,
            CancellationToken ct)
        {
            var result = new TableSyncResult { TableName = table.TableName };
            var sw = System.Diagnostics.Stopwatch.StartNew();

            try
            {
                using var sageExtractor = new SageExtractor(
                    _agent.SageServer,
                    _agent.SageDatabase,
                    _agent.SageUsername,
                    _agent.SagePassword,
                    _agent.Name);

                using var dwhWriter = new DwhWriter(
                    _agent.DwhServer,
                    _agent.DwhDatabase,
                    _agent.DwhUsername ?? "sa",
                    _agent.DwhPassword ?? "",
                    _agent.Name);

                // Obtenir la derniere sync
                var lastSync = table.ForceFullReload ? null : _syncScheduler?.GetLastSync(table.TableName);

                // Extraction avec support incremental
                ReportProgress(table.TableName, tableIndex, totalTables, 0, "Extraction...");

                var extractProgress = new Progress<int>(rows =>
                {
                    ReportProgress(table.TableName, tableIndex, totalTables, rows, $"Extraction: {rows:N0}");
                });

                List<Dictionary<string, object?>> data;

                if (_incrementalEngine != null &&
                    table.SyncType == "incremental" &&
                    !string.IsNullOrEmpty(table.TimestampColumn) &&
                    lastSync != null &&
                    !table.ForceFullReload)
                {
                    // Mode incremental
                    data = await _incrementalEngine.ExtractIncrementalAsync(
                        sageExtractor,
                        table,
                        lastSync,
                        extractProgress,
                        ct);
                }
                else
                {
                    // Mode full
                    data = await sageExtractor.ExtractTableAsync(
                        table.TableName,
                        table.CustomQuery,
                        table.BatchSize > 0 ? table.BatchSize : 5000,
                        extractProgress,
                        ct);
                }

                // Injecter DB_Id (identifiant client multi-tenant) dans chaque ligne
                if (data.Any() && !string.IsNullOrWhiteSpace(_agent.DwhCode))
                {
                    foreach (var row in data)
                        row["DB_Id"] = _agent.DwhCode;
                }

                // Determiner les PKs et le mode incremental AVANT le check 0 lignes
                // Car on a besoin de ces infos pour la detection des suppressions
                var pks = _deleteDetectionService?.ParsePrimaryKeys(table.PrimaryKeyColumns) ?? new List<string>();
                bool isIncremental = table.SyncType == "incremental" && !table.ForceFullReload;
                bool forceFullReload = table.ForceFullReload;

                int rowsWritten = 0;
                string strategy = "skip";

                if (!data.Any())
                {
                    Log($"[{table.TableName}] 0 lignes modifiees");
                }
                else
                {
                    // Ecriture dans le DWH
                    ReportProgress(table.TableName, tableIndex, totalTables, data.Count, "Ecriture DWH...");

                    var writeProgress = new Progress<int>(rows =>
                    {
                        ReportProgress(table.TableName, tableIndex, totalTables, rows, $"Ecrit: {rows:N0}");
                    });

                    // === STRATEGIE AUTO (comme Python agent-etl) ===
                    // Determiner la strategie: auto, merge, ou truncate_insert
                    // - truncate_insert: Plus robuste (DELETE societe + INSERT)
                    // - merge: Plus efficace pour syncs incrementales (MERGE SQL)
                    // - auto: Choisir automatiquement selon le contexte
                    strategy = "auto";
                    if (strategy == "auto")
                    {
                        if (forceFullReload || !isIncremental || data.Count > 100000 || !pks.Any())
                        {
                            strategy = "truncate_insert";
                        }
                        else
                        {
                            strategy = "merge";
                        }
                    }
                    // Meme en truncate_insert, si incremental avec peu de lignes, forcer MERGE
                    if (strategy == "truncate_insert" && isIncremental && pks.Any() && data.Count > 0 && data.Count < 10000)
                    {
                        strategy = "merge";
                        Log($"[{table.TableName}] Mode incremental avec {data.Count} lignes: MERGE au lieu de truncate_insert");
                    }

                    _logger.Info(LogCategory.TRANSFORMATION, $"Strategie: {strategy} (force_full={forceFullReload}, rows={data.Count}, incremental={isIncremental}, has_pk={pks.Any()})", _agent.Name, table.TableName);

                    if (strategy == "merge" && pks.Any())
                    {
                        // Mode MERGE pour incremental avec FALLBACK automatique
                        try
                        {
                            var (inserted, updated) = await dwhWriter.UpsertTableDataAsync(
                                table.TargetTable ?? table.TableName,
                                data,
                                pks,
                                _agent.DwhCode,
                                writeProgress,
                                ct);
                            rowsWritten = inserted + updated;

                            // Log detaille INSERT vs UPDATE
                            if (inserted > 0 || updated > 0)
                            {
                                _logger.Info(LogCategory.CHARGEMENT, $"MERGE: +{inserted} ajoutees, ~{updated} modifiees", _agent.Name, table.TableName);
                            }
                        }
                        catch (Exception mergeEx)
                        {
                            // === FALLBACK GLOBAL: MERGE echoue → DELETE societe + INSERT ===
                            _logger.Error(LogCategory.CHARGEMENT, $"MERGE echoue: {mergeEx.Message}", mergeEx, _agent.Name, table.TableName);
                            _logger.Warn(LogCategory.CHARGEMENT, $"Fallback → DELETE societe + INSERT...", _agent.Name, table.TableName);

                            ReportProgress(table.TableName, tableIndex, totalTables, 0, "Fallback DELETE+INSERT...");

                            rowsWritten = await dwhWriter.WriteTableDataForSocieteAsync(
                                table.TargetTable ?? table.TableName,
                                data,
                                _agent.DwhCode,
                                writeProgress,
                                ct);

                            _logger.Info(LogCategory.CHARGEMENT, $"Fallback DELETE+INSERT OK: {rowsWritten:N0} lignes", _agent.Name, table.TableName);
                        }
                    }
                    else
                    {
                        // Mode DELETE societe + INSERT (avec colonne societe)
                        rowsWritten = await dwhWriter.WriteTableDataForSocieteAsync(
                            table.TargetTable ?? table.TableName,
                            data,
                            _agent.DwhCode,
                            writeProgress,
                            ct);
                    }
                }

                // === DETECTION DES SUPPRESSIONS ===
                // IMPORTANT: Toujours executer MEME si 0 lignes modifiees!
                // Car supprimer une ligne dans Sage ne modifie PAS cbModification des autres lignes
                // → l'incremental retourne 0 lignes, mais la ligne supprimee est absente de la source
                // → il faut comparer les PKs source vs DWH pour detecter les orphelins
                bool shouldDetectDeletes = table.DeleteDetection || (isIncremental && pks.Any());
                if (shouldDetectDeletes && _deleteDetectionService != null && pks.Any())
                {
                    ReportProgress(table.TableName, tableIndex, totalTables, rowsWritten, "Detection suppressions...");

                    // Forcer temporairement DeleteDetection a true pour le service
                    var originalDeleteDetection = table.DeleteDetection;
                    table.DeleteDetection = true;

                    try
                    {
                        var deleted = await _deleteDetectionService.DetectAndDeleteDirectAsync(
                            table,
                            sageExtractor,
                            dwhWriter,
                            _agent.DwhCode,
                            ct);

                        if (deleted > 0)
                        {
                            _logger.Warn(LogCategory.DETECTION, $"-{deleted} supprimees (orphelines)", _agent.Name, table.TableName);
                        }
                    }
                    catch (OperationCanceledException)
                    {
                        throw;
                    }
                    catch (Exception detEx)
                    {
                        _logger.Warn(LogCategory.DETECTION, $"Detection suppressions ignoree (colonne PK introuvable ou requete incompatible): {detEx.Message}", _agent.Name, table.TableName);
                    }
                    finally
                    {
                        table.DeleteDetection = originalDeleteDetection;
                    }
                }

                result.Success = true;
                result.RowsSent = rowsWritten;
                sw.Stop();
                result.DurationSeconds = sw.Elapsed.TotalSeconds;

                ReportProgress(table.TableName, tableIndex, totalTables, rowsWritten, "OK");
                _logger.Info(LogCategory.CHARGEMENT, $"Strategie: {strategy} | {rowsWritten:N0} lignes en {result.DurationSeconds:F1}s", _agent.Name, table.TableName);
            }
            catch (Exception ex)
            {
                _logger.Error(LogCategory.ORCHESTRATION, $"Erreur sync: {ex.Message}", ex, _agent.Name, table.TableName);
                result.Success = false;
                result.Error = ex.Message;
                throw;
            }

            return result;
        }

        /// <summary>
        /// Synchronise les tables en parallele (optimise pour gros volumes)
        /// </summary>
        private async Task SyncTablesParallelAsync(
            List<TableConfig> tablesToSync,
            AgentSyncResult result,
            CancellationToken ct)
        {
            var semaphore = new SemaphoreSlim(MaxParallelTables);
            var tableIndex = 0;
            var lockObj = new object();

            var tasks = tablesToSync.Select(async table =>
            {
                await semaphore.WaitAsync(ct);
                try
                {
                    ct.ThrowIfCancellationRequested();

                    int currentIndex;
                    lock (lockObj)
                    {
                        currentIndex = ++tableIndex;
                    }

                    _syncState.CurrentTask = $"Sync {table.TableName} ({currentIndex}/{tablesToSync.Count})";
                    ReportProgress(table.TableName, currentIndex, tablesToSync.Count, 0, "Demarrage...");

                    try
                    {
                        var tableResult = await SyncTableAsync(table, currentIndex, tablesToSync.Count, ct);

                        lock (lockObj)
                        {
                            result.TableResults.Add(tableResult);

                            if (tableResult.Success)
                            {
                                result.TablesSuccess++;
                                result.TotalRows += tableResult.RowsSent;

                                _syncScheduler?.MarkTableSynced(table.TableName);
                                table.SyncNow = false;
                                table.ForceFullReload = false;
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        _logger.Error(LogCategory.ORCHESTRATION, $"Erreur sync: {ex.Message}", ex, _agent.Name, table.TableName);
                        lock (lockObj)
                        {
                            result.TableResults.Add(new TableSyncResult
                            {
                                TableName = table.TableName,
                                Success = false,
                                Error = ex.Message
                            });
                        }
                    }
                }
                finally
                {
                    semaphore.Release();
                }
            });

            await Task.WhenAll(tasks);
        }

        /// <summary>
        /// Synchronise les tables de maniere sequentielle (mode classique)
        /// </summary>
        private async Task SyncTablesSequentialAsync(
            List<TableConfig> tablesToSync,
            AgentSyncResult result,
            CancellationToken ct)
        {
            int tableIndex = 0;
            foreach (var table in tablesToSync)
            {
                ct.ThrowIfCancellationRequested();

                tableIndex++;
                _syncState.CurrentTask = $"Sync {table.TableName}";

                ReportProgress(table.TableName, tableIndex, tablesToSync.Count, 0, "Demarrage...");

                try
                {
                    var tableResult = await SyncTableAsync(table, tableIndex, tablesToSync.Count, ct);
                    result.TableResults.Add(tableResult);

                    if (tableResult.Success)
                    {
                        result.TablesSuccess++;
                        result.TotalRows += tableResult.RowsSent;

                        _syncScheduler?.MarkTableSynced(table.TableName);
                        table.SyncNow = false;
                        table.ForceFullReload = false;
                    }
                }
                catch (Exception ex)
                {
                    Log($"Erreur sync {table.TableName}: {ex.Message}");
                    result.TableResults.Add(new TableSyncResult
                    {
                        TableName = table.TableName,
                        Success = false,
                        Error = ex.Message
                    });
                }
            }
        }

        private void OnCommandReceived(object? sender, AgentCommand command)
        {
            if (_commandProcessor != null)
            {
                _ = _commandProcessor.ProcessCommandAsync(command);
            }
        }

        private void ReportProgress(string tableName, int tableIndex, int totalTables, int rows, string message)
        {
            var progress = (double)tableIndex / totalTables * 100;

            ProgressChanged?.Invoke(this, new SyncProgressEvent
            {
                AgentId = _agent.AgentId,
                AgentName = _agent.Name,
                CurrentTable = tableName,
                TableIndex = tableIndex,
                TotalTables = totalTables,
                CurrentRows = rows,
                ProgressPercent = progress,
                Message = message
            });
        }


        /// <summary>
        /// Log de compatibilite - redirige vers SyncLogger avec categorie ORCHESTRATION par defaut.
        /// Les appels specifiques dans SyncTableAsync utilisent les categories appropriees directement.
        /// </summary>
        private void Log(string message)
        {
            _logger.Info(LogCategory.ORCHESTRATION, message, _agent.Name);
        }

        #endregion

        public void Dispose()
        {
            _cts?.Cancel();
            CleanupServices();
        }
    }
}
