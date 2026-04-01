using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Newtonsoft.Json;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Processeur de commandes recues du serveur
    /// Traite les commandes: sync_now, sync_table, pause, resume, reload_config, force_full_sync, test_connection
    /// </summary>
    public class CommandProcessor
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;
        private readonly ApiClient _apiClient;
        private readonly SyncState _syncState;

        #region Events

        /// <summary>
        /// Demande de synchronisation immediate de toutes les tables
        /// </summary>
        public event EventHandler? SyncNowRequested;

        /// <summary>
        /// Demande de synchronisation d'une table specifique
        /// </summary>
        public event EventHandler<string>? SyncTableRequested;

        /// <summary>
        /// Demande de mise en pause
        /// </summary>
        public event EventHandler? PauseRequested;

        /// <summary>
        /// Demande de reprise
        /// </summary>
        public event EventHandler? ResumeRequested;

        /// <summary>
        /// Demande de rechargement de la configuration
        /// </summary>
        public event EventHandler? ReloadConfigRequested;

        /// <summary>
        /// Demande de resync complete (reset des timestamps)
        /// Parametre: nom de table ou null pour toutes
        /// </summary>
        public event EventHandler<string?>? ForceFullSyncRequested;

        /// <summary>
        /// Demande de test de connexion
        /// </summary>
        public event EventHandler? TestConnectionRequested;

        /// <summary>
        /// Evenement de log
        /// </summary>
        public event EventHandler<string>? LogMessage;

        #endregion

        public CommandProcessor(ApiClient apiClient, SyncState syncState)
        {
            _apiClient = apiClient;
            _syncState = syncState;
        }

        /// <summary>
        /// Traite une commande recue du serveur
        /// </summary>
        public async Task ProcessCommandAsync(AgentCommand command)
        {
            Log($"Commande recue: {command.CommandType} (ID: {command.Id})");

            try
            {
                // Accuser reception
                await AckCommandAsync(command.Id, "acknowledged");

                // Executer la commande
                switch (command.CommandType.ToLowerInvariant())
                {
                    case "sync_now":
                        await HandleSyncNowAsync(command);
                        break;

                    case "sync_table":
                        await HandleSyncTableAsync(command);
                        break;

                    case "pause":
                        await HandlePauseAsync(command);
                        break;

                    case "resume":
                        await HandleResumeAsync(command);
                        break;

                    case "reload_config":
                        await HandleReloadConfigAsync(command);
                        break;

                    case "force_full_sync":
                        await HandleForceFullSyncAsync(command);
                        break;

                    case "test_connection":
                        await HandleTestConnectionAsync(command);
                        break;

                    default:
                        _logger.Warn(LogCategory.COMMUNICATION, $"Commande inconnue: {command.CommandType}");
                        await CompleteCommandAsync(command.Id, false, $"Commande inconnue: {command.CommandType}");
                        break;
                }
            }
            catch (Exception ex)
            {
                _logger.Error(LogCategory.COMMUNICATION, $"Erreur traitement commande {command.CommandType}: {ex.Message}", ex);
                await CompleteCommandAsync(command.Id, false, ex.Message);
            }
        }

        /// <summary>
        /// Traite plusieurs commandes
        /// </summary>
        public async Task ProcessCommandsAsync(IEnumerable<AgentCommand> commands)
        {
            foreach (var command in commands)
            {
                await ProcessCommandAsync(command);
            }
        }

        #region Command Handlers

        private async Task HandleSyncNowAsync(AgentCommand command)
        {
            Log("Execution: sync_now");
            SyncNowRequested?.Invoke(this, EventArgs.Empty);
            await CompleteCommandAsync(command.Id, true);
        }

        private async Task HandleSyncTableAsync(AgentCommand command)
        {
            var tableName = GetCommandData<string>(command, "table_name");

            if (string.IsNullOrEmpty(tableName))
            {
                await CompleteCommandAsync(command.Id, false, "table_name manquant");
                return;
            }

            Log($"Execution: sync_table ({tableName})");
            SyncTableRequested?.Invoke(this, tableName);
            await CompleteCommandAsync(command.Id, true);
        }

        private async Task HandlePauseAsync(AgentCommand command)
        {
            Log("Execution: pause");
            _syncState.IsPaused = true;
            _syncState.Status = "paused";
            PauseRequested?.Invoke(this, EventArgs.Empty);
            await CompleteCommandAsync(command.Id, true);
        }

        private async Task HandleResumeAsync(AgentCommand command)
        {
            Log("Execution: resume");
            _syncState.IsPaused = false;
            _syncState.Status = "active";
            ResumeRequested?.Invoke(this, EventArgs.Empty);
            await CompleteCommandAsync(command.Id, true);
        }

        private async Task HandleReloadConfigAsync(AgentCommand command)
        {
            Log("Execution: reload_config");
            ReloadConfigRequested?.Invoke(this, EventArgs.Empty);
            await CompleteCommandAsync(command.Id, true);
        }

        private async Task HandleForceFullSyncAsync(AgentCommand command)
        {
            var tableName = GetCommandData<string>(command, "table_name");

            if (string.IsNullOrEmpty(tableName))
            {
                Log("Execution: force_full_sync (TOUTES les tables)");
            }
            else
            {
                Log($"Execution: force_full_sync ({tableName})");
            }

            ForceFullSyncRequested?.Invoke(this, tableName);
            await CompleteCommandAsync(command.Id, true);
        }

        private async Task HandleTestConnectionAsync(AgentCommand command)
        {
            Log("Execution: test_connection");
            TestConnectionRequested?.Invoke(this, EventArgs.Empty);
            await CompleteCommandAsync(command.Id, true, result: new { status = "connection_test_triggered" });
        }

        #endregion

        #region API Communication

        private async Task AckCommandAsync(int commandId, string status)
        {
            try
            {
                await _apiClient.AckCommandAsync(
                    _syncState.AgentId,
                    "", // API key sera fourni par le service appelant
                    commandId,
                    status);
            }
            catch (Exception ex)
            {
                _logger.Error(LogCategory.COMMUNICATION, $"Erreur ack commande {commandId}: {ex.Message}", ex);
            }
        }

        private async Task CompleteCommandAsync(int commandId, bool success, string? error = null, object? result = null)
        {
            try
            {
                await _apiClient.CompleteCommandAsync(
                    _syncState.AgentId,
                    "", // API key sera fourni par le service appelant
                    commandId,
                    success,
                    error,
                    result);
            }
            catch (Exception ex)
            {
                _logger.Error(LogCategory.COMMUNICATION, $"Erreur completion commande {commandId}: {ex.Message}", ex);
            }
        }

        #endregion

        #region Helpers

        /// <summary>
        /// Extrait une valeur du command_data
        /// </summary>
        private T? GetCommandData<T>(AgentCommand command, string key)
        {
            if (command.CommandData == null)
                return default;

            if (!command.CommandData.TryGetValue(key, out var value))
                return default;

            if (value == null)
                return default;

            // Si c'est deja le bon type
            if (value is T typedValue)
                return typedValue;

            // Essayer de convertir via JSON
            try
            {
                var json = JsonConvert.SerializeObject(value);
                return JsonConvert.DeserializeObject<T>(json);
            }
            catch
            {
                return default;
            }
        }

        private void Log(string message)
        {
            _logger.Info(LogCategory.COMMUNICATION, message);
        }

        #endregion
    }
}
