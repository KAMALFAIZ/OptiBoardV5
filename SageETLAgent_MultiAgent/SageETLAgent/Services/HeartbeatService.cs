using System;
using System.Diagnostics;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Service de heartbeat continu
    /// Envoie des heartbeats au serveur et recoit les commandes
    /// </summary>
    public class HeartbeatService : IDisposable
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;
        private readonly ApiClient _apiClient;
        private readonly SyncState _syncState;
        private readonly string _agentId;
        private readonly string _apiKey;

        private CancellationTokenSource? _cts;
        private Task? _heartbeatTask;

        /// <summary>
        /// Intervalle entre les heartbeats en millisecondes (defaut: 30 secondes)
        /// </summary>
        public int IntervalMs { get; set; } = 30000;

        /// <summary>
        /// Timeout pour l'envoi du heartbeat en secondes
        /// </summary>
        public int TimeoutSeconds { get; set; } = 5;

        /// <summary>
        /// Indique si le service est en cours d'execution
        /// </summary>
        public bool IsRunning => _heartbeatTask != null && !_heartbeatTask.IsCompleted;

        #region Events

        /// <summary>
        /// Commande recue du serveur
        /// </summary>
        public event EventHandler<AgentCommand>? CommandReceived;

        /// <summary>
        /// Heartbeat envoye avec succes
        /// </summary>
        public event EventHandler? HeartbeatSent;

        /// <summary>
        /// Erreur lors de l'envoi du heartbeat
        /// </summary>
        public event EventHandler<string>? HeartbeatError;

        /// <summary>
        /// Evenement de log
        /// </summary>
        public event EventHandler<string>? LogMessage;

        #endregion

        public HeartbeatService(
            ApiClient apiClient,
            SyncState syncState,
            string agentId,
            string apiKey)
        {
            _apiClient = apiClient;
            _syncState = syncState;
            _agentId = agentId;
            _apiKey = apiKey;
        }

        /// <summary>
        /// Demarre le service de heartbeat
        /// </summary>
        public void Start()
        {
            if (IsRunning)
            {
                Log("Heartbeat deja en cours");
                return;
            }

            Log($"Demarrage heartbeat (intervalle: {IntervalMs / 1000}s)");

            _cts = new CancellationTokenSource();
            _heartbeatTask = HeartbeatLoopAsync(_cts.Token);
        }

        /// <summary>
        /// Arrete le service de heartbeat
        /// </summary>
        public async Task StopAsync()
        {
            if (!IsRunning)
                return;

            Log("Arret du heartbeat...");

            _cts?.Cancel();

            try
            {
                if (_heartbeatTask != null)
                {
                    await _heartbeatTask.WaitAsync(TimeSpan.FromSeconds(5));
                }
            }
            catch (OperationCanceledException)
            {
                // Normal
            }
            catch (TimeoutException)
            {
                Log("Timeout arret heartbeat");
            }

            // Envoyer un dernier heartbeat "offline"
            try
            {
                await SendOfflineHeartbeatAsync();
            }
            catch
            {
                // Ignorer les erreurs
            }

            _cts?.Dispose();
            _cts = null;

            Log("Heartbeat arrete");
        }

        /// <summary>
        /// Envoie un heartbeat immediat (hors boucle)
        /// </summary>
        public async Task SendImmediateHeartbeatAsync()
        {
            await SendHeartbeatAsync();
        }

        #region Private Methods

        private async Task HeartbeatLoopAsync(CancellationToken ct)
        {
            // Attendre un peu avant le premier heartbeat
            await Task.Delay(1000, ct);

            while (!ct.IsCancellationRequested)
            {
                try
                {
                    await SendHeartbeatAsync();
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    _logger.Error(LogCategory.COMMUNICATION, $"Erreur heartbeat: {ex.Message}", ex);
                    HeartbeatError?.Invoke(this, ex.Message);
                }

                // Attendre l'intervalle
                try
                {
                    await Task.Delay(IntervalMs, ct);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }
        }

        private async Task SendHeartbeatAsync()
        {
            var payload = BuildHeartbeatPayload();

            var response = await _apiClient.SendHeartbeatWithResponseAsync(
                _agentId,
                _apiKey,
                payload);

            if (response.Success)
            {
                _syncState.LastHeartbeat = DateTime.Now;
                HeartbeatSent?.Invoke(this, EventArgs.Empty);

                // Traiter les commandes recues
                if (response.Commands != null && response.Commands.Count > 0)
                {
                    Log($"Recues {response.Commands.Count} commande(s)");

                    foreach (var command in response.Commands)
                    {
                        CommandReceived?.Invoke(this, command);
                    }
                }
            }
            else
            {
                Log($"Heartbeat echoue: {response.Error}");
                HeartbeatError?.Invoke(this, response.Error ?? "Erreur inconnue");
            }
        }

        private async Task SendOfflineHeartbeatAsync()
        {
            var payload = new HeartbeatPayload
            {
                Status = "offline",
                Hostname = Environment.MachineName,
                AgentVersion = "2.0.0"
            };

            await _apiClient.SendHeartbeatWithResponseAsync(_agentId, _apiKey, payload);
        }

        private HeartbeatPayload BuildHeartbeatPayload()
        {
            var payload = new HeartbeatPayload
            {
                Status = _syncState.Status,
                CurrentTask = _syncState.CurrentTask,
                Hostname = Environment.MachineName,
                AgentVersion = "2.0.0"
            };

            // Ajouter les metriques systeme
            try
            {
                payload.CpuUsage = GetCpuUsage();
                payload.MemoryUsage = GetMemoryUsage();
            }
            catch
            {
                _logger.Debug(LogCategory.COMMUNICATION, "Metriques systeme indisponibles");
            }

            // Ajouter l'adresse IP
            try
            {
                payload.IpAddress = GetLocalIpAddress();
            }
            catch
            {
                _logger.Debug(LogCategory.COMMUNICATION, "Adresse IP indisponible");
            }

            // Ajouter les infos OS
            try
            {
                payload.OsInfo = $"{Environment.OSVersion.Platform} {Environment.OSVersion.Version}";
            }
            catch
            {
                _logger.Debug(LogCategory.COMMUNICATION, "Infos OS indisponibles");
            }

            return payload;
        }

        private float GetCpuUsage()
        {
            // Utiliser PerformanceCounter pour Windows
            try
            {
                using var cpuCounter = new PerformanceCounter("Processor", "% Processor Time", "_Total");
                cpuCounter.NextValue(); // Premier appel retourne toujours 0
                Thread.Sleep(100);
                return cpuCounter.NextValue();
            }
            catch
            {
                return 0;
            }
        }

        private float GetMemoryUsage()
        {
            try
            {
                var gcMemory = GC.GetTotalMemory(false);
                var workingSet = Environment.WorkingSet;

                // Estimation basique
                using var ramCounter = new PerformanceCounter("Memory", "% Committed Bytes In Use");
                return ramCounter.NextValue();
            }
            catch
            {
                return 0;
            }
        }

        private string GetLocalIpAddress()
        {
            try
            {
                foreach (var ni in NetworkInterface.GetAllNetworkInterfaces())
                {
                    if (ni.OperationalStatus == OperationalStatus.Up &&
                        ni.NetworkInterfaceType != NetworkInterfaceType.Loopback)
                    {
                        foreach (var ip in ni.GetIPProperties().UnicastAddresses)
                        {
                            if (ip.Address.AddressFamily == AddressFamily.InterNetwork)
                            {
                                return ip.Address.ToString();
                            }
                        }
                    }
                }
            }
            catch
            {
                // Ignorer
            }

            return "127.0.0.1";
        }

        private void Log(string message)
        {
            _logger.Info(LogCategory.COMMUNICATION, message);
        }

        #endregion

        public void Dispose()
        {
            _cts?.Cancel();
            _cts?.Dispose();
        }
    }
}
