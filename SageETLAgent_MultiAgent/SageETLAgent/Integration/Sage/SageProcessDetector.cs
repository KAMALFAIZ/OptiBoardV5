using System;
using System.Diagnostics;
using System.Linq;
using System.Threading;
using SageETLAgent.Logging;

namespace SageETLAgent.Integration.Sage
{
    /// <summary>
    /// Détecte si Sage ERP est en cours d'exécution et surveille sa fermeture.
    /// Utilise Process.GetProcessesByName() ciblé (plus efficace que GetProcesses()).
    /// </summary>
    public sealed class SageProcessDetector : IDisposable
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;

        // Noms de processus Sage connus (sans extension .exe)
        private static readonly string[] SageProcessNames =
        {
            "Sage100",
            "Sage100c",
            "Sage50",
            "Sage50c",
            "SCM",          // Sage Gestion commerciale
            "SACPT",        // Sage Comptabilité
            "BPCS",
            "SageManager"
        };

        private Thread? _watchThread;
        private volatile bool _watching;
        private Action? _onExitCallback;

        /// <summary>
        /// Retourne true si au moins un processus Sage avec une fenêtre "Sage " est détecté.
        /// </summary>
        public bool IsRunning()
        {
            // 1. Chercher par noms connus (rapide)
            foreach (var name in SageProcessNames)
            {
                var procs = Process.GetProcessesByName(name);
                if (procs.Length > 0)
                {
                    foreach (var p in procs) p.Dispose();
                    return true;
                }
            }

            // 2. Fallback : parcourir tous les processus et filtrer par titre de fenêtre
            // Utilisé si le nom du processus Sage est inconnu (version custom)
            return Process.GetProcesses()
                          .Any(p =>
                          {
                              try
                              {
                                  return !string.IsNullOrEmpty(p.MainWindowTitle)
                                      && p.MainWindowTitle.StartsWith("Sage ", StringComparison.OrdinalIgnoreCase);
                              }
                              catch
                              {
                                  return false;
                              }
                              finally
                              {
                                  p.Dispose();
                              }
                          });
        }

        /// <summary>
        /// Lance une surveillance en arrière-plan : appelle <paramref name="onExit"/> dès que Sage se ferme.
        /// Si Sage n'est pas en cours, le callback est appelé immédiatement.
        /// </summary>
        /// <param name="onExit">Action à déclencher à la fermeture de Sage.</param>
        /// <param name="pollIntervalMs">Intervalle de vérification en millisecondes (défaut : 3000).</param>
        public void WatchForExit(Action onExit, int pollIntervalMs = 3000)
        {
            if (_watching)
            {
                _logger.Log(LogLevel.WARN, LogCategory.GENERAL,
                    "[SageProcessDetector] Surveillance déjà active — ignoré.");
                return;
            }

            _onExitCallback = onExit;

            if (!IsRunning())
            {
                _logger.Log(LogLevel.DEBUG, LogCategory.GENERAL,
                    "[SageProcessDetector] Sage non détecté — callback immédiat.");
                onExit();
                return;
            }

            _watching = true;
            _watchThread = new Thread(() =>
            {
                _logger.Log(LogLevel.INFO, LogCategory.GENERAL,
                    "[SageProcessDetector] Surveillance démarrée — en attente de fermeture Sage...");

                while (_watching)
                {
                    Thread.Sleep(pollIntervalMs);

                    if (!IsRunning())
                    {
                        _watching = false;
                        _logger.Log(LogLevel.INFO, LogCategory.GENERAL,
                            "[SageProcessDetector] Sage fermé — déclenchement synchronisation registre.");
                        _onExitCallback?.Invoke();
                        return;
                    }
                }
            })
            {
                IsBackground = true,
                Name = "SageWatcher"
            };

            _watchThread.Start();
        }

        /// <summary>
        /// Arrête la surveillance en arrière-plan.
        /// </summary>
        public void StopWatching()
        {
            _watching = false;
            _logger.Log(LogLevel.DEBUG, LogCategory.GENERAL,
                "[SageProcessDetector] Surveillance arrêtée.");
        }

        public void Dispose() => StopWatching();
    }
}
