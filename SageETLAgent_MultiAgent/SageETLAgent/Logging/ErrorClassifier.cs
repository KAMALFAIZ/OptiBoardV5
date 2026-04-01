using System;
using System.Data.SqlClient;
using System.Net.Http;

namespace SageETLAgent.Logging
{
    /// <summary>
    /// Classifie automatiquement les exceptions par type metier
    /// </summary>
    public static class ErrorClassifier
    {
        public static ErrorCategory Classify(Exception ex)
        {
            // Parcourir la chaine d'exceptions
            var current = ex;
            while (current != null)
            {
                var category = ClassifySingle(current);
                if (category != ErrorCategory.Unknown)
                    return category;
                current = current.InnerException;
            }

            // Fallback: heuristique sur le message complet
            return ClassifyByMessage(ex.ToString());
        }

        private static ErrorCategory ClassifySingle(Exception ex)
        {
            // Classification par type d'exception
            if (ex is SqlException sqlEx)
            {
                return sqlEx.Number switch
                {
                    2 or 53 or -2 or -1 or 258 => ErrorCategory.Connection,
                    102 or 156 or 207 or 208 or 4104 => ErrorCategory.SQL,
                    2601 or 2627 or 547 => ErrorCategory.SQL,
                    _ => ClassifyByMessage(sqlEx.Message)
                };
            }

            if (ex is HttpRequestException)
                return ErrorCategory.API;

            if (ex is System.IO.IOException)
                return ErrorCategory.IO;

            if (ex is TimeoutException)
                return ErrorCategory.Connection;

            if (ex is InvalidOperationException &&
                ex.Message.Contains("connection", StringComparison.OrdinalIgnoreCase))
                return ErrorCategory.Connection;

            return ErrorCategory.Unknown;
        }

        private static ErrorCategory ClassifyByMessage(string message)
        {
            var lower = message.ToLowerInvariant();

            // Patterns connexion (coherent avec ConnectionManager.IsConnectionError)
            string[] connectionPatterns =
            {
                "communication link failure", "connection failure",
                "tcp provider", "connection reset", "connection closed",
                "network error", "timeout expired", "connection timeout",
                "unable to connect", "server was not found",
                "network-related", "transport-level error",
                "named pipes provider", "login timeout",
                "broken", "08s01", "08001", "08004"
            };
            foreach (var p in connectionPatterns)
                if (lower.Contains(p)) return ErrorCategory.Connection;

            // Patterns SQL
            string[] sqlPatterns =
            {
                "incorrect syntax", "invalid column", "invalid object name",
                "cannot insert duplicate", "truncation", "conversion failed",
                "alter table", "column does not allow nulls",
                "string or binary data would be truncated"
            };
            foreach (var p in sqlPatterns)
                if (lower.Contains(p)) return ErrorCategory.SQL;

            // Patterns API
            string[] apiPatterns =
            {
                "status code", "404", "500", "unauthorized", "forbidden"
            };
            foreach (var p in apiPatterns)
                if (lower.Contains(p)) return ErrorCategory.API;

            // Patterns configuration
            string[] configPatterns =
            {
                "configuration", "connection string", "not configured"
            };
            foreach (var p in configPatterns)
                if (lower.Contains(p)) return ErrorCategory.Config;

            return ErrorCategory.Unknown;
        }
    }
}
