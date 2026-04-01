using System;
using System.Collections.Generic;
using System.Data.SqlClient;
using System.Diagnostics;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Service de pointage (reconciliation) entre les donnees source Sage et le DWH
    /// Compare les comptages et les cles primaires pour detecter les ecarts
    /// </summary>
    public class ReconciliationService
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;

        public event EventHandler<string>? ProgressChanged;

        /// <summary>
        /// Lance le pointage complet de toutes les tables d'un agent
        /// </summary>
        public async Task<ReconciliationReport> RunReconciliationAsync(
            AgentProfile agent,
            List<TableConfig> tables,
            CancellationToken ct = default)
        {
            var report = new ReconciliationReport
            {
                AgentName = agent.Name,
                SageDatabase = agent.SageDatabase,
                DwhDatabase = agent.DwhDatabase,
                StartTime = DateTime.Now
            };

            var sw = Stopwatch.StartNew();

            _logger.Info(LogCategory.POINTAGE, $"Debut pointage: {tables.Count} tables ({agent.SageDatabase} -> {agent.DwhDatabase})", agent.Name);
            ReportProgress($"Pointage {agent.Name}: 0/{tables.Count} tables...");

            using var extractor = new SageExtractor(
                agent.SageServer,
                agent.SageDatabase,
                agent.SageUsername,
                agent.SagePassword,
                agent.Name);

            using var dwhWriter = new DwhWriter(
                agent.DwhServer,
                agent.DwhDatabase,
                agent.DwhUsername ?? "sa",
                agent.DwhPassword ?? "",
                agent.Name);

            var enabledTables = tables.Where(t => t.IsEnabled).ToList();
            int index = 0;

            foreach (var table in enabledTables)
            {
                ct.ThrowIfCancellationRequested();
                index++;

                ReportProgress($"Pointage {agent.Name}: {index}/{enabledTables.Count} - {table.TableName}");

                var result = await ReconcileTableAsync(
                    extractor, dwhWriter, table, agent.DwhCode, ct);

                report.Tables.Add(result);

                if (result.Status == "OK")
                    report.TablesOk++;
                else if (result.Status == "ECART")
                    report.TablesWithDiffs++;
                else
                    report.TablesError++;
            }

            sw.Stop();
            report.TablesChecked = enabledTables.Count;
            report.EndTime = DateTime.Now;
            report.DurationSeconds = sw.Elapsed.TotalSeconds;

            _logger.Info(LogCategory.POINTAGE,
                $"Pointage termine: {report.TablesOk} OK, {report.TablesWithDiffs} ecarts, {report.TablesError} erreurs en {report.DurationSeconds:F1}s",
                agent.Name);

            ReportProgress($"Pointage {agent.Name} termine.");

            return report;
        }

        /// <summary>
        /// Pointage d'une seule table : comptage + comparaison PKs
        /// </summary>
        private async Task<TableReconciliationResult> ReconcileTableAsync(
            SageExtractor extractor,
            DwhWriter dwhWriter,
            TableConfig table,
            string societeCode,
            CancellationToken ct)
        {
            var result = new TableReconciliationResult
            {
                TableName = table.TableName
            };
            var sw = Stopwatch.StartNew();

            try
            {
                var targetTable = table.TargetTable ?? table.TableName;

                // 1. Comptage source (gere CTE et point-virgule)
                result.SourceCount = await CountSourceRowsAsync(
                    extractor, table.TableName, table.CustomQuery, ct);

                // 2. Comptage DWH
                result.DwhCount = await dwhWriter.CountRowsForSocieteAsync(
                    targetTable, societeCode, ct);

                result.CountDifference = result.SourceCount - result.DwhCount;

                _logger.Info(LogCategory.POINTAGE,
                    $"[{table.TableName}] Source: {result.SourceCount:N0} | DWH: {result.DwhCount:N0} | Ecart: {result.CountDifference:+#;-#;0}");

                // 3. Comparaison PKs si disponibles
                var primaryKeys = ParsePrimaryKeys(table.PrimaryKeyColumns);
                result.HasPrimaryKey = primaryKeys.Any();

                if (result.HasPrimaryKey)
                {
                    var sourceIds = await extractor.GetPrimaryKeyValuesAsync(
                        table.TableName, table.CustomQuery, primaryKeys, ct);

                    var dwhIds = await dwhWriter.GetExistingIdsAsync(
                        targetTable, primaryKeys, societeCode, ct);

                    // Serialiser les IDs source pour comparaison
                    var sourceIdSet = new HashSet<string>(sourceIds.Select(id => SerializeId(id)));

                    // Manquantes dans DWH (dans source mais pas dans DWH)
                    result.MissingInDwh = sourceIdSet.Count(id => !dwhIds.Contains(id));

                    // Orphelines dans DWH (dans DWH mais pas dans source)
                    result.OrphansInDwh = dwhIds.Count(id => !sourceIdSet.Contains(id));

                    if (result.MissingInDwh > 0 || result.OrphansInDwh > 0)
                    {
                        _logger.Warn(LogCategory.POINTAGE,
                            $"[{table.TableName}] PKs: {result.MissingInDwh} manquantes DWH, {result.OrphansInDwh} orphelines DWH");
                    }
                }

                // 4. Determiner le statut
                bool hasCountDiff = result.CountDifference != 0;
                bool hasPkDiff = result.MissingInDwh > 0 || result.OrphansInDwh > 0;
                result.Status = (hasCountDiff || hasPkDiff) ? "ECART" : "OK";
            }
            catch (Exception ex)
            {
                result.Status = "ERREUR";
                result.ErrorMessage = ex.Message;
                _logger.Error(LogCategory.POINTAGE, $"[{table.TableName}] Erreur: {ex.Message}", ex);
            }

            sw.Stop();
            result.DurationSeconds = sw.Elapsed.TotalSeconds;
            return result;
        }

        /// <summary>
        /// Compte les lignes source en gerant correctement les CTE et les point-virgules.
        /// Construit une requete COUNT(*) et l'execute via ExtractTableWithQueryAsync.
        /// </summary>
        private async Task<int> CountSourceRowsAsync(
            SageExtractor extractor,
            string tableName,
            string? customQuery,
            CancellationToken ct)
        {
            if (string.IsNullOrEmpty(customQuery))
            {
                return await extractor.CountRowsAsync(tableName, ct);
            }

            // Nettoyer le point-virgule terminal et BOM
            var cleanQuery = customQuery.TrimEnd().TrimEnd(';').TrimEnd();
            var trimmed = cleanQuery.Trim('\uFEFF', '\u200B', ' ', '\t', '\r', '\n');

            // Detecter si c'est un CTE (WITH ... AS ...)
            bool isCte = Regex.IsMatch(
                trimmed, @"^WITH\s+[\w\[\]]+\s+AS\s*\(",
                RegexOptions.IgnoreCase | RegexOptions.Singleline);

            string countQuery;

            if (isCte)
            {
                // CTE: trouver le SELECT principal et l'encapsuler
                var upperQuery = cleanQuery.ToUpper();
                int depth = 0;
                int lastSelectPos = -1;
                for (int i = 0; i < upperQuery.Length - 6; i++)
                {
                    if (upperQuery[i] == '(') depth++;
                    else if (upperQuery[i] == ')') depth--;
                    else if (depth == 0 && upperQuery.Substring(i, 6) == "SELECT")
                    {
                        bool isWordStart = (i == 0 || !char.IsLetterOrDigit(upperQuery[i - 1]));
                        bool isWordEnd = (i + 6 >= upperQuery.Length || !char.IsLetterOrDigit(upperQuery[i + 6]));
                        if (isWordStart && isWordEnd)
                            lastSelectPos = i;
                    }
                }

                if (lastSelectPos > 0)
                {
                    var ctePart = cleanQuery.Substring(0, lastSelectPos).TrimEnd().TrimEnd(',');
                    var selectPart = cleanQuery.Substring(lastSelectPos);
                    countQuery = $"{ctePart}, _count_cte AS (\n{selectPart}\n)\nSELECT COUNT(*) AS cnt FROM _count_cte";
                }
                else
                {
                    countQuery = $"SELECT COUNT(*) AS cnt FROM ({cleanQuery}) AS _count_src";
                }
            }
            else
            {
                countQuery = $"SELECT COUNT(*) AS cnt FROM ({cleanQuery}) AS _count_src";
            }

            // Executer via ExtractTableWithQueryAsync pour reutiliser la gestion de connexion
            var rows = await extractor.ExtractTableWithQueryAsync(countQuery, 1, null, ct);
            if (rows.Any() && rows[0].ContainsKey("cnt"))
            {
                return Convert.ToInt32(rows[0]["cnt"]);
            }
            return 0;
        }

        private List<string> ParsePrimaryKeys(string? primaryKeyColumns)
        {
            if (string.IsNullOrWhiteSpace(primaryKeyColumns))
                return new List<string>();

            return primaryKeyColumns
                .Split(',', StringSplitOptions.RemoveEmptyEntries)
                .Select(pk => UnescapeUnicode(pk.Trim().Trim('[', ']').Trim('"')))
                .Where(pk => !string.IsNullOrEmpty(pk))
                .ToList();
        }

        private static string UnescapeUnicode(string value)
        {
            return System.Text.RegularExpressions.Regex.Replace(
                value,
                @"\\u([0-9a-fA-F]{4})",
                m => ((char)Convert.ToInt32(m.Groups[1].Value, 16)).ToString());
        }

        private string SerializeId(object id)
        {
            if (id == null) return "";

            if (id is IEnumerable<object> list)
                return string.Join("|", list.Select(SerializeValue));

            return SerializeValue(id);
        }

        private string SerializeValue(object value)
        {
            if (value == null) return "";

            return value switch
            {
                DateTime dt => dt.ToString("yyyy-MM-ddTHH:mm:ss"),
                byte[] bytes => Convert.ToBase64String(bytes),
                _ => value.ToString() ?? ""
            };
        }

        private void ReportProgress(string message)
        {
            ProgressChanged?.Invoke(this, message);
        }
    }
}
