using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Gestionnaire des intervalles de synchronisation par table
    /// Determine quelles tables doivent etre synchronisees en fonction de leurs intervalles
    /// </summary>
    public class SyncScheduler
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;

        /// <summary>
        /// Dictionnaire thread-safe stockant la derniere sync par table
        /// </summary>
        private readonly ConcurrentDictionary<string, DateTime> _tableLastSync = new();

        /// <summary>
        /// Intervalle par defaut en minutes si non specifie
        /// </summary>
        public int DefaultIntervalMinutes { get; set; } = 5;

        /// <summary>
        /// Evenement de log
        /// </summary>
        public event EventHandler<string>? LogMessage;

        /// <summary>
        /// Obtient la liste des tables qui doivent etre synchronisees maintenant
        /// </summary>
        /// <param name="allTables">Toutes les tables configurees</param>
        /// <returns>Tables dont l'intervalle est atteint ou sync_now est true</returns>
        public List<TableConfig> GetTablesToSync(List<TableConfig> allTables)
        {
            var now = DateTime.Now;
            var tablesToSync = new List<TableConfig>();

            foreach (var table in allTables.Where(t => t.IsEnabled))
            {
                // Priorite 1: Flag sync_now (sync immediate)
                if (table.SyncNow)
                {
                    _logger.Info(LogCategory.ORCHESTRATION, $"Table {table.TableName}: sync_now=true, ajoutee");
                    tablesToSync.Add(table);
                    continue;
                }

                // Priorite 2: Flag force_full_reload
                if (table.ForceFullReload)
                {
                    _logger.Info(LogCategory.ORCHESTRATION, $"Table {table.TableName}: force_full_reload=true, ajoutee");
                    tablesToSync.Add(table);
                    continue;
                }

                // Priorite 3: Verification de l'intervalle
                var intervalMinutes = table.IntervalMinutes > 0 ? table.IntervalMinutes : DefaultIntervalMinutes;
                var lastSync = GetLastSync(table.TableName);

                if (lastSync == null)
                {
                    // Jamais synchronisee -> sync maintenant
                    _logger.Info(LogCategory.ORCHESTRATION, $"Table {table.TableName}: premiere sync, ajoutee");
                    tablesToSync.Add(table);
                }
                else if (now - lastSync.Value >= TimeSpan.FromMinutes(intervalMinutes))
                {
                    // Intervalle atteint
                    var elapsed = now - lastSync.Value;
                    _logger.Info(LogCategory.ORCHESTRATION, $"Table {table.TableName}: intervalle atteint ({elapsed.TotalMinutes:F1}min >= {intervalMinutes}min), ajoutee");
                    tablesToSync.Add(table);
                }
                else
                {
                    // Pas encore le moment
                    var remaining = TimeSpan.FromMinutes(intervalMinutes) - (now - lastSync.Value);
                    _logger.Debug(LogCategory.ORCHESTRATION, $"Table {table.TableName}: prochaine sync dans {remaining.TotalMinutes:F1}min");
                }
            }

            // Trier par priorite (plus petit = plus prioritaire)
            tablesToSync = tablesToSync.OrderBy(t => t.Priority).ToList();

            _logger.Info(LogCategory.ORCHESTRATION, $"Tables a synchroniser: {tablesToSync.Count}/{allTables.Count(t => t.IsEnabled)}");
            return tablesToSync;
        }

        /// <summary>
        /// Marque une table comme synchronisee maintenant
        /// </summary>
        /// <param name="tableName">Nom de la table</param>
        public void MarkTableSynced(string tableName)
        {
            var now = DateTime.Now;
            _tableLastSync.AddOrUpdate(tableName, now, (_, _) => now);
            _logger.Debug(LogCategory.ORCHESTRATION, $"Table {tableName} marquee synchronisee a {now:HH:mm:ss}");
        }

        /// <summary>
        /// Marque une table comme synchronisee a une date specifique
        /// </summary>
        /// <param name="tableName">Nom de la table</param>
        /// <param name="syncTime">Heure de sync</param>
        public void MarkTableSynced(string tableName, DateTime syncTime)
        {
            _tableLastSync.AddOrUpdate(tableName, syncTime, (_, _) => syncTime);
        }

        /// <summary>
        /// Obtient la derniere date de synchronisation d'une table
        /// </summary>
        /// <param name="tableName">Nom de la table</param>
        /// <returns>Date de derniere sync ou null si jamais synchronisee</returns>
        public DateTime? GetLastSync(string tableName)
        {
            if (_tableLastSync.TryGetValue(tableName, out var lastSync))
            {
                return lastSync;
            }
            return null;
        }

        /// <summary>
        /// Reset la date de sync d'une table (pour forcer une sync complete)
        /// </summary>
        /// <param name="tableName">Nom de la table</param>
        public void ResetTableSync(string tableName)
        {
            if (_tableLastSync.TryRemove(tableName, out _))
            {
                Log($"Table {tableName}: timestamp reset (prochaine sync sera complete)");
            }
        }

        /// <summary>
        /// Reset toutes les tables (pour forcer une sync complete globale)
        /// </summary>
        public void ResetAllTables()
        {
            var count = _tableLastSync.Count;
            _tableLastSync.Clear();
            Log($"Reset de {count} tables (prochaine sync sera complete pour toutes)");
        }

        /// <summary>
        /// Verifie si une table specifique doit etre synchronisee
        /// </summary>
        /// <param name="table">Configuration de la table</param>
        /// <returns>True si la table doit etre synchronisee</returns>
        public bool ShouldSyncTable(TableConfig table)
        {
            if (!table.IsEnabled)
                return false;

            if (table.SyncNow || table.ForceFullReload)
                return true;

            var lastSync = GetLastSync(table.TableName);
            if (lastSync == null)
                return true;

            var intervalMinutes = table.IntervalMinutes > 0 ? table.IntervalMinutes : DefaultIntervalMinutes;
            return DateTime.Now - lastSync.Value >= TimeSpan.FromMinutes(intervalMinutes);
        }

        /// <summary>
        /// Obtient le temps restant avant la prochaine sync d'une table
        /// </summary>
        /// <param name="table">Configuration de la table</param>
        /// <returns>Temps restant ou TimeSpan.Zero si sync immediate</returns>
        public TimeSpan GetTimeUntilNextSync(TableConfig table)
        {
            if (!table.IsEnabled)
                return TimeSpan.MaxValue;

            if (table.SyncNow || table.ForceFullReload)
                return TimeSpan.Zero;

            var lastSync = GetLastSync(table.TableName);
            if (lastSync == null)
                return TimeSpan.Zero;

            var intervalMinutes = table.IntervalMinutes > 0 ? table.IntervalMinutes : DefaultIntervalMinutes;
            var nextSync = lastSync.Value.AddMinutes(intervalMinutes);
            var remaining = nextSync - DateTime.Now;

            return remaining > TimeSpan.Zero ? remaining : TimeSpan.Zero;
        }

        /// <summary>
        /// Obtient le temps minimum avant la prochaine table a synchroniser
        /// </summary>
        /// <param name="tables">Liste des tables</param>
        /// <returns>Temps avant prochaine sync</returns>
        public TimeSpan GetTimeUntilNextTableSync(List<TableConfig> tables)
        {
            var minTime = TimeSpan.MaxValue;

            foreach (var table in tables.Where(t => t.IsEnabled))
            {
                var timeUntil = GetTimeUntilNextSync(table);
                if (timeUntil < minTime)
                {
                    minTime = timeUntil;
                }
            }

            return minTime == TimeSpan.MaxValue ? TimeSpan.FromMinutes(1) : minTime;
        }

        /// <summary>
        /// Importe les dates de derniere sync depuis les configurations de tables
        /// </summary>
        /// <param name="tables">Tables avec LastSyncDate</param>
        public void ImportLastSyncDates(List<TableConfig> tables)
        {
            foreach (var table in tables)
            {
                if (!string.IsNullOrEmpty(table.LastSyncDate) &&
                    DateTime.TryParse(table.LastSyncDate, out var lastSync))
                {
                    _tableLastSync.AddOrUpdate(table.TableName, lastSync, (_, _) => lastSync);
                    Log($"Table {table.TableName}: LastSyncDate importe = {lastSync:yyyy-MM-dd HH:mm:ss}");
                }
            }
        }

        /// <summary>
        /// Exporte les dates de derniere sync
        /// </summary>
        /// <returns>Dictionnaire table -> derniere sync</returns>
        public Dictionary<string, DateTime> ExportLastSyncDates()
        {
            return new Dictionary<string, DateTime>(_tableLastSync);
        }

        /// <summary>
        /// Obtient les statistiques du scheduler
        /// </summary>
        /// <returns>Statistiques</returns>
        public SyncSchedulerStats GetStats()
        {
            return new SyncSchedulerStats
            {
                TotalTablesTracked = _tableLastSync.Count,
                OldestSync = _tableLastSync.Values.Any() ? _tableLastSync.Values.Min() : null,
                NewestSync = _tableLastSync.Values.Any() ? _tableLastSync.Values.Max() : null
            };
        }

        private void Log(string message)
        {
            _logger.Info(LogCategory.ORCHESTRATION, message);
        }
    }

    /// <summary>
    /// Statistiques du scheduler
    /// </summary>
    public class SyncSchedulerStats
    {
        public int TotalTablesTracked { get; set; }
        public DateTime? OldestSync { get; set; }
        public DateTime? NewestSync { get; set; }
    }
}
