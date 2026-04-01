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
    /// Service de detection des suppressions
    /// Compare les IDs source avec la destination et supprime les orphelins
    /// </summary>
    public class DeleteDetectionService
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;
        private readonly ApiClient? _apiClient;

        public event EventHandler<string>? LogMessage;

        /// <summary>
        /// Constructeur pour mode API (envoie les IDs au serveur)
        /// </summary>
        public DeleteDetectionService(ApiClient apiClient)
        {
            _apiClient = apiClient;
        }

        /// <summary>
        /// Constructeur pour mode Direct (comparaison locale)
        /// </summary>
        public DeleteDetectionService()
        {
            _apiClient = null;
        }

        #region Mode API

        /// <summary>
        /// Detecte et supprime les orphelins via l'API serveur
        /// Le serveur compare les IDs et supprime les enregistrements manquants
        /// </summary>
        public async Task<int> DetectAndDeleteViaApiAsync(
            string agentId,
            string apiKey,
            TableConfig table,
            SageExtractor extractor,
            string societeCode,
            CancellationToken ct = default)
        {
            if (_apiClient == null)
            {
                Log($"[{table.TableName}] Mode API non disponible");
                return 0;
            }

            if (!table.DeleteDetection)
            {
                Log($"[{table.TableName}] Detection suppressions desactivee");
                return 0;
            }

            var primaryKeys = ParsePrimaryKeys(table.PrimaryKeyColumns);
            if (!primaryKeys.Any())
            {
                Log($"[{table.TableName}] Pas de cle primaire definie, detection impossible");
                return 0;
            }

            Log($"[{table.TableName}] Recuperation des IDs source...");

            // Recuperer tous les IDs de la source
            var sourceIds = await extractor.GetPrimaryKeyValuesAsync(
                table.TableName,
                table.CustomQuery,
                primaryKeys,
                ct);

            _logger.Info(LogCategory.DETECTION, $"[{table.TableName}] {sourceIds.Count} IDs source recuperes");

            if (!sourceIds.Any())
            {
                _logger.Debug(LogCategory.DETECTION, $"[{table.TableName}] Aucun ID source, skip detection");
                return 0;
            }

            // Envoyer au serveur pour comparaison
            var request = new DeleteDetectionRequest
            {
                TableName = table.TableName,
                TargetTable = table.TargetTable ?? table.TableName,
                SocieteCode = societeCode,
                PrimaryKey = primaryKeys,
                SourceIds = sourceIds,
                SourceCount = sourceIds.Count
            };

            Log($"[{table.TableName}] Envoi au serveur pour detection...");

            var response = await _apiClient.PushDeletionsAsync(agentId, apiKey, request);

            if (response.Success)
            {
                if (response.DeletedCount > 0)
                {
                    _logger.Warn(LogCategory.DETECTION, $"[{table.TableName}] {response.DeletedCount} enregistrements supprimes");
                }
                else
                {
                    _logger.Debug(LogCategory.DETECTION, $"[{table.TableName}] Aucune suppression detectee");
                }
                return response.DeletedCount;
            }
            else
            {
                _logger.Error(LogCategory.DETECTION, $"[{table.TableName}] Erreur detection: {response.Error}");
                return 0;
            }
        }

        #endregion

        #region Mode Direct

        /// <summary>
        /// Detecte et supprime les orphelins en mode direct (SQL-to-SQL)
        /// Compare localement les IDs source et destination
        /// </summary>
        public async Task<int> DetectAndDeleteDirectAsync(
            TableConfig table,
            SageExtractor extractor,
            DwhWriter dwhWriter,
            string societeCode,
            CancellationToken ct = default)
        {
            if (!table.DeleteDetection)
            {
                Log($"[{table.TableName}] Detection suppressions desactivee");
                return 0;
            }

            var primaryKeys = ParsePrimaryKeys(table.PrimaryKeyColumns);
            if (!primaryKeys.Any())
            {
                Log($"[{table.TableName}] Pas de cle primaire definie, detection impossible");
                return 0;
            }

            Log($"[{table.TableName}] Detection suppressions (mode direct)...");

            // Recuperer les IDs source
            var sourceIds = await extractor.GetPrimaryKeyValuesAsync(
                table.TableName,
                table.CustomQuery,
                primaryKeys,
                ct);

            _logger.Info(LogCategory.DETECTION, $"[{table.TableName}] {sourceIds.Count} IDs source");

            if (!sourceIds.Any())
            {
                _logger.Debug(LogCategory.DETECTION, $"[{table.TableName}] Aucun ID source, skip");
                return 0;
            }

            // Supprimer les orphelins dans le DWH
            var targetTable = table.TargetTable ?? table.TableName;
            var deleted = await dwhWriter.DeleteOrphansAsync(
                targetTable,
                primaryKeys,
                sourceIds,
                societeCode,
                ct);

            if (deleted > 0)
            {
                _logger.Warn(LogCategory.DETECTION, $"[{table.TableName}] {deleted} enregistrements supprimes du DWH");
            }
            else
            {
                _logger.Debug(LogCategory.DETECTION, $"[{table.TableName}] Aucune suppression");
            }

            return deleted;
        }

        /// <summary>
        /// Compare les IDs source et destination et retourne les orphelins
        /// </summary>
        public async Task<List<object>> FindOrphansAsync(
            TableConfig table,
            SageExtractor extractor,
            DwhWriter dwhWriter,
            string societeCode,
            CancellationToken ct = default)
        {
            var primaryKeys = ParsePrimaryKeys(table.PrimaryKeyColumns);
            if (!primaryKeys.Any())
                return new List<object>();

            // Recuperer les IDs source
            var sourceIds = await extractor.GetPrimaryKeyValuesAsync(
                table.TableName,
                table.CustomQuery,
                primaryKeys,
                ct);

            // Recuperer les IDs destination
            var targetTable = table.TargetTable ?? table.TableName;
            var destIds = await dwhWriter.GetExistingIdsAsync(
                targetTable,
                primaryKeys,
                societeCode,
                ct);

            // Serialiser les IDs source pour comparaison
            var sourceIdSet = new HashSet<string>(sourceIds.Select(SerializeId));

            // Trouver les orphelins (dans dest mais pas dans source)
            var orphans = destIds.Where(id => !sourceIdSet.Contains(id)).ToList();

            return orphans.Cast<object>().ToList();
        }

        #endregion

        #region Helpers

        /// <summary>
        /// Parse les cles primaires depuis une chaine CSV
        /// Gere les sequences Unicode litterales du style \u00b0 (° ) stockees en texte brut
        /// </summary>
        public List<string> ParsePrimaryKeys(string? primaryKeyColumns)
        {
            if (string.IsNullOrWhiteSpace(primaryKeyColumns))
                return new List<string>();

            return primaryKeyColumns
                .Split(',', StringSplitOptions.RemoveEmptyEntries)
                .Select(pk => UnescapeUnicode(pk.Trim().Trim('[', ']').Trim('"')))
                .Where(pk => !string.IsNullOrEmpty(pk))
                .ToList();
        }

        /// <summary>
        /// Convertit les sequences Unicode litterales \uXXXX en caracteres reels
        /// Ex: "N\u00b0 interne" → "N° interne"
        /// </summary>
        private static string UnescapeUnicode(string value)
        {
            return System.Text.RegularExpressions.Regex.Replace(
                value,
                @"\\u([0-9a-fA-F]{4})",
                m => ((char)Convert.ToInt32(m.Groups[1].Value, 16)).ToString());
        }

        /// <summary>
        /// Serialise un ID pour comparaison
        /// </summary>
        private string SerializeId(object id)
        {
            if (id == null)
                return "";

            if (id is IEnumerable<object> list)
            {
                return string.Join("|", list.Select(SerializeValue));
            }

            return SerializeValue(id);
        }

        private string SerializeValue(object value)
        {
            if (value == null)
                return "";

            return value switch
            {
                DateTime dt => dt.ToString("yyyy-MM-ddTHH:mm:ss"),
                byte[] bytes => Convert.ToBase64String(bytes),
                _ => value.ToString() ?? ""
            };
        }

        private void Log(string message)
        {
            _logger.Info(LogCategory.DETECTION, message);
        }

        #endregion
    }
}
