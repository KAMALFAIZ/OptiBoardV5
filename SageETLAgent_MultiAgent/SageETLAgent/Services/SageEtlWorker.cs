using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Hosting;
using Newtonsoft.Json;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Services
{
    /// <summary>
    /// BackgroundService pour le mode Service Windows.
    /// Charge les agents depuis l'API, demarre un ContinuousSyncService par agent,
    /// tourne jusqu'a l'arret du service.
    /// </summary>
    public class SageEtlWorker : BackgroundService
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;
        private readonly Dictionary<string, ContinuousSyncService> _services = new();
        private ServiceConfig _config = new();

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            _logger.Info(LogCategory.GENERAL, "SageEtlWorker: demarrage...");

            try
            {
                // 1. Charger la configuration
                _config = LoadConfig();
                _logger.Info(LogCategory.GENERAL,
                    $"Configuration: ServerUrl={_config.ServerUrl}, AgentFilter={_config.AgentFilter ?? "ALL"}");

                // 2. Charger les agents depuis l'API
                var agents = await LoadAgentsFromApiAsync(_config, stoppingToken);
                if (!agents.Any())
                {
                    _logger.Error(LogCategory.GENERAL,
                        "Aucun agent trouve. Le service va s'arreter.");
                    return;
                }

                _logger.Info(LogCategory.GENERAL, $"{agents.Count} agent(s) a demarrer");

                // 3. Demarrer un ContinuousSyncService par agent
                foreach (var agent in agents)
                {
                    if (stoppingToken.IsCancellationRequested) break;

                    var service = new ContinuousSyncService(_config.ServerUrl, agent);
                    service.SyncCompleted += (s, result) =>
                    {
                        _logger.Info(LogCategory.ORCHESTRATION,
                            $"Cycle termine: {result.TablesSuccess}/{result.TablesTotal} tables, " +
                            $"{result.TotalRows:N0} lignes en {result.DurationSeconds:F1}s",
                            agent.Name);
                    };
                    service.ErrorOccurred += (s, error) =>
                    {
                        _logger.Error(LogCategory.ORCHESTRATION,
                            $"Erreur: {error}", agentName: agent.Name);
                    };

                    _services[agent.AgentId] = service;

                    try
                    {
                        await service.StartAsync();
                        _logger.Info(LogCategory.GENERAL,
                            $"Agent {agent.Name} ({agent.DwhCode}) demarre", agent.Name);
                    }
                    catch (Exception ex)
                    {
                        _logger.Error(LogCategory.GENERAL,
                            $"Echec demarrage {agent.Name}: {ex.Message}", ex, agent.Name);
                    }
                }

                _logger.Info(LogCategory.GENERAL,
                    $"Service actif avec {_services.Count} agent(s)");

                // 4. Attendre le signal d'arret
                try
                {
                    await Task.Delay(Timeout.Infinite, stoppingToken);
                }
                catch (OperationCanceledException)
                {
                    // Arret normal demande par le SCM
                }
            }
            catch (Exception ex)
            {
                _logger.Error(LogCategory.GENERAL,
                    $"Erreur fatale Worker: {ex.Message}", ex);
                throw;
            }
        }

        public override async Task StopAsync(CancellationToken cancellationToken)
        {
            _logger.Info(LogCategory.GENERAL, "SageEtlWorker: arret en cours...");

            // Arreter tous les services en parallele
            var stopTasks = _services.Values.Select(async service =>
            {
                try
                {
                    await service.StopAsync();
                    service.Dispose();
                }
                catch (Exception ex)
                {
                    _logger.Error(LogCategory.GENERAL,
                        $"Erreur arret service: {ex.Message}", ex);
                }
            });

            await Task.WhenAll(stopTasks);
            _services.Clear();

            _logger.Info(LogCategory.GENERAL, "SageEtlWorker: arrete");
            SyncLogger.Instance.Dispose();

            await base.StopAsync(cancellationToken);
        }

        /// <summary>
        /// Charge la configuration depuis appsettings.json
        /// </summary>
        private ServiceConfig LoadConfig()
        {
            var configPath = Path.Combine(
                AppDomain.CurrentDomain.BaseDirectory, "appsettings.json");

            if (File.Exists(configPath))
            {
                try
                {
                    var json = File.ReadAllText(configPath);
                    var config = JsonConvert.DeserializeObject<ServiceConfigRoot>(json);
                    if (config?.SageEtl != null)
                    {
                        _logger.Info(LogCategory.GENERAL,
                            $"Configuration chargee: {configPath}");
                        return config.SageEtl;
                    }
                }
                catch (Exception ex)
                {
                    _logger.Error(LogCategory.GENERAL,
                        $"Erreur lecture config: {ex.Message}", ex);
                }
            }
            else
            {
                _logger.Warn(LogCategory.GENERAL,
                    $"Fichier config absent: {configPath}, utilisation des valeurs par defaut");
            }

            return new ServiceConfig();
        }

        /// <summary>
        /// Charge la liste des agents depuis l'API serveur
        /// </summary>
        private async Task<List<AgentProfile>> LoadAgentsFromApiAsync(
            ServiceConfig config, CancellationToken ct)
        {
            try
            {
                using var apiClient = new ApiClient(config.ServerUrl, config.DwhCode);

                // Tester la connexion
                var (ok, msg) = await apiClient.TestConnectionAsync();
                if (!ok)
                {
                    _logger.Error(LogCategory.COMMUNICATION,
                        $"Connexion serveur echouee: {msg}");
                    return new List<AgentProfile>();
                }

                _logger.Info(LogCategory.COMMUNICATION, "Connexion serveur OK");

                var allAgents = await apiClient.GetAgentsAsync();
                _logger.Info(LogCategory.COMMUNICATION,
                    $"API retourne {allAgents.Count} agent(s)");

                // Filtrer: uniquement les agents actifs et actives
                var filteredAgents = allAgents
                    .Where(a => a.IsEnabled && a.IsActive)
                    .ToList();

                // Filtre supplementaire si AgentFilter est defini
                if (!string.IsNullOrWhiteSpace(config.AgentFilter))
                {
                    var filter = config.AgentFilter
                        .Split(',', StringSplitOptions.RemoveEmptyEntries |
                                    StringSplitOptions.TrimEntries);

                    filteredAgents = filteredAgents
                        .Where(a => filter.Contains(a.AgentId) ||
                                    filter.Contains(a.DwhCode) ||
                                    filter.Contains(a.Name))
                        .ToList();

                    _logger.Info(LogCategory.GENERAL,
                        $"Filtre applique: {filteredAgents.Count} agent(s) apres filtrage");
                }

                return filteredAgents;
            }
            catch (Exception ex)
            {
                _logger.Error(LogCategory.COMMUNICATION,
                    $"Erreur chargement agents: {ex.Message}", ex);
                return new List<AgentProfile>();
            }
        }
    }

    #region Config Models

    /// <summary>
    /// Racine du fichier appsettings.json
    /// </summary>
    internal class ServiceConfigRoot
    {
        [JsonProperty("SageEtl")]
        public ServiceConfig? SageEtl { get; set; }
    }

    /// <summary>
    /// Configuration specifique au service
    /// </summary>
    public class ServiceConfig
    {
        /// <summary>
        /// URL du serveur API
        /// </summary>
        [JsonProperty("ServerUrl")]
        public string ServerUrl { get; set; } = "http://kasoft.selfip.net:50231";

        /// <summary>
        /// Code DWH client (X-DWH-Code header).
        /// Requis pour lire les agents depuis la base client (avec credentials Sage).
        /// </summary>
        [JsonProperty("DwhCode")]
        public string? DwhCode { get; set; }

        /// <summary>
        /// Filtre agents (CSV: AgentId, DwhCode ou Name).
        /// Vide = demarrer TOUS les agents actifs.
        /// </summary>
        [JsonProperty("AgentFilter")]
        public string? AgentFilter { get; set; }
    }

    #endregion
}
