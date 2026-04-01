using System;

namespace SageETLAgent.Logging
{
    /// <summary>
    /// Entree de log structuree avec toutes les metadonnees
    /// </summary>
    public class LogEntry
    {
        public DateTime Timestamp { get; set; }
        public LogLevel Level { get; set; }
        public LogCategory Category { get; set; }
        public string AgentName { get; set; } = "";
        public string Message { get; set; } = "";
        public string? TableName { get; set; }
        public string? ExceptionDetails { get; set; }
        public ErrorCategory? ErrorType { get; set; }

        /// <summary>
        /// Format pour affichage UI:
        /// [HH:mm:ss] [LEVEL] [CATEGORY] [Agent] [Table] Message
        /// </summary>
        public string ToFormattedString()
        {
            var ts = Timestamp.ToString("HH:mm:ss");
            var lvl = Level.ToString().PadRight(5);
            var cat = Category.ToString();
            var agent = string.IsNullOrEmpty(AgentName) ? "" : $"[{AgentName}] ";
            var table = string.IsNullOrEmpty(TableName) ? "" : $"[{TableName}] ";
            return $"[{ts}] [{lvl}] [{cat}] {agent}{table}{Message}";
        }

        /// <summary>
        /// Format complet pour fichier log (avec exception si presente)
        /// </summary>
        public string ToFileString()
        {
            var main = ToFormattedString();
            if (!string.IsNullOrEmpty(ExceptionDetails))
            {
                return $"{main}\n    Exception ({ErrorType}): {ExceptionDetails}";
            }
            return main;
        }
    }
}
