using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using SageETLAgent.Logging;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Gestionnaire de connexions avec backoff exponentiel et reconnexion automatique
    /// </summary>
    public class ConnectionManager
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;
        private int _consecutiveErrors = 0;
        private readonly object _lock = new();

        /// <summary>
        /// Temps de backoff maximum en secondes (5 minutes)
        /// </summary>
        public int MaxBackoffSeconds { get; set; } = 300;

        /// <summary>
        /// Nombre d'erreurs avant d'appliquer le backoff
        /// </summary>
        public int BackoffThreshold { get; set; } = 3;

        /// <summary>
        /// Nombre maximum de tentatives de reconnexion
        /// </summary>
        public int MaxRetries { get; set; } = 3;

        /// <summary>
        /// Evenement de log
        /// </summary>
        public event EventHandler<string>? LogMessage;

        /// <summary>
        /// Nombre d'erreurs consecutives actuelles
        /// </summary>
        public int ConsecutiveErrors
        {
            get { lock (_lock) { return _consecutiveErrors; } }
        }

        /// <summary>
        /// Teste si une connexion est active
        /// </summary>
        /// <param name="testFunc">Fonction de test qui retourne (succes, message)</param>
        /// <param name="connectionName">Nom de la connexion pour les logs</param>
        /// <returns>True si la connexion est active</returns>
        public async Task<bool> IsConnectionAliveAsync(
            Func<Task<(bool Success, string Message)>> testFunc,
            string connectionName)
        {
            try
            {
                var (success, message) = await testFunc();
                if (success)
                {
                    _logger.Info(LogCategory.CONNEXION, $"[{connectionName}] Connexion OK: {message}");
                    return true;
                }
                else
                {
                    _logger.Warn(LogCategory.CONNEXION, $"[{connectionName}] Connexion echouee: {message}");
                    return false;
                }
            }
            catch (Exception ex)
            {
                _logger.Error(LogCategory.CONNEXION, $"[{connectionName}] Erreur test connexion: {ex.Message}", ex);
                return false;
            }
        }

        /// <summary>
        /// Calcule le temps de backoff en fonction du nombre d'erreurs consecutives
        /// Formule: 30 * 2^(n-3) secondes, max 5 minutes
        /// </summary>
        /// <returns>Temps d'attente</returns>
        public TimeSpan GetBackoffTime()
        {
            lock (_lock)
            {
                if (_consecutiveErrors < BackoffThreshold)
                {
                    return TimeSpan.Zero;
                }

                // Formule: 30 * 2^(n-3) avec max 300 secondes
                int exponent = _consecutiveErrors - BackoffThreshold;
                int backoffSeconds = Math.Min(MaxBackoffSeconds, 30 * (int)Math.Pow(2, exponent));
                return TimeSpan.FromSeconds(backoffSeconds);
            }
        }

        /// <summary>
        /// Tente de retablir les connexions avec retry
        /// </summary>
        /// <param name="reconnectFunc">Fonction de reconnexion</param>
        /// <param name="ct">Token d'annulation</param>
        /// <returns>True si reconnexion reussie</returns>
        public async Task<bool> EnsureConnectionsAsync(
            Func<Task<bool>> reconnectFunc,
            CancellationToken ct = default)
        {
            for (int attempt = 1; attempt <= MaxRetries; attempt++)
            {
                ct.ThrowIfCancellationRequested();

                try
                {
                    _logger.Warn(LogCategory.CONNEXION, $"Tentative de reconnexion {attempt}/{MaxRetries}...");

                    bool success = await reconnectFunc();
                    if (success)
                    {
                        _logger.Info(LogCategory.CONNEXION, "Reconnexion reussie");
                        ResetErrors();
                        return true;
                    }
                }
                catch (OperationCanceledException)
                {
                    throw;
                }
                catch (Exception ex)
                {
                    _logger.Error(LogCategory.CONNEXION, $"Erreur reconnexion tentative {attempt}: {ex.Message}", ex);
                }

                if (attempt < MaxRetries)
                {
                    // Attente avant prochaine tentative: 1s, 2s, 4s...
                    int waitSeconds = (int)Math.Pow(2, attempt - 1);
                    _logger.Warn(LogCategory.CONNEXION, $"Attente {waitSeconds}s avant prochaine tentative...");
                    await Task.Delay(TimeSpan.FromSeconds(waitSeconds), ct);
                }
            }

            _logger.Error(LogCategory.CONNEXION, "Echec de reconnexion apres toutes les tentatives");
            return false;
        }

        /// <summary>
        /// Execute une operation avec retry et backoff
        /// </summary>
        /// <typeparam name="T">Type de retour</typeparam>
        /// <param name="operation">Operation a executer</param>
        /// <param name="operationName">Nom pour les logs</param>
        /// <param name="ct">Token d'annulation</param>
        /// <returns>Resultat de l'operation</returns>
        public async Task<T> ExecuteWithRetryAsync<T>(
            Func<Task<T>> operation,
            string operationName,
            CancellationToken ct = default)
        {
            Exception? lastException = null;

            for (int attempt = 1; attempt <= MaxRetries; attempt++)
            {
                ct.ThrowIfCancellationRequested();

                try
                {
                    T result = await operation();
                    ResetErrors();
                    return result;
                }
                catch (OperationCanceledException)
                {
                    throw;
                }
                catch (Exception ex)
                {
                    lastException = ex;
                    IncrementErrors();

                    if (IsConnectionError(ex))
                    {
                        _logger.Error(LogCategory.CONNEXION, $"[{operationName}] Erreur connexion (tentative {attempt}/{MaxRetries}): {ex.Message}", ex);

                        if (attempt < MaxRetries)
                        {
                            var backoff = GetBackoffTime();
                            if (backoff > TimeSpan.Zero)
                            {
                                _logger.Warn(LogCategory.CONNEXION, $"Backoff: attente {backoff.TotalSeconds:F0}s...");
                                await Task.Delay(backoff, ct);
                            }
                        }
                    }
                    else
                    {
                        // Erreur non-reseau, ne pas retry
                        _logger.Error(LogCategory.CONNEXION, $"[{operationName}] Erreur non-reseau: {ex.Message}", ex);
                        throw;
                    }
                }
            }

            throw lastException ?? new Exception($"Echec de l'operation {operationName}");
        }

        /// <summary>
        /// Reset le compteur d'erreurs consecutives
        /// </summary>
        public void ResetErrors()
        {
            lock (_lock)
            {
                if (_consecutiveErrors > 0)
                {
                    _logger.Debug(LogCategory.CONNEXION, $"Reset compteur erreurs (etait a {_consecutiveErrors})");
                    _consecutiveErrors = 0;
                }
            }
        }

        /// <summary>
        /// Incremente le compteur d'erreurs
        /// </summary>
        public void IncrementErrors()
        {
            lock (_lock)
            {
                _consecutiveErrors++;
                _logger.Error(LogCategory.CONNEXION, $"Erreur consecutive #{_consecutiveErrors}");
            }
        }

        /// <summary>
        /// Determine si une exception est liee a une erreur de connexion
        /// </summary>
        /// <param name="ex">Exception a analyser</param>
        /// <returns>True si c'est une erreur de connexion</returns>
        public bool IsConnectionError(Exception ex)
        {
            string errorStr = ex.Message.ToLowerInvariant();

            // Ajouter le message des inner exceptions
            var inner = ex.InnerException;
            while (inner != null)
            {
                errorStr += " " + inner.Message.ToLowerInvariant();
                inner = inner.InnerException;
            }

            // Patterns d'erreurs de connexion
            var connectionErrors = new[]
            {
                "communication link failure",
                "connection failure",
                "tcp provider",
                "08s01",  // SQLSTATE connection error
                "08001",  // Unable to connect
                "08004",  // Server rejected connection
                "connection reset",
                "connection closed",
                "network error",
                "timeout expired",
                "connection timeout",
                "unable to connect",
                "server was not found",
                "network-related",
                "instance-specific error",
                "named pipes provider",
                "login timeout",
                "connection was closed",
                "transport-level error",
                "remote host",
                "l'hôte distant",  // French: remote host
                "hôte de connexion"  // French: connection host
            };

            foreach (var pattern in connectionErrors)
            {
                if (errorStr.Contains(pattern))
                {
                    return true;
                }
            }

            return false;
        }

        /// <summary>
        /// Verifie si le backoff doit etre applique
        /// </summary>
        /// <returns>True si le seuil est atteint</returns>
        public bool ShouldApplyBackoff()
        {
            lock (_lock)
            {
                return _consecutiveErrors >= BackoffThreshold;
            }
        }

        /// <summary>
        /// Attend le temps de backoff si necessaire
        /// </summary>
        /// <param name="ct">Token d'annulation</param>
        public async Task WaitBackoffIfNeededAsync(CancellationToken ct = default)
        {
            var backoff = GetBackoffTime();
            if (backoff > TimeSpan.Zero)
            {
                _logger.Warn(LogCategory.CONNEXION, $"Backoff actif: attente {backoff.TotalSeconds:F0}s ({_consecutiveErrors} erreurs consecutives)...");
                await Task.Delay(backoff, ct);
            }
        }

        private void Log(string message)
        {
            _logger.Info(LogCategory.CONNEXION, message);
        }
    }
}
