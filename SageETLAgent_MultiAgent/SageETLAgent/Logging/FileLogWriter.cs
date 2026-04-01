using System;
using System.IO;
using System.Text;

namespace SageETLAgent.Logging
{
    /// <summary>
    /// Ecrit les logs dans un fichier quotidien: logs/SageETL_yyyy-MM-dd.log
    /// Thread-safe avec rotation automatique par jour.
    /// </summary>
    public sealed class FileLogWriter : IDisposable
    {
        private readonly string _logDirectory;
        private readonly object _lock = new();
        private StreamWriter? _writer;
        private string _currentDate = "";
        private bool _disposed;

        public FileLogWriter(string? logDirectory = null)
        {
            _logDirectory = logDirectory
                ?? Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "logs");
        }

        public void Write(LogEntry entry)
        {
            if (_disposed) return;

            var today = DateTime.Now.ToString("yyyy-MM-dd");
            var line = entry.ToFileString();

            lock (_lock)
            {
                try
                {
                    // Rotation si changement de jour
                    if (today != _currentDate)
                    {
                        RotateWriter(today);
                    }

                    _writer?.WriteLine(line);
                    _writer?.Flush();
                }
                catch
                {
                    // Le logging fichier ne doit JAMAIS crasher l'application
                }
            }
        }

        private void RotateWriter(string newDate)
        {
            _writer?.Dispose();

            Directory.CreateDirectory(_logDirectory);

            var filePath = Path.Combine(_logDirectory, $"SageETL_{newDate}.log");
            _writer = new StreamWriter(filePath, append: true, Encoding.UTF8)
            {
                AutoFlush = false
            };
            _currentDate = newDate;
        }

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;

            lock (_lock)
            {
                _writer?.Flush();
                _writer?.Dispose();
                _writer = null;
            }
        }
    }
}
