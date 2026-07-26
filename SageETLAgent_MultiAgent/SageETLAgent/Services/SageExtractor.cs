using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Extracteur de donnees Sage
    /// OPTIMISE: Connexion persistante, options turbo
    /// </summary>
    public class SageExtractor : IDisposable
    {
        private readonly string _connectionString;
        private readonly SyncLogger _logger = SyncLogger.Instance;
        private readonly string _agentName;
        private SqlConnection? _persistentConnection;

        public bool UsePersistentConnection { get; set; } = true;

        public bool ForceWindowsAuth { get; set; } = false;

        public SageExtractor(string server, string database, string username, string password, string? agentName = null, bool forceWindowsAuth = false)
        {
            _agentName = agentName ?? "";
            ForceWindowsAuth = forceWindowsAuth;
            // Windows Auth uniquement si explicitement demande OU si serveur local sans credentials
            bool useWindowsAuth = forceWindowsAuth
                || (IsLocalServer(server) && string.IsNullOrWhiteSpace(username));
            string auth = useWindowsAuth
                ? "Integrated Security=True;Trusted_Connection=True"
                : $"User Id={username};Password={password}";
            if (useWindowsAuth && !forceWindowsAuth && IsLocalServer(server))
                _logger.Warn(LogCategory.CONNEXION,
                    $"Serveur local '{server}' sans username: Windows Auth implicite. Definir ForceWindowsAuth=true pour etre explicite.",
                    _agentName);
            _connectionString = $"Server={server};Database={database};{auth};" +
                              $"TrustServerCertificate=True;Connection Timeout=60;" +
                              $"Packet Size=32768;Application Name=SageETL_Extractor";
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
                        _logger.Debug(LogCategory.CONNEXION, $"Connexion Sage persistante morte, recreation...", _agentName);
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
                    _logger.Warn(LogCategory.CONNEXION, $"Connexion Sage echouee (tentative {attempt}/{maxRetries}): {ex.Message}", _agentName);
                    await Task.Delay(1000 * attempt, ct);
                }
            }

            throw lastException ?? new Exception("Impossible de se connecter apres plusieurs tentatives");
        }

        /// <summary>
        /// Verifie si l'erreur est temporaire (transient)
        /// </summary>
        private bool IsTransientError(Exception ex)
        {
            var message = ex.Message.ToLower();
            return message.Contains("communication link failure") ||
                   message.Contains("connection") ||
                   message.Contains("timeout") ||
                   message.Contains("network") ||
                   message.Contains("08s01") ||
                   message.Contains("tcp provider");
        }

        /// <summary>
        /// Force la reconnexion
        /// </summary>
        public void ResetConnection()
        {
            _persistentConnection?.Dispose();
            _persistentConnection = null;
        }

        /// <summary>
        /// Teste la connexion a la base Sage
        /// </summary>
        public async Task<(bool Success, string Message)> TestConnectionAsync()
        {
            try
            {
                using var conn = new SqlConnection(_connectionString);
                await conn.OpenAsync();

                using var cmd = new SqlCommand("SELECT DB_NAME() AS CurrentDB", conn);
                var dbName = await cmd.ExecuteScalarAsync();

                _logger.Info(LogCategory.CONNEXION, $"Connexion Sage OK: {dbName}", _agentName);
                return (true, $"Connecte a {dbName}");
            }
            catch (Exception ex)
            {
                _logger.Error(LogCategory.CONNEXION, $"Test connexion Sage echoue: {ex.Message}", ex, _agentName);
                return (false, ex.Message);
            }
        }

        /// <summary>
        /// Extrait les donnees d'une table
        /// </summary>
        public async Task<List<Dictionary<string, object?>>> ExtractTableAsync(
            string tableName,
            string? customQuery = null,
            int batchSize = 5000,
            IProgress<int>? progress = null,
            CancellationToken cancellationToken = default)
        {
            var query = customQuery ?? $"SELECT * FROM [{tableName}]";
            return await ExtractTableWithQueryAsync(query, batchSize, progress, cancellationToken);
        }

        /// <summary>
        /// Extrait les donnees avec une requete personnalisee
        /// OPTIMISE: Connexion persistante, lecture rapide, retry automatique
        /// </summary>
        public async Task<List<Dictionary<string, object?>>> ExtractTableWithQueryAsync(
            string query,
            int batchSize = 5000,
            IProgress<int>? progress = null,
            CancellationToken cancellationToken = default)
        {
            // Retry en cas d'erreur de connexion
            for (int attempt = 1; attempt <= 3; attempt++)
            {
                try
                {
                    return await ExtractTableWithQueryInternalAsync(query, batchSize, progress, cancellationToken);
                }
                catch (Exception ex) when (attempt < 3 && IsTransientError(ex))
                {
                    _logger.Warn(LogCategory.EXTRACTION, $"Extraction echouee (tentative {attempt}/3): {ex.Message}", _agentName);
                    ResetConnection();
                    await Task.Delay(1000 * attempt, cancellationToken);
                }
            }

            // Derniere tentative sans catch
            return await ExtractTableWithQueryInternalAsync(query, batchSize, progress, cancellationToken);
        }

        private async Task<List<Dictionary<string, object?>>> ExtractTableWithQueryInternalAsync(
            string query,
            int batchSize,
            IProgress<int>? progress,
            CancellationToken cancellationToken)
        {
            var results = new List<Dictionary<string, object?>>();

            var conn = await GetConnectionAsync(cancellationToken);

            using var cmd = new SqlCommand(query, conn);
            cmd.CommandTimeout = 600; // 10 minutes pour gros volumes

            using var reader = await cmd.ExecuteReaderAsync(CommandBehavior.SequentialAccess, cancellationToken);

            var columns = new List<string>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                columns.Add(reader.GetName(i));
            }

            int rowCount = 0;
            while (await reader.ReadAsync(cancellationToken))
            {
                var row = new Dictionary<string, object?>();
                foreach (var col in columns)
                {
                    var value = reader[col];
                    row[col] = value == DBNull.Value ? null : value;
                }
                results.Add(row);

                rowCount++;
                if (rowCount % 1000 == 0)
                {
                    progress?.Report(rowCount);
                }
            }

            progress?.Report(rowCount);
            return results;
        }

        /// <summary>
        /// Extraction STREAMEE : lit le DataReader et invoque onBatchAsync tous les batchSize lignes,
        /// sans jamais accumuler toute la table en memoire (pic memoire = 1 lot). Le consommateur
        /// ecrit puis libere chaque lot.
        /// IMPORTANT: pas de retry inline (un lot deja consomme ne doit pas etre re-emis) — une erreur
        /// transitoire remonte a l'appelant, qui fera echouer la table pour ce cycle (retentee au suivant).
        /// </summary>
        public async Task ExtractTableStreamedAsync(
            string query,
            int batchSize,
            Func<List<Dictionary<string, object?>>, Task> onBatchAsync,
            IProgress<int>? progress = null,
            CancellationToken cancellationToken = default)
        {
            if (batchSize <= 0) batchSize = 5000;

            // Retry UNIQUEMENT a l'ouverture (avant toute ecriture) : recupere les transitoires
            // courants au demarrage de la requete, comme le chemin non streame. Des qu'un lot est
            // emis (donc potentiellement ecrit dans le DWH), plus aucun retry — re-emettre un lot
            // deja consomme provoquerait une double-ecriture.
            SqlCommand cmd = null!;
            SqlDataReader reader = null!;
            for (int attempt = 1; ; attempt++)
            {
                try
                {
                    var conn = await GetConnectionAsync(cancellationToken);
                    cmd = new SqlCommand(query, conn) { CommandTimeout = 600 }; // 10 min pour gros volumes
                    reader = await cmd.ExecuteReaderAsync(CommandBehavior.SequentialAccess, cancellationToken);
                    break;
                }
                catch (Exception ex) when (attempt < 3 && IsTransientError(ex))
                {
                    cmd?.Dispose();
                    _logger.Warn(LogCategory.EXTRACTION,
                        $"Extraction streamee: ouverture echouee (tentative {attempt}/3): {ex.Message}", _agentName);
                    ResetConnection();
                    await Task.Delay(1000 * attempt, cancellationToken);
                }
            }

            using (cmd)
            using (reader)
            {
                var columns = new List<string>();
                for (int i = 0; i < reader.FieldCount; i++)
                {
                    columns.Add(reader.GetName(i));
                }

                var batch = new List<Dictionary<string, object?>>(batchSize);
                int rowCount = 0;

                while (await reader.ReadAsync(cancellationToken))
                {
                    var row = new Dictionary<string, object?>();
                    foreach (var col in columns)
                    {
                        var value = reader[col];
                        row[col] = value == DBNull.Value ? null : value;
                    }
                    batch.Add(row);
                    rowCount++;

                    if (batch.Count >= batchSize)
                    {
                        await onBatchAsync(batch);
                        progress?.Report(rowCount);
                        // Nouveau lot : l'ancien pourra etre collecte apres consommation
                        batch = new List<Dictionary<string, object?>>(batchSize);
                    }
                }

                // Dernier lot partiel
                if (batch.Count > 0)
                {
                    await onBatchAsync(batch);
                }

                progress?.Report(rowCount);
            }
        }

        /// <summary>
        /// Extrait les donnees avec un filtre WHERE additionnel
        /// </summary>
        public async Task<List<Dictionary<string, object?>>> ExtractTableWithFilterAsync(
            string tableName,
            string? customQuery,
            string? whereClause,
            int batchSize = 5000,
            IProgress<int>? progress = null,
            CancellationToken cancellationToken = default)
        {
            var baseQuery = customQuery ?? $"SELECT * FROM [{tableName}]";

            // Ajouter le filtre WHERE si fourni
            if (!string.IsNullOrEmpty(whereClause))
            {
                if (baseQuery.Contains("WHERE", StringComparison.OrdinalIgnoreCase))
                {
                    baseQuery += $" AND {whereClause}";
                }
                else
                {
                    baseQuery += $" WHERE {whereClause}";
                }
            }

            return await ExtractTableWithQueryAsync(baseQuery, batchSize, progress, cancellationToken);
        }

        /// <summary>
        /// Extrait uniquement les valeurs des cles primaires.
        ///
        /// STRATEGIE ROBUSTE:
        ///   Les colonnes PK peuvent contenir des caracteres Unicode (ex: "N° interne", "N° Pièce").
        ///   Utiliser ces noms comme identificateurs SQL dans un SELECT externe cause des erreurs:
        ///     - "Nom de colonne non valide : 'N° interne'"
        ///     - "Le identificateur qui commence par '[N° ...] FROM...' est trop long"
        ///
        ///   SOLUTION: au lieu de referencer le nom de colonne Unicode dans un SELECT externe,
        ///   on execute la requete source complete et on lit les colonnes PK PAR POSITION
        ///   apres avoir identifie leur indice via reader.GetName() (comparaison C# native).
        ///   Cette approche fonctionne pour toutes les requetes quelle que soit leur complexite.
        /// </summary>
        public async Task<List<object>> GetPrimaryKeyValuesAsync(
            string tableName,
            string? customQuery,
            List<string> primaryKeyColumns,
            CancellationToken cancellationToken = default)
        {
            if (!primaryKeyColumns.Any())
                return new List<object>();

            var results = new List<object>();

            // Reutiliser la connexion persistante pour beneficier des parametres de session Sage 100
            // (QUOTED_IDENTIFIER, ANSI_NULLS, etc.) etablis par la connexion principale.
            // Une connexion fraiche peut echouer sur les requetes Sage 100 avec syntaxe JOIN imbriquee
            // (ex: "FROM T AS alias INNER JOIN T2 INNER JOIN T3 ON ... ON ...") avec l'erreur
            // "Nom de colonne non valide : 'AS'" car le parseur SQL Server interprete AS comme colonne.
            var conn = await GetConnectionAsync(cancellationToken);
            var ownsConnection = !UsePersistentConnection;

            try
            {

            string query;
            bool readByPosition = false; // true = lire par indice via GetName, false = lire reader[0..n]
            List<int> pkColumnIndices = new List<int>(); // indices dans le reader (pour readByPosition)

            if (!string.IsNullOrEmpty(customQuery))
            {
                // Nettoyer le point-virgule final
                var cleanQuery = customQuery.TrimEnd().TrimEnd(';').TrimEnd();

                // Verifier si c'est un CTE (WITH ... AS ...)
                var trimmed = cleanQuery.Trim('\uFEFF', '\u200B', ' ', '\t', '\r', '\n');
                bool isCte = System.Text.RegularExpressions.Regex.IsMatch(
                    trimmed, @"^WITH\s+[\w\[\]]+\s+AS\s*\(",
                    System.Text.RegularExpressions.RegexOptions.IgnoreCase | System.Text.RegularExpressions.RegexOptions.Singleline);

                // Noms de colonnes PK nettoyes (sans crochets)
                var pkNames = primaryKeyColumns.Select(pk => pk.Trim('[', ']')).ToList();

                // Chercher l'expression source reelle pour chaque PK
                // (ex: "DL_No" pour l'alias "N° interne", "F_DOCENTETE.cbMarq" pour "N° interne", etc.)
                var pkExpressions = pkNames.Select(pkName => FindPkSourceExpression(cleanQuery, pkName)).ToList();

                if (isCte)
                {
                    // CTE: trouver le SELECT principal (dernier SELECT au niveau depth=0)
                    var upperQuery = cleanQuery.ToUpperInvariant();
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
                        var ctePart = cleanQuery.Substring(0, lastSelectPos).TrimEnd().TrimEnd(',').TrimEnd();
                        var outerSelect = cleanQuery.Substring(lastSelectPos);

                        // Trouver le FROM du SELECT externe (au niveau depth=0 dans outerSelect)
                        int fromPos = FindFromPositionAtDepth0(outerSelect);
                        // Verifier que le FROM n'est pas une sous-requete (FROM (SELECT ...))
                        bool outerFromIsSubquery = false;
                        if (fromPos > 0)
                        {
                            var afterFrom = outerSelect.Substring(fromPos + 4).TrimStart();
                            outerFromIsSubquery = afterFrom.StartsWith("(");
                        }
                        if (fromPos > 0 && pkExpressions.All(e => e != null) && !outerFromIsSubquery)
                        {
                            // Remplacer le SELECT externe par DISTINCT avec expressions reelles + aliases safe
                            var fromClause = RemoveTrailingOrderByStr(outerSelect.Substring(fromPos));
                            var innerCols = pkExpressions.Select((e, i) => $"{e} AS [_pk_col_{i}]").ToList();
                            var outerCols = Enumerable.Range(0, pkNames.Count).Select(i => $"[_pk_col_{i}]").ToList();
                            // Wrap outer SELECT in new CTE pour isoler les alias
                            query = $"{ctePart}\n, _pk_final AS (\n  SELECT DISTINCT {string.Join(", ", innerCols)} {fromClause}\n)\nSELECT {string.Join(", ", outerCols)} FROM _pk_final";
                        }
                        else if (lastSelectPos > 0)
                        {
                            // Fallback CTE: utiliser la requete source complete et lire par position
                            query = cleanQuery;
                            readByPosition = true;
                        }
                        else
                        {
                            query = cleanQuery;
                            readByPosition = true;
                        }
                    }
                    else
                    {
                        query = cleanQuery;
                        readByPosition = true;
                    }
                }
                else
                {
                    // Non-CTE: tenter de remplacer le SELECT complet par DISTINCT pk_expression
                    int fromPos = FindFromPositionAtDepth0(cleanQuery);

                    // Verifier que le FROM ne pointe pas vers une sous-requete (FROM (SELECT ...))
                    // Dans ce cas, l'expression trouvee dans la sous-requete n'est pas accessible
                    // directement depuis le FROM externe -> fallback readByPosition
                    bool fromIsSubquery = false;
                    if (fromPos > 0)
                    {
                        var afterFrom = cleanQuery.Substring(fromPos + 4).TrimStart(); // skip "from" + whitespace
                        fromIsSubquery = afterFrom.StartsWith("(");
                    }

                    if (fromPos > 0 && pkExpressions.All(e => e != null) && !fromIsSubquery)
                    {
                        // On a les expressions sources reelles et le FROM clause (sans sous-requete)
                        var fromClause = RemoveTrailingOrderByStr(cleanQuery.Substring(fromPos));
                        var innerCols = pkExpressions.Select((e, i) => $"{e} AS [_pk_col_{i}]").ToList();
                        var outerCols = Enumerable.Range(0, pkNames.Count).Select(i => $"[_pk_col_{i}]").ToList();
                        // Double wrapping: inner remplace les colonnes SELECT, outer utilise aliases safe ASCII
                        var innerQuery = $"SELECT DISTINCT {string.Join(", ", innerCols)} {fromClause}";
                        query = $"SELECT {string.Join(", ", outerCols)} FROM ({innerQuery}) AS _pk_wrap";
                    }
                    else
                    {
                        // Fallback: executer la requete source complete et lire par position (nom de colonne)
                        // Evite tout probleme d'identifiant Unicode dans le SQL genere
                        var cleanQueryNoOrderBy = RemoveTrailingOrderByStr(cleanQuery);
                        query = cleanQueryNoOrderBy;
                        readByPosition = true;
                    }
                }
            }
            else
            {
                // Requete simple (pas de custom query)
                // Pour les tables simples, les noms de colonnes PK sont generalement ASCII
                var pkColumnsStr = string.Join(", ", primaryKeyColumns.Select(pk => $"[{pk.Trim('[', ']')}]"));
                query = $"SELECT DISTINCT {pkColumnsStr} FROM [{tableName}]";
            }

            // Si la requete generee est invalide (ex: 'AS' invalide), fallback readByPosition
            SqlDataReader reader;
            try
            {
                var cmd = new SqlCommand(query, conn) { CommandTimeout = 300 };
                reader = await cmd.ExecuteReaderAsync(cancellationToken);
            }
            catch (SqlException sqlEx) when (!readByPosition && !string.IsNullOrEmpty(customQuery))
            {
                // La requete generee est invalide — retenter avec la requete source complete
                _logger.Debug(LogCategory.DETECTION,
                    $"[PK Retry] Requete generee invalide ({sqlEx.Message}), fallback lecture integrale");
                var cleanQueryNoOrderBy = RemoveTrailingOrderByStr(
                    customQuery.TrimEnd().TrimEnd(';').TrimEnd());
                var cmd2 = new SqlCommand(cleanQueryNoOrderBy, conn) { CommandTimeout = 300 };
                reader = await cmd2.ExecuteReaderAsync(cancellationToken);
                readByPosition = true;
                // Recalculer les indices PK sur ce reader
                pkColumnIndices = new List<int>();
            }

            try
            {
            using (reader)
            {

                // Si readByPosition, trouver les indices des colonnes PK par leur nom (comparaison C#)
                if (readByPosition)
                {
                    var pkNames = primaryKeyColumns.Select(pk => pk.Trim('[', ']')).ToList();
                    pkColumnIndices = new List<int>(new int[pkNames.Count]);
                    for (int idx = 0; idx < pkNames.Count; idx++)
                        pkColumnIndices[idx] = -1;

                    for (int col = 0; col < reader.FieldCount; col++)
                    {
                        var colName = reader.GetName(col);
                        for (int pkIdx = 0; pkIdx < pkNames.Count; pkIdx++)
                        {
                            if (string.Equals(colName, pkNames[pkIdx], StringComparison.OrdinalIgnoreCase))
                            {
                                pkColumnIndices[pkIdx] = col;
                                break;
                            }
                        }
                    }

                    // Si aucune colonne PK trouvee, log et retourner vide
                    if (pkColumnIndices.Any(idx => idx < 0))
                    {
                        _logger.Warn(LogCategory.DETECTION,
                            $"Colonnes PK introuvables dans les donnees source: {string.Join(", ", primaryKeyColumns)}");
                        return new List<object>();
                    }
                }

                var seen = new HashSet<string>();
                while (await reader.ReadAsync(cancellationToken))
                {
                    if (primaryKeyColumns.Count == 1)
                    {
                        // Cle simple: valeur directe
                        var colIdx = readByPosition ? pkColumnIndices[0] : 0;
                        var value = reader[colIdx];
                        if (value != DBNull.Value)
                        {
                            var converted = ConvertToSerializable(value);
                            // Deduplication en memoire si readByPosition (pas DISTINCT en SQL)
                            var key = converted?.ToString() ?? "";
                            if (!readByPosition || seen.Add(key))
                                results.Add(converted);
                        }
                    }
                    else
                    {
                        // Cle composite: tuple de valeurs
                        var tuple = new List<object>();
                        for (int i = 0; i < primaryKeyColumns.Count; i++)
                        {
                            var colIdx = readByPosition ? pkColumnIndices[i] : i;
                            var value = reader[colIdx];
                            tuple.Add(value == DBNull.Value ? "" : ConvertToSerializable(value));
                        }
                        // Deduplication en memoire si readByPosition
                        var tupleKey = string.Join("|", tuple);
                        if (!readByPosition || seen.Add(tupleKey))
                            results.Add(tuple);
                    }
                }
            } // end using reader
            } // end try
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (Exception ex)
            {
                // La colonne PK n'existe pas dans la requete source (alias different ou CTE mal formee)
                // Retourner liste vide: la detection sera ignoree pour cette table
                _logger.Warn(LogCategory.DETECTION,
                    $"GetPrimaryKeyValues impossible (colonne PK absente ou syntaxe incompatible): {ex.Message}");
                return new List<object>();
            }

            return results;

            } // end try (connexion)
            finally
            {
                if (ownsConnection)
                    conn.Dispose();
            }
        }

        /// <summary>
        /// Mots-cles SQL Server qui ne peuvent pas etre des expressions de colonne valides.
        /// Si FindPkSourceExpression capture un de ces mots, on retourne null pour forcer le fallback readByPosition.
        /// Cas typique: "ISNULL(CASE ... END, '') AS [alias]" -> Pattern 1 capture "END",
        ///              "... END AS [alias] ..."              -> Pattern 2 capture "AS".
        /// </summary>
        private static readonly HashSet<string> _sqlKeywords = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "AS", "ON", "FROM", "WHERE", "AND", "OR", "IN", "NOT", "IS", "NULL",
            "END", "THEN", "ELSE", "WHEN", "CASE", "BEGIN", "BY", "SELECT",
            "JOIN", "INNER", "LEFT", "RIGHT", "OUTER", "FULL", "CROSS",
            "GROUP", "ORDER", "HAVING", "UNION", "ALL", "SET", "INTO",
            "VALUES", "WITH", "OVER", "PARTITION", "DISTINCT", "TOP",
            "ISNULL", "COALESCE", "CAST", "CONVERT", "COUNT", "SUM", "MAX", "MIN", "AVG"
        };

        /// <summary>
        /// Cherche l'expression source reelle d'un alias de colonne dans une requete SQL.
        /// Exemples:
        ///   "DL_No [N° interne]"              -> "DL_No"
        ///   "F_DOCENTETE.cbMarq [N° interne]"  -> "F_DOCENTETE.cbMarq"
        ///   "EC_No AS [N° interne]"            -> "EC_No"
        ///   "F_ECRITUREC.EC_No AS [N° interne]"-> "F_ECRITUREC.EC_No"
        ///   "ISNULL(CASE...) AS [Type Document]"-> null (fallback readByPosition)
        /// Retourne null si non trouve ou si l'expression capturee est un mot-cle SQL.
        /// </summary>
        private string? FindPkSourceExpression(string query, string columnAlias)
        {
            var escapedAlias = System.Text.RegularExpressions.Regex.Escape(columnAlias);

            // Pattern avec AS: "expression AS [alias]" ou "expression AS alias"
            var m = System.Text.RegularExpressions.Regex.Match(
                query,
                $@"([\w\.\[\]]+)\s+AS\s+\[?{escapedAlias}\]?",
                System.Text.RegularExpressions.RegexOptions.IgnoreCase);
            if (m.Success)
            {
                var expr = m.Groups[1].Value.Trim('[', ']');
                // Rejeter les mots-cles SQL (ex: END, THEN, ELSE captures depuis CASE...END AS [alias])
                if (_sqlKeywords.Contains(expr))
                {
                    _logger.Debug(LogCategory.DETECTION, $"[PK Expr] '{columnAlias}' -> expression invalide '{expr}' (mot-cle SQL), fallback");
                    return null;
                }
                _logger.Debug(LogCategory.DETECTION, $"[PK Expr] '{columnAlias}' -> '{expr}' (via AS)");
                return expr.Contains('.') ? expr : $"[{expr}]";
            }

            // Pattern sans AS: "expression [alias]" (syntaxe T-SQL raccourcie Sage 100)
            // ATTENTION: ce pattern peut capturer le mot-cle AS dans "...END AS [alias]"
            // -> le filtre _sqlKeywords ci-dessous est critique ici
            m = System.Text.RegularExpressions.Regex.Match(
                query,
                $@"([\w\.\[\]]+)\s+\[{escapedAlias}\]",
                System.Text.RegularExpressions.RegexOptions.IgnoreCase);
            if (m.Success)
            {
                var expr = m.Groups[1].Value.Trim('[', ']');
                // Rejeter les mots-cles SQL (ex: AS capture depuis "END AS [Type Document]")
                if (_sqlKeywords.Contains(expr))
                {
                    _logger.Debug(LogCategory.DETECTION, $"[PK Expr] '{columnAlias}' -> expression invalide '{expr}' (mot-cle SQL), fallback");
                    return null;
                }
                _logger.Debug(LogCategory.DETECTION, $"[PK Expr] '{columnAlias}' -> '{expr}' (sans AS)");
                return expr.Contains('.') ? expr : $"[{expr}]";
            }

            _logger.Debug(LogCategory.DETECTION, $"[PK Expr] '{columnAlias}' -> expression non trouvee, fallback lecture par nom");
            return null;
        }

        /// <summary>
        /// Trouve la position du premier FROM au niveau de profondeur 0 (hors sous-requetes).
        /// Retourne -1 si non trouve.
        /// </summary>
        private int FindFromPositionAtDepth0(string query)
        {
            var upper = query.ToUpperInvariant();
            int depth = 0;
            bool pastFirstSelect = false;
            for (int i = 0; i < upper.Length; i++)
            {
                if (upper[i] == '(') { depth++; continue; }
                if (upper[i] == ')') { depth--; continue; }
                if (depth != 0) continue;

                if (!pastFirstSelect && i + 6 <= upper.Length && upper.Substring(i, 6) == "SELECT")
                {
                    bool ws = (i == 0 || !char.IsLetterOrDigit(upper[i - 1]));
                    bool we = (i + 6 >= upper.Length || !char.IsLetterOrDigit(upper[i + 6]));
                    if (ws && we) { pastFirstSelect = true; i += 5; continue; }
                }

                if (pastFirstSelect && i + 4 <= upper.Length && upper.Substring(i, 4) == "FROM")
                {
                    bool ws = (i == 0 || !char.IsLetterOrDigit(upper[i - 1]));
                    bool we = (i + 4 >= upper.Length || !char.IsLetterOrDigit(upper[i + 4]));
                    if (ws && we) return i;
                }
            }
            return -1;
        }

        /// <summary>
        /// Supprime le ORDER BY en fin de requete (au niveau depth=0).
        /// </summary>
        private string RemoveTrailingOrderByStr(string query)
        {
            var upper = query.ToUpperInvariant();
            int lastOrderBy = -1;
            int depth = 0;
            for (int i = 0; i < upper.Length - 7; i++)
            {
                if (upper[i] == '(') depth++;
                else if (upper[i] == ')') depth--;
                else if (depth == 0 && i + 8 <= upper.Length && upper.Substring(i, 8) == "ORDER BY")
                {
                    bool ws = (i == 0 || !char.IsLetterOrDigit(upper[i - 1]));
                    bool we = (i + 8 >= upper.Length || !char.IsLetterOrDigit(upper[i + 8]));
                    if (ws && we) lastOrderBy = i;
                }
            }
            if (lastOrderBy > 0)
            {
                // Verifier que le ORDER BY est vraiment a la fin (pas suivi d'autre clause)
                var after = query.Substring(lastOrderBy + 8).Trim();
                // Si apres le ORDER BY il y a juste des noms de colonnes et c'est la fin
                // (pas de FROM, WHERE, GROUP BY, etc.) => on peut supprimer
                var upperAfter = after.ToUpperInvariant();
                if (!upperAfter.Contains("FROM") && !upperAfter.Contains("WHERE") &&
                    !upperAfter.Contains("GROUP BY") && !upperAfter.Contains("HAVING"))
                {
                    return query.Substring(0, lastOrderBy).TrimEnd();
                }
            }
            return query;
        }

        /// <summary>
        /// Convertit une valeur en type serialisable
        /// </summary>
        private object ConvertToSerializable(object value)
        {
            return value switch
            {
                DateTime dt => dt.ToString("yyyy-MM-ddTHH:mm:ss"),
                byte[] bytes => Convert.ToBase64String(bytes),
                Guid guid => guid.ToString(),
                _ => value
            };
        }

        /// <summary>
        /// Compte les lignes d'une table
        /// </summary>
        public async Task<int> CountRowsAsync(string tableName, CancellationToken cancellationToken = default)
        {
            using var conn = new SqlConnection(_connectionString);
            await conn.OpenAsync(cancellationToken);

            using var cmd = new SqlCommand($"SELECT COUNT(*) FROM [{tableName}]", conn);
            var result = await cmd.ExecuteScalarAsync(cancellationToken);
            return Convert.ToInt32(result);
        }

        /// <summary>
        /// Compte les lignes avec un filtre
        /// </summary>
        public async Task<int> CountRowsWithFilterAsync(
            string tableName,
            string? customQuery,
            string? whereClause,
            CancellationToken cancellationToken = default)
        {
            using var conn = new SqlConnection(_connectionString);
            await conn.OpenAsync(cancellationToken);

            string query;

            if (!string.IsNullOrEmpty(customQuery))
            {
                query = $"SELECT COUNT(*) FROM ({customQuery}) AS _count_src";
                if (!string.IsNullOrEmpty(whereClause))
                {
                    query = $"SELECT COUNT(*) FROM ({customQuery}) AS _count_src WHERE {whereClause}";
                }
            }
            else
            {
                query = $"SELECT COUNT(*) FROM [{tableName}]";
                if (!string.IsNullOrEmpty(whereClause))
                {
                    query += $" WHERE {whereClause}";
                }
            }

            using var cmd = new SqlCommand(query, conn);
            cmd.CommandTimeout = 120;

            var result = await cmd.ExecuteScalarAsync(cancellationToken);
            return Convert.ToInt32(result);
        }

        /// <summary>
        /// Liste les tables disponibles
        /// </summary>
        public async Task<List<string>> GetTablesAsync(CancellationToken cancellationToken = default)
        {
            var tables = new List<string>();

            using var conn = new SqlConnection(_connectionString);
            await conn.OpenAsync(cancellationToken);

            var query = @"
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                  AND TABLE_NAME LIKE 'F_%'
                ORDER BY TABLE_NAME";

            using var cmd = new SqlCommand(query, conn);
            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);

            while (await reader.ReadAsync(cancellationToken))
            {
                tables.Add(reader.GetString(0));
            }

            return tables;
        }

        /// <summary>
        /// Obtient le schema d'une table
        /// </summary>
        public async Task<List<ColumnInfo>> GetTableSchemaAsync(
            string tableName,
            CancellationToken cancellationToken = default)
        {
            var columns = new List<ColumnInfo>();

            using var conn = new SqlConnection(_connectionString);
            await conn.OpenAsync(cancellationToken);

            var query = @"
                SELECT
                    COLUMN_NAME,
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH,
                    IS_NULLABLE,
                    COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = @tableName
                ORDER BY ORDINAL_POSITION";

            using var cmd = new SqlCommand(query, conn);
            cmd.Parameters.AddWithValue("@tableName", tableName);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);

            while (await reader.ReadAsync(cancellationToken))
            {
                columns.Add(new ColumnInfo
                {
                    Name = reader.GetString(0),
                    DataType = reader.GetString(1),
                    MaxLength = reader.IsDBNull(2) ? null : reader.GetInt32(2),
                    IsNullable = reader.GetString(3) == "YES",
                    DefaultValue = reader.IsDBNull(4) ? null : reader.GetString(4)
                });
            }

            return columns;
        }

        /// <summary>
        /// Obtient les noms de colonnes d'une requete sans charger les donnees (SELECT TOP 0)
        /// Utilise pour creer la table DWH meme quand la requete retourne 0 lignes
        /// </summary>
        public async Task<List<string>> GetQueryColumnsAsync(
            string query,
            CancellationToken cancellationToken = default)
        {
            var columns = new List<string>();
            try
            {
                var conn = await GetConnectionAsync(cancellationToken);
                // Nettoyer le point-virgule terminal et BOM avant d'envelopper
                var cleanQuery = query.Trim('﻿', '​', ' ', '\t', '\r', '\n')
                                      .TrimEnd(';').TrimEnd();
                // Envelopper dans SELECT TOP 0 pour obtenir les colonnes sans charger les donnees
                var top0Query = $"SELECT TOP 0 * FROM ({cleanQuery}) AS _schema_probe";
                using var cmd = new SqlCommand(top0Query, conn);
                cmd.CommandTimeout = 30;
                using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
                for (int i = 0; i < reader.FieldCount; i++)
                    columns.Add(reader.GetName(i));
            }
            catch (Exception ex)
            {
                _logger.Warn(LogCategory.EXTRACTION, $"GetQueryColumnsAsync echoue: {ex.Message}", _agentName);
            }
            return columns;
        }

        /// <summary>
        /// Obtient les cles primaires d'une table
        /// </summary>
        public async Task<List<string>> GetPrimaryKeysAsync(
            string tableName,
            CancellationToken cancellationToken = default)
        {
            var pks = new List<string>();

            using var conn = new SqlConnection(_connectionString);
            await conn.OpenAsync(cancellationToken);

            var query = @"
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + QUOTENAME(CONSTRAINT_NAME)), 'IsPrimaryKey') = 1
                  AND TABLE_NAME = @tableName
                ORDER BY ORDINAL_POSITION";

            using var cmd = new SqlCommand(query, conn);
            cmd.Parameters.AddWithValue("@tableName", tableName);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);

            while (await reader.ReadAsync(cancellationToken))
            {
                pks.Add(reader.GetString(0));
            }

            return pks;
        }

        /// <summary>
        /// Diagnostic: detecte les lignes exclues par les JOINs de la requete d'extraction.
        /// Compare COUNT(*) sur la table source brute vs COUNT de la requete avec JOINs.
        /// </summary>
        public async Task<(int baseCount, int queryCount, int excluded)> DiagnoseJoinExclusionsAsync(
            string tableName,
            string? customQuery,
            string? whereClause,
            CancellationToken ct = default)
        {
            try
            {
                var conn = await GetConnectionAsync(ct);

                // 1. Count base table (with WHERE if applicable)
                string baseTableName = tableName;
                // Extract base table from FROM clause if possible
                if (!string.IsNullOrEmpty(customQuery))
                {
                    var match = System.Text.RegularExpressions.Regex.Match(
                        customQuery, @"FROM\s+(\[?\w+\]?)\s",
                        System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                    if (match.Success)
                        baseTableName = match.Groups[1].Value.Trim('[', ']');
                }

                string baseCountQuery;
                if (!string.IsNullOrEmpty(whereClause))
                    baseCountQuery = $"SELECT COUNT(*) FROM [{baseTableName}] WHERE {whereClause}";
                else
                {
                    // Try to extract WHERE from custom query
                    var whereMatch = System.Text.RegularExpressions.Regex.Match(
                        customQuery ?? "", @"\bWHERE\b(.+?)(?:ORDER\s+BY|$)",
                        System.Text.RegularExpressions.RegexOptions.IgnoreCase | System.Text.RegularExpressions.RegexOptions.Singleline);
                    if (whereMatch.Success)
                        baseCountQuery = $"SELECT COUNT(*) FROM [{baseTableName}] WHERE {whereMatch.Groups[1].Value.TrimEnd(';').Trim()}";
                    else
                        baseCountQuery = $"SELECT COUNT(*) FROM [{baseTableName}]";
                }

                int baseCount;
                using (var cmd1 = new SqlCommand(baseCountQuery, conn))
                {
                    cmd1.CommandTimeout = 120;
                    baseCount = (int)(await cmd1.ExecuteScalarAsync(ct) ?? 0);
                }

                // 2. Count via full query (with JOINs)
                int queryCount = baseCount;
                if (!string.IsNullOrEmpty(customQuery))
                {
                    var cleanQuery = customQuery.Trim('﻿', '​', ' ', '\t', '\r', '\n')
                                                .TrimEnd(';').TrimEnd();
                    var countSql = $"SELECT COUNT(*) FROM ({cleanQuery}) AS _diag";
                    try
                    {
                        using var cmd2 = new SqlCommand(countSql, conn);
                        cmd2.CommandTimeout = 300;
                        queryCount = (int)(await cmd2.ExecuteScalarAsync(ct) ?? 0);
                    }
                    catch
                    {
                        // Complex query (CTE etc) - skip diagnostic
                        return (baseCount, -1, -1);
                    }
                }

                int excluded = baseCount - queryCount;
                if (excluded > 0)
                {
                    _logger.Warn(LogCategory.EXTRACTION,
                        $"[DIAGNOSTIC] [{tableName}] JOINs excluent {excluded:N0} lignes ({baseCount:N0} base vs {queryCount:N0} avec JOINs)",
                        _agentName);
                }

                return (baseCount, queryCount, excluded);
            }
            catch (Exception ex)
            {
                _logger.Debug(LogCategory.EXTRACTION,
                    $"[DIAGNOSTIC] [{tableName}] Echec diagnostic: {ex.Message}", _agentName);
                return (-1, -1, -1);
            }
        }

        /// <summary>
        /// Extrait les valeurs des informations libres Sage en format EAV.
        /// Lit cbSysLibre pour decouvrir les champs, puis pour chaque table parente,
        /// construit dynamiquement un UNPIVOT via CROSS APPLY VALUES.
        /// </summary>
        public async Task<List<Dictionary<string, object?>>> ExtractInfoLibresValuesAsync(
            IProgress<int>? progress = null,
            CancellationToken cancellationToken = default)
        {
            var results = new List<Dictionary<string, object?>>();

            var conn = await GetConnectionAsync(cancellationToken);

            // 1. Lire les definitions d'info libres depuis cbSysLibre
            var definitions = new List<(string CbFile, string CbName)>();
            using (var cmd = new SqlCommand("SELECT [CB_File], [CB_Name] FROM [cbSysLibre] WHERE [CB_Name] IS NOT NULL AND [CB_Name] <> ''", conn))
            {
                cmd.CommandTimeout = 60;
                using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
                while (await reader.ReadAsync(cancellationToken))
                {
                    var cbFile = reader["CB_File"]?.ToString()?.Trim() ?? "";
                    var cbName = reader["CB_Name"]?.ToString()?.Trim() ?? "";
                    if (!string.IsNullOrEmpty(cbFile) && !string.IsNullOrEmpty(cbName))
                        definitions.Add((cbFile, cbName));
                }
            }

            if (!definitions.Any())
            {
                _logger.Info(LogCategory.EXTRACTION, "Aucune information libre trouvee dans cbSysLibre", _agentName);
                return results;
            }

            _logger.Info(LogCategory.EXTRACTION,
                $"Info libres: {definitions.Count} champs trouves dans {definitions.Select(d => d.CbFile).Distinct().Count()} tables",
                _agentName);

            // 2. Grouper par table parente
            var grouped = definitions.GroupBy(d => d.CbFile);

            int totalRows = 0;

            foreach (var group in grouped)
            {
                var tableName = group.Key;
                var fields = group.Select(g => g.CbName).Distinct().ToList();

                // Verifier quels champs existent reellement comme colonnes dans la table
                var existingColumns = new List<string>();
                try
                {
                    using var schemaCmd = new SqlCommand(
                        $"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = @table",
                        conn);
                    schemaCmd.Parameters.AddWithValue("@table", tableName);
                    schemaCmd.CommandTimeout = 30;
                    using var schemaReader = await schemaCmd.ExecuteReaderAsync(cancellationToken);
                    var allColumns = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                    while (await schemaReader.ReadAsync(cancellationToken))
                    {
                        allColumns.Add(schemaReader["COLUMN_NAME"]?.ToString() ?? "");
                    }

                    existingColumns = fields.Where(f => allColumns.Contains(f)).ToList();
                }
                catch (Exception ex)
                {
                    _logger.Warn(LogCategory.EXTRACTION,
                        $"Info libres: impossible de lire le schema de [{tableName}]: {ex.Message}",
                        _agentName);
                    continue;
                }

                if (!existingColumns.Any())
                {
                    _logger.Debug(LogCategory.EXTRACTION,
                        $"Info libres: aucune colonne correspondante dans [{tableName}] (champs: {string.Join(", ", fields)})",
                        _agentName);
                    continue;
                }

                // 3. Construire la requete CROSS APPLY VALUES pour UNPIVOT
                // SELECT 'F_COMPTET' as CB_File, CAST(cbMarq AS VARCHAR(50)) as entity_key,
                //        il.field_name as CB_Name, il.field_value as CB_Value
                // FROM [F_COMPTET]
                // CROSS APPLY (VALUES
                //     ('CA', CAST([CA] AS NVARCHAR(500))),
                //     ('CHAUFFEUR', CAST([CHAUFFEUR] AS NVARCHAR(500)))
                // ) AS il(field_name, field_value)
                // WHERE il.field_value IS NOT NULL AND il.field_value <> ''

                var valuesClause = string.Join(",\n    ",
                    existingColumns.Select(col =>
                        $"(N'{col.Replace("'", "''")}', CAST([{col}] AS NVARCHAR(500)))"));

                var query = $@"SELECT
    N'{tableName.Replace("'", "''")}' AS [CB_File],
    CAST(cbMarq AS VARCHAR(50)) AS [entity_key],
    il.field_name AS [CB_Name],
    il.field_value AS [CB_Value]
FROM [{tableName}]
CROSS APPLY (VALUES
    {valuesClause}
) AS il(field_name, field_value)
WHERE il.field_value IS NOT NULL AND LTRIM(RTRIM(CAST(il.field_value AS NVARCHAR(500)))) <> ''";

                try
                {
                    using var dataCmd = new SqlCommand(query, conn);
                    dataCmd.CommandTimeout = 300;
                    using var dataReader = await dataCmd.ExecuteReaderAsync(cancellationToken);

                    while (await dataReader.ReadAsync(cancellationToken))
                    {
                        var row = new Dictionary<string, object?>
                        {
                            ["CB_File"] = dataReader["CB_File"],
                            ["entity_key"] = dataReader["entity_key"],
                            ["CB_Name"] = dataReader["CB_Name"],
                            ["CB_Value"] = dataReader["CB_Value"]
                        };
                        results.Add(row);
                        totalRows++;

                        if (totalRows % 1000 == 0)
                            progress?.Report(totalRows);
                    }

                    _logger.Info(LogCategory.EXTRACTION,
                        $"Info libres [{tableName}]: {existingColumns.Count} champs, {results.Count - (totalRows - results.Count)} lignes extraites",
                        _agentName);
                }
                catch (Exception ex)
                {
                    _logger.Warn(LogCategory.EXTRACTION,
                        $"Info libres [{tableName}]: extraction echouee: {ex.Message}",
                        _agentName);
                }
            }

            progress?.Report(totalRows);
            _logger.Info(LogCategory.EXTRACTION,
                $"Info libres total: {totalRows} valeurs extraites de {grouped.Count()} tables",
                _agentName);

            return results;
        }

        /// <summary>
        /// Extrait les informations libres d'UNE table Sage au format LARGE (pivote) :
        /// une ligne par entite (cbMarq -> entity_key), une colonne par champ libre.
        /// Alternative a ExtractInfoLibresValuesAsync (EAV) : evite l'explosion du volume
        /// (1 ligne/entite au lieu de 1 ligne/champ). Les colonnes gardent leur type Sage.
        /// La table cible est auto-creee par DwhWriter d'apres les colonnes retournees.
        /// </summary>
        public async Task<List<Dictionary<string, object?>>> ExtractInfoLibresWideAsync(
            string cbFile,
            IProgress<int>? progress = null,
            CancellationToken cancellationToken = default)
        {
            var results = new List<Dictionary<string, object?>>();
            if (string.IsNullOrWhiteSpace(cbFile)) return results;
            cbFile = cbFile.Trim();

            var conn = await GetConnectionAsync(cancellationToken);

            // 1. Champs libres definis pour cette table (cbSysLibre)
            var fields = new List<string>();
            using (var cmd = new SqlCommand(
                "SELECT [CB_Name] FROM [cbSysLibre] WHERE [CB_File] = @f AND [CB_Name] IS NOT NULL AND [CB_Name] <> ''", conn))
            {
                cmd.Parameters.AddWithValue("@f", cbFile);
                cmd.CommandTimeout = 60;
                using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
                while (await reader.ReadAsync(cancellationToken))
                {
                    var n = reader["CB_Name"]?.ToString()?.Trim() ?? "";
                    if (!string.IsNullOrEmpty(n) && !fields.Contains(n)) fields.Add(n);
                }
            }
            if (!fields.Any())
            {
                _logger.Info(LogCategory.EXTRACTION, $"Info libres WIDE [{cbFile}]: aucun champ dans cbSysLibre", _agentName);
                return results;
            }

            // 2. Ne garder que les champs reellement presents comme colonnes
            var existingColumns = new List<string>();
            try
            {
                using var schemaCmd = new SqlCommand(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = @table", conn);
                schemaCmd.Parameters.AddWithValue("@table", cbFile);
                schemaCmd.CommandTimeout = 30;
                using var schemaReader = await schemaCmd.ExecuteReaderAsync(cancellationToken);
                var allColumns = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                while (await schemaReader.ReadAsync(cancellationToken))
                    allColumns.Add(schemaReader["COLUMN_NAME"]?.ToString() ?? "");
                existingColumns = fields.Where(f => allColumns.Contains(f)).ToList();
            }
            catch (Exception ex)
            {
                _logger.Warn(LogCategory.EXTRACTION, $"Info libres WIDE [{cbFile}]: schema illisible: {ex.Message}", _agentName);
                return results;
            }
            if (!existingColumns.Any())
            {
                _logger.Debug(LogCategory.EXTRACTION, $"Info libres WIDE [{cbFile}]: aucune colonne correspondante", _agentName);
                return results;
            }

            // 3. SELECT large : cbMarq + une colonne par champ (types Sage conserves, pas d'UNPIVOT)
            var selectCols = string.Join(",\n    ",
                existingColumns.Select(col => $"[{col.Replace("]", "]]")}]"));
            var query = $@"SELECT
    CAST(cbMarq AS VARCHAR(50)) AS [entity_key],
    {selectCols}
FROM [{cbFile.Replace("]", "]]")}]";

            try
            {
                using var dataCmd = new SqlCommand(query, conn);
                dataCmd.CommandTimeout = 600;
                using var dataReader = await dataCmd.ExecuteReaderAsync(cancellationToken);
                int totalRows = 0;
                while (await dataReader.ReadAsync(cancellationToken))
                {
                    var row = new Dictionary<string, object?>();
                    for (int i = 0; i < dataReader.FieldCount; i++)
                    {
                        var v = dataReader.GetValue(i);
                        row[dataReader.GetName(i)] = v == DBNull.Value ? null : v;
                    }
                    results.Add(row);
                    totalRows++;
                    if (totalRows % 5000 == 0) progress?.Report(totalRows);
                }
                progress?.Report(totalRows);
                _logger.Info(LogCategory.EXTRACTION,
                    $"Info libres WIDE [{cbFile}]: {existingColumns.Count} champs, {totalRows} lignes", _agentName);
            }
            catch (Exception ex)
            {
                _logger.Warn(LogCategory.EXTRACTION, $"Info libres WIDE [{cbFile}]: extraction echouee: {ex.Message}", _agentName);
            }

            return results;
        }

        public void Dispose()
        {
            _persistentConnection?.Dispose();
            _persistentConnection = null;
        }
    }

    /// <summary>
    /// Information sur une colonne
    /// </summary>
    public class ColumnInfo
    {
        public string Name { get; set; } = "";
        public string DataType { get; set; } = "";
        public int? MaxLength { get; set; }
        public bool IsNullable { get; set; }
        public string? DefaultValue { get; set; }
    }
}
