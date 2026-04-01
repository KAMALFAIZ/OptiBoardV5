using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Moteur de synchronisation incrementale
    /// Construit les requetes avec filtre temporel pour ne recuperer que les donnees modifiees
    /// </summary>
    public class IncrementalSyncEngine
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;

        /// <summary>
        /// Evenement de log
        /// </summary>
        public event EventHandler<string>? LogMessage;

        /// <summary>
        /// Construit une requete avec filtre incremental
        /// </summary>
        /// <param name="table">Configuration de la table</param>
        /// <param name="baseQuery">Requete de base (custom ou SELECT *)</param>
        /// <param name="lastSyncTimestamp">Derniere synchronisation</param>
        /// <returns>Requete avec clause WHERE temporelle</returns>
        public string BuildIncrementalQuery(
            TableConfig table,
            string baseQuery,
            DateTime? lastSyncTimestamp)
        {
            // Si pas de timestamp ou sync full, retourner la requete telle quelle
            if (table.SyncType != "incremental" ||
                string.IsNullOrEmpty(table.TimestampColumn) ||
                lastSyncTimestamp == null ||
                table.ForceFullReload)
            {
                Log($"[{table.TableName}] Mode full: pas de filtre temporel");
                return baseQuery;
            }

            var timestampColumn = NormalizeTimestampColumn(table.TimestampColumn, baseQuery, table.TableName);
            var timestampFilter = BuildTimestampFilter(timestampColumn, lastSyncTimestamp.Value);

            string query;

            var hasCustomQuery = !string.IsNullOrEmpty(table.CustomQuery);

            // ─────────────────────────────────────────────────────────────────
            // STRATEGIE RADICALE:
            //   CAS A — timestampColumn est un ALIAS dans le SELECT
            //            (ex: "cbModification AS [Date modification]")
            //            → la colonne EST exposee dans le result set
            //            → CTE: ajouter WHERE/AND dans le SELECT EXTERNE (outer)
            //            → non-CTE: wrapping SELECT * FROM (...) WHERE [alias]
            //   CAS B — timestampColumn est une vraie colonne source
            //            (ex: "cbModification")
            //            → CTE: injecter dans le PREMIER CTE interne
            //            → non-CTE: injection directe dans la requete
            // ─────────────────────────────────────────────────────────────────
            if (hasCustomQuery)
            {
                var isCte = IsCteQuery(baseQuery);
                bool isAlias = IsAliasInQuery(baseQuery, timestampColumn);

                Log($"[{table.TableName}] IsCteQuery={isCte}, IsAlias={isAlias}, col='{timestampColumn}'");

                if (isAlias && isCte)
                {
                    // CAS A-CTE: alias expose dans le SELECT externe du CTE
                    // → on ajoute le filtre dans le SELECT externe (le alias y est accessible)
                    Log($"[{table.TableName}] Alias+CTE → filtre dans SELECT externe");
                    query = AddFilterToCteOuterSelect(baseQuery, timestampFilter);
                }
                else if (isAlias)
                {
                    // CAS A-NonCTE: alias expose → wrapping simple
                    Log($"[{table.TableName}] Alias+NonCTE → wrapping SELECT * FROM (...)");
                    var cleanQ = RemoveTrailingOrderBy(baseQuery.TrimEnd().TrimEnd(';').TrimEnd());
                    query = $"SELECT * FROM (\n{cleanQ}\n) _filtered\nWHERE {timestampFilter}";
                }
                else if (isCte)
                {
                    // CAS B-CTE: vraie colonne → injecter dans le premier CTE interne
                    Log($"[{table.TableName}] RealCol+CTE → injection dans CTE interne");
                    query = AddFilterToCteQuery(baseQuery, timestampColumn, lastSyncTimestamp.Value);
                }
                else
                {
                    // CAS B-NonCTE: vraie colonne → injection directe
                    Log($"[{table.TableName}] RealCol+NonCTE → injection directe");
                    query = WrapQueryWithFilter(baseQuery, timestampColumn, timestampFilter);
                }
            }
            else
            {
                // Cas simple (SELECT * FROM [table]): ajouter WHERE directement
                query = AddFilterToQuery(baseQuery, timestampFilter);
            }

            _logger.Info(LogCategory.TRANSFORMATION, $"[{table.TableName}] Mode incremental: filtre apres {lastSyncTimestamp:yyyy-MM-dd HH:mm:ss}");
            return query;
        }

        /// <summary>
        /// Normalise le nom de la colonne timestamp pour corriger les erreurs de config.
        /// Cas traite: 'cbModification1' (chiffre parasite en fin) alors que la query
        /// contient 'cbModification' → retourne 'cbModification'.
        /// Logique: si la colonne config n'existe pas dans la query MAIS qu'une version
        /// sans chiffres finaux existe → utiliser la version propre.
        /// </summary>
        private string NormalizeTimestampColumn(string timestampColumn, string query, string tableName)
        {
            if (string.IsNullOrEmpty(timestampColumn) || string.IsNullOrEmpty(query))
                return timestampColumn;

            var clean = timestampColumn.Trim('[', ']').Trim();

            // Si la colonne existe telle quelle dans la query → OK, pas de normalisation
            if (Regex.IsMatch(query, $@"\b{Regex.Escape(clean)}\b", RegexOptions.IgnoreCase))
                return timestampColumn;

            // Supprimer les chiffres finaux et reessayer
            var baseClean = Regex.Replace(clean, @"\d+$", "");
            if (baseClean != clean && baseClean.Length > 0 &&
                Regex.IsMatch(query, $@"\b{Regex.Escape(baseClean)}\b", RegexOptions.IgnoreCase))
            {
                Log($"[{tableName}] NORMALISATION timestamp: '{clean}' non trouve dans la query, corrige en '{baseClean}'");
                return baseClean;
            }

            // Aucune normalisation possible → retourner tel quel
            Log($"[{tableName}] timestamp column '{clean}' non trouve dans la query (aucune normalisation possible)");
            return timestampColumn;
        }

        /// <summary>
        /// Construit le filtre temporel pour SQL Server
        /// </summary>
        private string BuildTimestampFilter(string timestampColumn, DateTime lastSync)
        {
            // Format ISO 8601 pour SQL Server avec CONVERT
            var lastSyncStr = lastSync.ToString("yyyy-MM-ddTHH:mm:ss");

            // Mettre le nom de colonne entre crochets si pas deja fait
            var col = FormatColumnName(timestampColumn);

            // Utiliser CONVERT pour compatibilite SQL Server
            return $"{col} > CONVERT(datetime, '{lastSyncStr}', 126)";
        }

        /// <summary>
        /// Formate le nom de colonne avec crochets
        /// </summary>
        private string FormatColumnName(string columnName)
        {
            if (string.IsNullOrEmpty(columnName))
                return columnName;

            // Nettoyer les crochets existants
            columnName = columnName.Trim('[', ']');

            return $"[{columnName}]";
        }

        /// <summary>
        /// Detecte si la requete contient une CTE (Common Table Expression)
        /// Supporte: WITH name AS (...), WITH [name] AS (...), WITH name AS(...)
        /// </summary>
        private bool IsCteQuery(string query)
        {
            if (string.IsNullOrWhiteSpace(query))
                return false;

            // Nettoyer agressivement: BOM, espaces, retours chariot, tabs
            var trimmed = query.Trim('\uFEFF', '\u200B', ' ', '\t', '\r', '\n');

            // Log pour debug
            var preview = trimmed.Length > 50 ? trimmed.Substring(0, 50) : trimmed;
            Log($"[CTE Check] Debut requete: '{preview}...'");

            // Test simple d'abord: commence par WITH (case insensitive)
            if (!trimmed.StartsWith("WITH", StringComparison.OrdinalIgnoreCase))
            {
                Log($"[CTE Check] Ne commence PAS par WITH -> pas un CTE");
                return false;
            }

            // Verifier que c'est bien WITH name AS ( et pas juste un mot commencant par WITH
            // Patterns supportes:
            //   WITH Cte_Lignes AS (
            //   WITH [Cte_Lignes] AS (
            //   with cte as(
            //   WITH Cte_Lignes AS\n(
            var isCte = Regex.IsMatch(trimmed, @"^WITH\s+[\w\[\]]+\s+AS\s*\(", RegexOptions.IgnoreCase | RegexOptions.Singleline);

            Log($"[CTE Check] Regex match = {isCte}");
            return isCte;
        }

        /// <summary>
        /// Resout le prefixe de table pour une colonne dans une requete avec JOINs.
        /// Gere aussi le cas ou timestampColumn est un ALIAS SELECT (ex: "Date modification")
        /// qui correspond a "cbModification AS [Date modification]" dans la requete.
        /// Dans ce cas, retourne la vraie expression source (ex: "F_FOURNISS.[cbModification]").
        /// </summary>
        private string ResolveColumnWithTableAlias(string query, string columnName)
        {
            var cleanCol = columnName.Trim('[', ']');

            // 1. Chercher si c'est un ALIAS — deux syntaxes T-SQL:
            //    Avec AS:  "cbModification AS [Date modification]"
            //    Sans AS:  "cbModification [Date modification]"   ← syntaxe Sage 100
            var escapedCol = Regex.Escape(cleanCol);
            var aliasPatternWithAs    = $@"([\w\.\[\]]+)\s+AS\s+\[?{escapedCol}\]?";
            var aliasPatternWithoutAs = $@"([\w\.\[\]]+)\s+\[{escapedCol}\]";
            var aliasMatch = Regex.Match(query, aliasPatternWithAs, RegexOptions.IgnoreCase);
            if (!aliasMatch.Success)
                aliasMatch = Regex.Match(query, aliasPatternWithoutAs, RegexOptions.IgnoreCase);
            if (aliasMatch.Success)
            {
                var realExpr = aliasMatch.Groups[1].Value.Trim('[', ']');
                var dotIdx = realExpr.LastIndexOf('.');
                if (dotIdx > 0)
                {
                    var tbl = realExpr.Substring(0, dotIdx).Trim('[', ']');
                    var col = realExpr.Substring(dotIdx + 1).Trim('[', ']');
                    Log($"[CTE Filter] '{cleanCol}' est un alias de '{tbl}.[{col}]'");
                    return $"{tbl}.[{col}]";
                }
                Log($"[CTE Filter] '{cleanCol}' est un alias de '[{realExpr}]'");
                return $"[{realExpr}]";
            }

            // 2. Chercher le pattern direct: alias.columnName (avec ou sans crochets)
            //    Exemples: dr.cbModification, dr.[cbModification], [dr].cbModification
            var pattern = $@"(\w+)\.\[?{Regex.Escape(cleanCol)}\]?";
            var match = Regex.Match(query, pattern, RegexOptions.IgnoreCase);
            if (match.Success)
            {
                var alias = match.Groups[1].Value;
                Log($"[CTE Filter] Colonne '{cleanCol}' trouvee avec prefixe '{alias}' -> {alias}.[{cleanCol}]");
                return $"{alias}.[{cleanCol}]";
            }

            Log($"[CTE Filter] Colonne '{cleanCol}' sans prefixe de table -> [{cleanCol}]");
            return $"[{cleanCol}]";
        }

        /// <summary>
        /// Detecte si timestampColumn est utilise comme ALIAS dans le SELECT de la requete.
        /// Gere les deux syntaxes T-SQL:
        ///   Avec AS:    "cbModification AS [Date modification]"
        ///   Sans AS:    "cbModification [Date modification]"   ← syntaxe Sage 100
        /// </summary>
        private bool IsAliasInQuery(string query, string timestampColumn)
        {
            var cleanCol = Regex.Escape(timestampColumn.Trim('[', ']'));
            // Avec AS keyword
            if (Regex.IsMatch(query, $@"\bAS\s+\[?{cleanCol}\]?", RegexOptions.IgnoreCase))
                return true;
            // Sans AS: colonne suivie directement de [alias] (syntaxe T-SQL raccourcie)
            if (Regex.IsMatch(query, $@"\w\s+\[{cleanCol}\]", RegexOptions.IgnoreCase))
                return true;
            return false;
        }

        /// <summary>
        /// Ajoute le filtre dans le SELECT EXTERNE d'une requete CTE.
        /// Utilise quand timestampColumn est un ALIAS expose dans le result set final.
        ///
        /// IMPORTANT — restriction SQL Server:
        ///   SQL Server evalue WHERE AVANT que les alias SELECT soient calcules.
        ///   Donc "SELECT col AS [Alias] ... WHERE [Alias] > ..." echoue avec
        ///   "Nom de colonne non valide 'Alias'".
        ///
        /// SOLUTION: envelopper le SELECT externe dans un CTE supplementaire "_outer_filter"
        ///   puis filtrer depuis ce CTE:
        ///   WITH existing_ctes...,
        ///        _outer_filter AS ( SELECT ... FROM ... )
        ///   SELECT * FROM _outer_filter
        ///   WHERE [Alias] > CONVERT(datetime, '...', 126)
        ///
        ///   Dans "_outer_filter", [Alias] devient une vraie colonne nommee,
        ///   donc le WHERE suivant peut l'utiliser sans erreur.
        /// </summary>
        private string AddFilterToCteOuterSelect(string query, string filter)
        {
            var cleanQuery = query.TrimEnd();
            while (cleanQuery.EndsWith(";"))
                cleanQuery = cleanQuery.TrimEnd(';').TrimEnd();

            var upperQuery = cleanQuery.ToUpperInvariant();

            // Trouver le dernier SELECT au niveau depth=0 (SELECT externe du CTE)
            int mainSelectPos = -1;
            int depth = 0;
            for (int i = 0; i < upperQuery.Length - 6; i++)
            {
                if (upperQuery[i] == '(') depth++;
                else if (upperQuery[i] == ')') depth--;
                else if (depth == 0 && i + 6 <= upperQuery.Length && upperQuery.Substring(i, 6) == "SELECT")
                {
                    bool isWordStart = (i == 0 || !char.IsLetterOrDigit(upperQuery[i - 1]));
                    bool isWordEnd = (i + 6 >= upperQuery.Length || !char.IsLetterOrDigit(upperQuery[i + 6]));
                    if (isWordStart && isWordEnd) mainSelectPos = i;
                }
            }

            if (mainSelectPos < 0)
            {
                Log($"[CTE Outer] SELECT externe non trouve, ajout a la fin");
                return cleanQuery + $"\nWHERE {filter}";
            }

            // Extraire les parties CTE et SELECT externe
            // ctePart = "WITH Cte1 AS (...), Cte2 AS (...)"  (sans virgule finale)
            var ctePart = cleanQuery.Substring(0, mainSelectPos).TrimEnd().TrimEnd(',').TrimEnd();
            // outerSelect = "SELECT ... FROM ..." (sans ORDER BY car on va wrapper)
            var outerSelect = RemoveTrailingOrderBy(cleanQuery.Substring(mainSelectPos).TrimEnd());

            // Construire: ctePart, _outer_filter AS (outerSelect) SELECT * FROM _outer_filter WHERE filter
            // Ainsi [Alias] est une vraie colonne dans _outer_filter, le WHERE peut l'utiliser
            var result = $"{ctePart}\n, _outer_filter AS (\n{outerSelect}\n)\nSELECT * FROM _outer_filter\nWHERE {filter}";

            Log($"[CTE Outer] Wrapping outer SELECT dans _outer_filter CTE, filtre: {filter}");
            return result;
        }

        /// <summary>
        /// Ajoute le filtre dans une requete CTE (WITH ... AS (...)).
        /// Strategie a deux niveaux:
        ///   1. Priorite SELECT EXTERNE: si la colonne timestamp est trouvee dans le SELECT
        ///      externe (ex: dr.cbModification dans FROM F_DOCREGL dr), on injecte le filtre
        ///      directement dans le WHERE du SELECT externe. C'est le cas le plus courant
        ///      quand cbModification appartient a la table principale (ex: Echeances_Ventes).
        ///   2. Fallback PREMIER CTE: si la colonne n'est pas dans le SELECT externe
        ///      (ex: cbModification dans F_DOCLIGNE l), on injecte dans le premier CTE interne.
        /// </summary>
        private string AddFilterToCteQuery(string query, string timestampColumn, DateTime lastSync)
        {
            var lastSyncStr = lastSync.ToString("yyyy-MM-ddTHH:mm:ss");

            var cleanQuery = query.TrimEnd();
            while (cleanQuery.EndsWith(";"))
                cleanQuery = cleanQuery.TrimEnd(';').TrimEnd();

            // ── Etape 1: chercher la colonne dans le SELECT EXTERNE ──────────────
            // Le SELECT externe est le dernier SELECT a profondeur 0 (apres tous les CTEs)
            var upperFull = cleanQuery.ToUpperInvariant();
            int mainSelectPos = -1;
            int depthScan = 0;
            for (int i = 0; i < upperFull.Length - 6; i++)
            {
                if (upperFull[i] == '(') depthScan++;
                else if (upperFull[i] == ')') depthScan--;
                else if (depthScan == 0 && i + 6 <= upperFull.Length &&
                         upperFull.Substring(i, 6) == "SELECT")
                {
                    bool wStart = (i == 0 || !char.IsLetterOrDigit(upperFull[i - 1]));
                    bool wEnd   = (i + 6 >= upperFull.Length || !char.IsLetterOrDigit(upperFull[i + 6]));
                    if (wStart && wEnd) mainSelectPos = i;
                }
            }

            if (mainSelectPos > 0)
            {
                var outerPart = cleanQuery.Substring(mainSelectPos);
                var resolvedOuter = ResolveColumnWithTableAlias(outerPart, timestampColumn);
                var defaultBracket = $"[{timestampColumn.Trim('[', ']')}]";

                // Si la colonne est trouvee avec un prefixe de table dans le SELECT externe
                // (ex: dr.[cbModification]) → injecter la directement
                if (!string.Equals(resolvedOuter, defaultBracket, StringComparison.OrdinalIgnoreCase))
                {
                    Log($"[CTE Filter] '{timestampColumn}' trouve dans SELECT externe ({resolvedOuter}) → injection outer WHERE");
                    var outerFilter = $"{resolvedOuter} > CONVERT(datetime, '{lastSyncStr}', 126)";
                    var filteredOuter = AddFilterToQuery(outerPart, outerFilter);
                    return cleanQuery.Substring(0, mainSelectPos) + filteredOuter;
                }
            }

            // ── Etape 2: fallback — injection dans le PREMIER CTE interne ────────
            Log($"[CTE Filter] '{timestampColumn}' non trouve dans SELECT externe → injection CTE interne");

            int firstOpen = cleanQuery.IndexOf('(');
            if (firstOpen < 0)
            {
                Log($"[CTE Filter] Parenthese introuvable, ajout WHERE a la fin");
                var col0 = ResolveColumnWithTableAlias(cleanQuery, timestampColumn);
                return cleanQuery + $" WHERE {col0} > CONVERT(datetime, '{lastSyncStr}', 126)";
            }

            // Trouver la parenthese fermante correspondante
            int depth = 0;
            int firstClose = -1;
            for (int i = firstOpen; i < cleanQuery.Length; i++)
            {
                if (cleanQuery[i] == '(') depth++;
                else if (cleanQuery[i] == ')') { depth--; if (depth == 0) { firstClose = i; break; } }
            }

            if (firstClose < 0)
            {
                Log($"[CTE Filter] Parentheses non equilibrees, ajout WHERE a la fin");
                var col0 = ResolveColumnWithTableAlias(cleanQuery, timestampColumn);
                return cleanQuery + $" WHERE {col0} > CONVERT(datetime, '{lastSyncStr}', 126)";
            }

            // Extraire la requete interne du premier CTE
            var innerQuery = cleanQuery.Substring(firstOpen + 1, firstClose - firstOpen - 1);

            // Resoudre le prefixe de table dans la requete interne (ex: F_DOCENTETE.[cbModification])
            var qualifiedColumn = ResolveColumnWithTableAlias(innerQuery, timestampColumn);
            var filter = $"{qualifiedColumn} > CONVERT(datetime, '{lastSyncStr}', 126)";

            Log($"[CTE Filter] Injection dans CTE interne: {filter}");

            // Injecter le filtre dans la requete interne
            var filteredInner = AddFilterToQuery(innerQuery, filter);

            // Reconstruire la requete complete
            return cleanQuery.Substring(0, firstOpen + 1) + filteredInner + cleanQuery.Substring(firstClose);
        }

        /// <summary>
        /// Trouve la fin d'une clause en respectant la profondeur des parentheses
        /// Cherche ORDER BY, GROUP BY, HAVING comme mots complets (pas prefixes par lettre/chiffre)
        /// </summary>
        private int FindClauseEndAtDepth(string query, int startIndex)
        {
            var upperQuery = query.ToUpperInvariant();
            var keywords = new[] { "ORDER BY", "GROUP BY", "HAVING" };

            int depth = 0;
            for (int i = startIndex + 1; i < upperQuery.Length; i++)
            {
                if (upperQuery[i] == '(') depth++;
                else if (upperQuery[i] == ')') depth--;
                else if (depth == 0)
                {
                    foreach (var kw in keywords)
                    {
                        if (i + kw.Length <= upperQuery.Length &&
                            upperQuery.Substring(i, kw.Length) == kw)
                        {
                            // Verifier que c'est un mot complet
                            bool isWordStart = (i == 0 || !char.IsLetterOrDigit(upperQuery[i - 1]));
                            bool isWordEnd = (i + kw.Length >= upperQuery.Length || !char.IsLetterOrDigit(upperQuery[i + kw.Length]));
                            if (isWordStart && isWordEnd)
                                return i;
                        }
                    }
                }
            }

            return query.Length;
        }

        /// <summary>
        /// Trouve le point d'insertion pour WHERE apres une position donnee
        /// en respectant la profondeur des parentheses
        /// Cherche ORDER BY, GROUP BY, HAVING comme mots complets
        /// </summary>
        private int FindInsertPointAfter(string query, int afterIndex)
        {
            var upperQuery = query.ToUpperInvariant();
            var keywords = new[] { "ORDER BY", "GROUP BY", "HAVING" };

            int depth = 0;
            for (int i = afterIndex; i < upperQuery.Length; i++)
            {
                if (upperQuery[i] == '(') depth++;
                else if (upperQuery[i] == ')') depth--;
                else if (depth == 0)
                {
                    foreach (var kw in keywords)
                    {
                        if (i + kw.Length <= upperQuery.Length &&
                            upperQuery.Substring(i, kw.Length) == kw)
                        {
                            // Verifier que c'est un mot complet
                            bool isWordStart = (i == 0 || !char.IsLetterOrDigit(upperQuery[i - 1]));
                            bool isWordEnd = (i + kw.Length >= upperQuery.Length || !char.IsLetterOrDigit(upperQuery[i + kw.Length]));
                            if (isWordStart && isWordEnd)
                                return i;
                        }
                    }
                }
            }

            return query.Length;
        }

        /// <summary>
        /// Injecte le filtre directement dans la requete personnalisee.
        /// Anciennement: wrapping SELECT * FROM (...) WHERE filter
        /// Probleme du wrapping: si timestampColumn n'est pas dans le SELECT de la sous-requete,
        /// SQL Server retourne "Nom de colonne non valide" sur la clause WHERE externe.
        /// Fix: injection directe avec resolution du prefixe de table (ex: F_DOCENTETE.[cbModification])
        /// </summary>
        private string WrapQueryWithFilter(string query, string timestampColumn, string filter)
        {
            var innerQuery = query.TrimEnd();

            // Supprimer le point-virgule final
            while (innerQuery.EndsWith(";"))
                innerQuery = innerQuery.TrimEnd(';').TrimEnd();

            // Supprimer ORDER BY (inutile pour filtrage incremental)
            innerQuery = RemoveTrailingOrderBy(innerQuery);

            // Resoudre le prefixe de table pour eviter ambiguite dans les JOINs
            // Ex: cbModification -> F_DOCENTETE.[cbModification]
            var qualifiedColumn = ResolveColumnWithTableAlias(innerQuery, timestampColumn);
            var col = FormatColumnName(timestampColumn);
            var qualifiedFilter = qualifiedColumn != col
                ? filter.Replace(col, qualifiedColumn)
                : filter;

            Log($"[{timestampColumn}] Injection directe du filtre: {qualifiedFilter}");

            // Injecter directement dans la requete (evite "Nom de colonne non valide")
            return AddFilterToQuery(innerQuery, qualifiedFilter);
        }

        /// <summary>
        /// Supprime un ORDER BY en fin de requete (pour permettre le wrapping en sous-requete)
        /// </summary>
        private string RemoveTrailingOrderBy(string query)
        {
            // Trouver le dernier ORDER BY qui n'est pas dans une sous-requete
            var upperQuery = query.ToUpperInvariant();
            var lastOrderBy = upperQuery.LastIndexOf("ORDER BY");

            if (lastOrderBy < 0)
                return query;

            // Verifier que ce ORDER BY n'est pas dans une sous-requete
            // en comptant les parentheses ouvertes/fermees apres ce point
            int depth = 0;
            for (int i = lastOrderBy; i < query.Length; i++)
            {
                if (query[i] == '(') depth++;
                if (query[i] == ')') depth--;
            }

            // Si depth == 0, le ORDER BY est au niveau principal, on peut le supprimer
            if (depth == 0)
            {
                return query.Substring(0, lastOrderBy).TrimEnd();
            }

            return query;
        }

        /// <summary>
        /// Ajoute le filtre a une requete simple
        /// </summary>
        private string AddFilterToQuery(string query, string filter)
        {
            var upperQuery = query.ToUpperInvariant();

            if (upperQuery.Contains("WHERE"))
            {
                // Trouver l'endroit ou inserer AND
                var insertPoint = FindInsertPointForAnd(query);
                return query.Insert(insertPoint, $" AND {filter}");
            }
            else
            {
                // Trouver l'endroit ou inserer WHERE
                var insertPoint = FindInsertPointForWhere(query);
                return query.Insert(insertPoint, $" WHERE {filter}");
            }
        }

        /// <summary>
        /// Trouve l'endroit ou inserer WHERE
        /// </summary>
        private int FindInsertPointForWhere(string query)
        {
            var upperQuery = query.ToUpperInvariant();

            // Chercher GROUP BY, ORDER BY, ou fin de requete
            var keywords = new[] { "GROUP BY", "ORDER BY", "HAVING" };

            foreach (var keyword in keywords)
            {
                var index = upperQuery.LastIndexOf(keyword);
                if (index > 0)
                    return index;
            }

            return query.Length;
        }

        /// <summary>
        /// Trouve l'endroit ou inserer AND apres WHERE
        /// </summary>
        private int FindInsertPointForAnd(string query)
        {
            var upperQuery = query.ToUpperInvariant();

            // Chercher GROUP BY, ORDER BY, HAVING apres le WHERE
            var whereIndex = upperQuery.LastIndexOf("WHERE");
            if (whereIndex < 0)
                return query.Length;

            var keywords = new[] { "GROUP BY", "ORDER BY", "HAVING" };

            foreach (var keyword in keywords)
            {
                var index = upperQuery.IndexOf(keyword, whereIndex);
                if (index > whereIndex)
                    return index;
            }

            return query.Length;
        }

        /// <summary>
        /// Trouve la fin d'une clause WHERE
        /// </summary>
        private int FindClauseEnd(string query, int startIndex)
        {
            var upperQuery = query.ToUpperInvariant();
            var keywords = new[] { "GROUP BY", "ORDER BY", "HAVING", "UNION", "EXCEPT", "INTERSECT" };

            var minIndex = query.Length;

            foreach (var keyword in keywords)
            {
                var index = upperQuery.IndexOf(keyword, startIndex);
                if (index > startIndex && index < minIndex)
                    minIndex = index;
            }

            return minIndex;
        }

        /// <summary>
        /// Ajoute ORDER BY si absent
        /// </summary>
        private string AddOrderBy(string query, string? timestampColumn)
        {
            if (string.IsNullOrEmpty(timestampColumn))
                return query;

            var upperQuery = query.ToUpperInvariant();

            if (!upperQuery.Contains("ORDER BY"))
            {
                var col = FormatColumnName(timestampColumn);
                return $"{query} ORDER BY {col}";
            }

            return query;
        }

        /// <summary>
        /// Extrait les donnees de maniere incrementale
        /// </summary>
        public async Task<List<Dictionary<string, object?>>> ExtractIncrementalAsync(
            SageExtractor extractor,
            TableConfig table,
            DateTime? lastSyncTimestamp,
            IProgress<int>? progress = null,
            CancellationToken ct = default)
        {
            // Construire la requete de base
            var baseQuery = table.CustomQuery ?? $"SELECT * FROM [{table.TableName}]";

            // Appliquer le filtre incremental
            var incrementalQuery = BuildIncrementalQuery(table, baseQuery, lastSyncTimestamp);

            Log($"[{table.TableName}] Extraction avec requete: {TruncateQuery(incrementalQuery)}");

            // Extraire les donnees
            return await extractor.ExtractTableWithQueryAsync(
                incrementalQuery,
                table.BatchSize > 0 ? table.BatchSize : 5000,
                progress,
                ct);
        }

        /// <summary>
        /// Extrait le dernier timestamp des donnees
        /// </summary>
        public DateTime? ExtractLastTimestamp(
            List<Dictionary<string, object?>> data,
            string? timestampColumn)
        {
            if (string.IsNullOrEmpty(timestampColumn) || !data.Any())
                return null;

            DateTime? lastTimestamp = null;

            foreach (var row in data)
            {
                if (row.TryGetValue(timestampColumn, out var value) && value != null)
                {
                    DateTime? rowTimestamp = null;

                    if (value is DateTime dt)
                        rowTimestamp = dt;
                    else if (DateTime.TryParse(value.ToString(), out var parsed))
                        rowTimestamp = parsed;

                    if (rowTimestamp.HasValue)
                    {
                        if (lastTimestamp == null || rowTimestamp.Value > lastTimestamp.Value)
                            lastTimestamp = rowTimestamp.Value;
                    }
                }
            }

            return lastTimestamp;
        }

        /// <summary>
        /// Tronque une requete pour les logs
        /// </summary>
        private string TruncateQuery(string query, int maxLength = 200)
        {
            if (string.IsNullOrEmpty(query))
                return query;

            // Nettoyer les espaces multiples
            query = Regex.Replace(query, @"\s+", " ").Trim();

            if (query.Length <= maxLength)
                return query;

            return query.Substring(0, maxLength) + "...";
        }

        private void Log(string message)
        {
            _logger.Debug(LogCategory.TRANSFORMATION, message);
        }
    }
}
