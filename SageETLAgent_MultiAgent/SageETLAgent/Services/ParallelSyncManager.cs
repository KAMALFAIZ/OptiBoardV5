using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Gestionnaire de synchronisation parallele pour plusieurs agents
    /// Mode: SQL-to-SQL direct (Sage -> DWH)
    /// </summary>
    public class ParallelSyncManager
    {
        private readonly string _serverUrl;
        private readonly SyncLogger _logger = SyncLogger.Instance;
        private CancellationTokenSource? _cts;

        public event EventHandler<SyncProgressEvent>? ProgressChanged;
        public event EventHandler<string>? LogMessage;
        public event EventHandler<AgentSyncResult>? AgentCompleted;
        public event EventHandler? AllCompleted;

        public bool IsRunning { get; private set; }

        public ParallelSyncManager(string serverUrl)
        {
            _serverUrl = serverUrl;
        }

        /// <summary>
        /// Lance la synchronisation parallele de tous les agents selectionnes
        /// </summary>
        public async Task SyncAllAsync(IEnumerable<AgentProfile> agents, int maxParallelism = 4)
        {
            if (IsRunning)
            {
                throw new InvalidOperationException("Une synchronisation est deja en cours");
            }

            var agentList = agents.Where(a => a.IsSelected && a.IsEnabled).ToList();
            if (!agentList.Any())
            {
                Log("Aucun agent selectionne");
                return;
            }

            IsRunning = true;
            _cts = new CancellationTokenSource();

            try
            {
                Log($"Demarrage sync parallele pour {agentList.Count} agent(s)...");

                var options = new ParallelOptions
                {
                    MaxDegreeOfParallelism = maxParallelism,
                    CancellationToken = _cts.Token
                };

                var results = new ConcurrentBag<AgentSyncResult>();

                await Parallel.ForEachAsync(agentList, options, async (agent, ct) =>
                {
                    var result = await SyncAgentAsync(agent, ct);
                    results.Add(result);
                    AgentCompleted?.Invoke(this, result);
                });

                // Resume
                var totalTables = results.Sum(r => r.TablesTotal);
                var successTables = results.Sum(r => r.TablesSuccess);
                var totalRows = results.Sum(r => r.TotalRows);

                Log($"=== SYNC TERMINEE ===");
                Log($"Agents: {results.Count}");
                Log($"Tables: {successTables}/{totalTables}");
                Log($"Lignes: {totalRows:N0}");

                AllCompleted?.Invoke(this, EventArgs.Empty);
            }
            catch (OperationCanceledException)
            {
                Log("Synchronisation annulee par l'utilisateur");
            }
            catch (Exception ex)
            {
                Log($"ERREUR: {ex.Message}");
            }
            finally
            {
                IsRunning = false;
                _cts?.Dispose();
                _cts = null;
            }
        }

        /// <summary>
        /// Synchronise un seul agent (mode SQL-to-SQL direct)
        /// </summary>
        public async Task<AgentSyncResult> SyncAgentAsync(AgentProfile agent, CancellationToken cancellationToken = default)
        {
            var result = new AgentSyncResult
            {
                AgentId = agent.AgentId,
                AgentName = agent.Name
            };

            var sw = Stopwatch.StartNew();

            try
            {
                Log($"[{agent.Name}] Demarrage sync (mode SQL-to-SQL)...");

                // Creer les clients
                using var apiClient = new ApiClient(_serverUrl);
                using var sageExtractor = new SageExtractor(
                    agent.SageServer,
                    agent.SageDatabase,
                    agent.SageUsername,
                    agent.SagePassword,
                    agent.Name
                );

                // Verifier la config DWH
                if (string.IsNullOrEmpty(agent.DwhServer) || string.IsNullOrEmpty(agent.DwhDatabase))
                {
                    throw new Exception("Configuration DWH incomplete (serveur ou base manquant)");
                }

                using var dwhWriter = new DwhWriter(
                    agent.DwhServer,
                    agent.DwhDatabase,
                    agent.DwhUsername ?? "sa",
                    agent.DwhPassword ?? "",
                    agent.Name
                );

                // Tester connexion Sage
                var (sageOk, sageMsg) = await sageExtractor.TestConnectionAsync();
                if (!sageOk)
                {
                    throw new Exception($"Connexion Sage echouee: {sageMsg}");
                }
                Log($"[{agent.Name}] Sage OK: {sageMsg}");

                // Tester connexion DWH
                var (dwhOk, dwhMsg) = await dwhWriter.TestConnectionAsync();
                if (!dwhOk)
                {
                    throw new Exception($"Connexion DWH echouee: {dwhMsg}");
                }
                Log($"[{agent.Name}] DWH OK: {dwhMsg}");

                // Charger les tables depuis l'API (si configurees)
                var tables = new List<TableConfig>();
                try
                {
                    tables = await apiClient.GetTablesAsync(agent.AgentId, agent.ApiKey);
                }
                catch (Exception ex)
                {
                    Log($"[{agent.Name}] ERREUR chargement tables depuis le serveur: {ex.Message}");
                }

                if (!tables.Any())
                {
                    Log($"[{agent.Name}] ERREUR: Aucune table retournee par le serveur. Verifiez la configuration de l'agent.");
                    result.Error = "Aucune table configuree sur le serveur";
                    return result;
                }

                result.TablesTotal = tables.Count;
                Log($"[{agent.Name}] {tables.Count} tables a synchroniser");

                // Synchroniser chaque table
                int tableIndex = 0;
                foreach (var table in tables.Where(t => t.IsEnabled).OrderBy(t => t.Priority))
                {
                    cancellationToken.ThrowIfCancellationRequested();

                    tableIndex++;
                    ReportProgress(agent, table.TableName, tableIndex, tables.Count, 0, "Extraction...");

                    try
                    {
                        var tableResult = await SyncTableDirectAsync(
                            agent,
                            sageExtractor,
                            dwhWriter,
                            table,
                            tableIndex,
                            tables.Count,
                            cancellationToken
                        );

                        result.TableResults.Add(tableResult);
                        if (tableResult.Success)
                        {
                            result.TablesSuccess++;
                            result.TotalRows += tableResult.RowsSent;
                        }
                    }
                    catch (Exception ex)
                    {
                        Log($"[{agent.Name}] ERREUR {table.TableName}: {ex.Message}");
                        result.TableResults.Add(new TableSyncResult
                        {
                            TableName = table.TableName,
                            Success = false,
                            Error = ex.Message
                        });
                    }
                }

                result.Success = result.TablesSuccess == result.TablesTotal;
                sw.Stop();
                result.DurationSeconds = sw.Elapsed.TotalSeconds;

                Log($"[{agent.Name}] TERMINE: {result.TablesSuccess}/{result.TablesTotal} tables, {result.TotalRows:N0} lignes en {result.DurationSeconds:F1}s");
            }
            catch (Exception ex)
            {
                result.Success = false;
                result.Error = ex.Message;
                Log($"[{agent.Name}] ECHEC: {ex.Message}");
            }

            return result;
        }

        /// <summary>
        /// Synchronise une table en mode SQL-to-SQL direct
        /// </summary>
        private async Task<TableSyncResult> SyncTableDirectAsync(
            AgentProfile agent,
            SageExtractor sageExtractor,
            DwhWriter dwhWriter,
            TableConfig table,
            int tableIndex,
            int totalTables,
            CancellationToken cancellationToken)
        {
            var sw = Stopwatch.StartNew();
            var result = new TableSyncResult { TableName = table.TableName };

            try
            {
                // Progress handler pour extraction
                var extractProgress = new Progress<int>(rows =>
                {
                    ReportProgress(agent, table.TableName, tableIndex, totalTables, rows, $"Extraction: {rows:N0} lignes");
                });

                // Extraire les donnees de Sage
                var data = await sageExtractor.ExtractTableAsync(
                    table.TableName,
                    table.CustomQuery,
                    5000,
                    extractProgress,
                    cancellationToken
                );

                if (!data.Any())
                {
                    Log($"[{agent.Name}] {table.TableName}: 0 lignes (skip)");
                    result.Success = true;
                    return result;
                }

                ReportProgress(agent, table.TableName, tableIndex, totalTables, data.Count, $"Ecriture DWH: {data.Count:N0} lignes...");

                // Ecrire dans le DWH
                var writeProgress = new Progress<int>(rows =>
                {
                    ReportProgress(agent, table.TableName, tableIndex, totalTables, rows, $"Ecrit: {rows:N0} lignes");
                });

                var rowsWritten = await dwhWriter.WriteTableDataAsync(
                    table.TableName,
                    data,
                    truncateFirst: true,
                    writeProgress,
                    cancellationToken
                );

                result.Success = true;
                result.RowsSent = rowsWritten;
                sw.Stop();
                result.DurationSeconds = sw.Elapsed.TotalSeconds;

                Log($"[{agent.Name}] {table.TableName}: {rowsWritten:N0} lignes OK ({result.DurationSeconds:F1}s)");

                ReportProgress(agent, table.TableName, tableIndex, totalTables, rowsWritten, "OK");
            }
            catch (Exception ex)
            {
                result.Success = false;
                result.Error = ex.Message;
                throw;
            }

            return result;
        }

        private void ReportProgress(AgentProfile agent, string tableName, int tableIndex, int totalTables, int rows, string message)
        {
            var progress = (double)tableIndex / totalTables * 100;

            ProgressChanged?.Invoke(this, new SyncProgressEvent
            {
                AgentId = agent.AgentId,
                AgentName = agent.Name,
                CurrentTable = tableName,
                TableIndex = tableIndex,
                TotalTables = totalTables,
                CurrentRows = rows,
                ProgressPercent = progress,
                Message = message
            });
        }

        private void Log(string message)
        {
            _logger.Info(LogCategory.ORCHESTRATION, message);
        }


        /// <summary>
        /// Annule la synchronisation en cours
        /// </summary>
        public void Cancel()
        {
            if (_cts != null && !_cts.IsCancellationRequested)
            {
                Log("Annulation demandee...");
                _cts.Cancel();
            }
        }
    }
}
