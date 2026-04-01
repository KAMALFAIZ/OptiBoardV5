using System;
using System.Drawing;
using System.Windows.Forms;

namespace SageETLAgent.Logging
{
    /// <summary>
    /// Logger centralise pour SageETLAgent.
    /// Singleton thread-safe.
    /// Sorties: RichTextBox (colore), fichier quotidien, EventHandler (retro-compat).
    /// </summary>
    public sealed class SyncLogger : IDisposable
    {
        private static SyncLogger? _instance;
        private static readonly object _instanceLock = new();

        private readonly FileLogWriter _fileWriter;
        private RichTextBox? _richTextBox;

        /// <summary>
        /// Niveau minimum pour l'affichage UI (RichTextBox).
        /// Les messages en-dessous sont masques dans l'UI mais ecrits dans le fichier.
        /// </summary>
        public LogLevel MinimumLevel { get; set; } = LogLevel.INFO;

        /// <summary>
        /// Niveau minimum pour l'ecriture fichier.
        /// Par defaut DEBUG = tout est ecrit dans le fichier pour diagnostic.
        /// </summary>
        public LogLevel FileMinimumLevel { get; set; } = LogLevel.DEBUG;

        /// <summary>
        /// Taille max du RichTextBox avant trim
        /// </summary>
        public int MaxRtbLength { get; set; } = 100_000;

        /// <summary>
        /// Evenement retro-compatible pour les abonnes qui veulent des strings bruts
        /// </summary>
        public event EventHandler<string>? LogMessage;

        /// <summary>
        /// Evenement structure pour les abonnes qui veulent le LogEntry complet
        /// </summary>
        public event EventHandler<LogEntry>? LogEntryEmitted;

        private SyncLogger()
        {
            _fileWriter = new FileLogWriter();
        }

        /// <summary>
        /// Instance singleton. Creee au premier acces.
        /// </summary>
        public static SyncLogger Instance
        {
            get
            {
                if (_instance == null)
                {
                    lock (_instanceLock)
                    {
                        _instance ??= new SyncLogger();
                    }
                }
                return _instance;
            }
        }

        /// <summary>
        /// Attache le RichTextBox pour la sortie UI coloree.
        /// Appeler depuis le thread UI lors de l'initialisation du formulaire.
        /// </summary>
        public void AttachRichTextBox(RichTextBox rtb)
        {
            _richTextBox = rtb;
        }

        // ---- Methodes de convenance ----

        public void Debug(LogCategory category, string message, string? agentName = null, string? tableName = null)
            => Log(LogLevel.DEBUG, category, message, agentName, tableName);

        public void Info(LogCategory category, string message, string? agentName = null, string? tableName = null)
            => Log(LogLevel.INFO, category, message, agentName, tableName);

        public void Warn(LogCategory category, string message, string? agentName = null, string? tableName = null)
            => Log(LogLevel.WARN, category, message, agentName, tableName);

        public void Error(LogCategory category, string message, Exception? ex = null, string? agentName = null, string? tableName = null)
        {
            var entry = new LogEntry
            {
                Timestamp = DateTime.Now,
                Level = LogLevel.ERROR,
                Category = category,
                AgentName = agentName ?? "",
                TableName = tableName,
                Message = message,
                ExceptionDetails = ex?.Message,
                ErrorType = ex != null ? ErrorClassifier.Classify(ex) : null
            };

            ProcessEntry(entry);
        }

        /// <summary>
        /// Methode de log principale.
        /// Ecrit TOUJOURS dans le fichier (si >= FileMinimumLevel).
        /// Affiche dans l'UI seulement si >= MinimumLevel.
        /// </summary>
        public void Log(LogLevel level, LogCategory category, string message,
                        string? agentName = null, string? tableName = null)
        {
            // Ignorer seulement si en-dessous des DEUX niveaux
            if (level < MinimumLevel && level < FileMinimumLevel) return;

            var entry = new LogEntry
            {
                Timestamp = DateTime.Now,
                Level = level,
                Category = category,
                AgentName = agentName ?? "",
                TableName = tableName,
                Message = message
            };

            ProcessEntry(entry);
        }

        private void ProcessEntry(LogEntry entry)
        {
            // 1. Fichier (toujours si >= FileMinimumLevel)
            if (entry.Level >= FileMinimumLevel)
            {
                _fileWriter.Write(entry);
            }

            // 2-4: UI seulement si >= MinimumLevel
            if (entry.Level >= MinimumLevel)
            {
                // 2. Evenement string retro-compatible
                var formatted = entry.ToFormattedString();
                LogMessage?.Invoke(this, formatted);

                // 3. Evenement structure
                LogEntryEmitted?.Invoke(this, entry);

                // 4. RichTextBox colore
                AppendToRichTextBox(entry);
            }
        }

        private void AppendToRichTextBox(LogEntry entry)
        {
            var rtb = _richTextBox;
            if (rtb == null || rtb.IsDisposed) return;

            var formatted = entry.ToFormattedString();
            var color = GetColorForEntry(entry);

            try
            {
                if (rtb.InvokeRequired)
                {
                    rtb.BeginInvoke(() => AppendColoredLine(rtb, formatted, color));
                }
                else
                {
                    AppendColoredLine(rtb, formatted, color);
                }
            }
            catch
            {
                // L'UI logging ne doit jamais crasher l'application
            }
        }

        private void AppendColoredLine(RichTextBox rtb, string text, Color color)
        {
            try
            {
                if (rtb.IsDisposed) return;

                // Trim si trop long
                if (rtb.TextLength > MaxRtbLength)
                {
                    rtb.Select(0, rtb.TextLength / 2);
                    rtb.SelectedText = "";
                }

                var startIndex = rtb.TextLength;
                rtb.AppendText(text + Environment.NewLine);
                rtb.Select(startIndex, text.Length + Environment.NewLine.Length);
                rtb.SelectionColor = color;
                rtb.SelectionLength = 0;
                rtb.ScrollToCaret();
            }
            catch
            {
                // L'UI logging ne doit jamais crasher l'application
            }
        }

        private static Color GetColorForEntry(LogEntry entry)
        {
            return entry.Level switch
            {
                LogLevel.ERROR => Color.FromArgb(255, 80, 80),      // Rouge
                LogLevel.WARN => Color.FromArgb(255, 220, 50),      // Jaune
                LogLevel.DEBUG => Color.FromArgb(128, 128, 128),    // Gris
                LogLevel.INFO => GetInfoColor(entry),
                _ => Color.White
            };
        }

        private static Color GetInfoColor(LogEntry entry)
        {
            var msg = entry.Message;

            // Vert pour les messages de succes/fin
            if (msg.Contains(" OK") || msg.Contains("termine") || msg.Contains("reussie") ||
                msg.Contains("demarre") || msg.Contains("Connecte") || msg.Contains("supprimees"))
            {
                return Color.FromArgb(80, 220, 100);    // Vert
            }

            // Bleu clair pour progression extraction/chargement
            if (entry.Category == LogCategory.EXTRACTION || entry.Category == LogCategory.CHARGEMENT)
            {
                return Color.FromArgb(100, 200, 255);   // Bleu clair
            }

            // Cyan pour detection
            if (entry.Category == LogCategory.DETECTION)
            {
                return Color.FromArgb(180, 140, 255);   // Violet clair
            }

            return Color.White;  // INFO par defaut
        }

        public void Dispose()
        {
            _fileWriter.Dispose();
        }
    }
}
