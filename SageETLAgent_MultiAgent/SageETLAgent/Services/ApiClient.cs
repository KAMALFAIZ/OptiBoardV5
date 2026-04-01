using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;
using SageETLAgent.Integration.Sage.Models;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Client API pour communiquer avec le serveur DWH
    /// </summary>
    public class ApiClient : IDisposable
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;
        private readonly string? _dwhCode;
        private readonly SyncLogger _logger = SyncLogger.Instance;

        public ApiClient(string baseUrl, string? dwhCode = null)
        {
            _baseUrl = baseUrl.TrimEnd('/');
            _dwhCode = dwhCode;
            _httpClient = new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(120)
            };
        }

        #region Connexion et Agents

        /// <summary>
        /// Teste la connexion au serveur
        /// </summary>
        public async Task<(bool Success, string Message)> TestConnectionAsync()
        {
            try
            {
                var response = await _httpClient.GetAsync($"{_baseUrl}/api/health");
                if (response.IsSuccessStatusCode)
                {
                    var content = await response.Content.ReadAsStringAsync();
                    _logger.Info(LogCategory.COMMUNICATION, "Connexion serveur OK");
                    return (true, "Connexion OK");
                }
                _logger.Warn(LogCategory.COMMUNICATION, $"Serveur HTTP {(int)response.StatusCode}");
                return (false, $"Erreur HTTP {(int)response.StatusCode}");
            }
            catch (Exception ex)
            {
                _logger.Error(LogCategory.COMMUNICATION, $"Test connexion serveur echoue: {ex.Message}", ex);
                return (false, $"Erreur: {ex.Message}");
            }
        }

        /// <summary>
        /// Charge la liste des agents depuis le serveur
        /// </summary>
        public async Task<List<AgentProfile>> GetAgentsAsync()
        {
            var request = new HttpRequestMessage(HttpMethod.Get, $"{_baseUrl}/api/admin/etl/agents");
            if (!string.IsNullOrWhiteSpace(_dwhCode))
                request.Headers.Add("X-DWH-Code", _dwhCode);

            var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();

            var content = await response.Content.ReadAsStringAsync();
            var result = JsonConvert.DeserializeObject<ApiResponse<List<AgentProfile>>>(content);

            return result?.Data ?? new List<AgentProfile>();
        }

        /// <summary>
        /// Charge les items de menu OptiBoard depuis /api/menus/flat
        /// Seuls les items actifs et non-dossier sont retournés.
        /// </summary>
        public async Task<List<OptiMenuItem>> GetMenuItemsAsync()
        {
            var request = new HttpRequestMessage(HttpMethod.Get, $"{_baseUrl}/api/menus/flat");
            if (!string.IsNullOrWhiteSpace(_dwhCode))
                request.Headers.Add("X-DWH-Code", _dwhCode);

            var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();

            var content = await response.Content.ReadAsStringAsync();
            var result  = JsonConvert.DeserializeObject<ApiResponse<List<OptiMenuItem>>>(content);
            var all     = result?.Data ?? new List<OptiMenuItem>();

            // Garder uniquement les feuilles actives (type ≠ folder)
            return all.FindAll(m => m.Actif && m.IsLeaf);
        }

        /// <summary>
        /// Met a jour les parametres de connexion d'un agent
        /// </summary>
        public async Task<(bool Success, string Message)> UpdateAgentAsync(string agentId, object updates, string? dwhCode = null)
        {
            try
            {
                var request = new HttpRequestMessage(HttpMethod.Put, $"{_baseUrl}/api/admin/etl/agents/{agentId}");
                if (!string.IsNullOrWhiteSpace(dwhCode))
                    request.Headers.Add("X-DWH-Code", dwhCode);
                request.Content = new StringContent(
                    JsonConvert.SerializeObject(updates),
                    System.Text.Encoding.UTF8,
                    "application/json");

                var response = await _httpClient.SendAsync(request);
                var content = await response.Content.ReadAsStringAsync();

                if (response.IsSuccessStatusCode)
                    return (true, "Agent mis a jour");

                return (false, $"Erreur {(int)response.StatusCode}: {content}");
            }
            catch (Exception ex)
            {
                return (false, ex.Message);
            }
        }

        /// <summary>
        /// Supprime un agent du serveur
        /// </summary>
        public async Task<(bool Success, string Message)> DeleteAgentAsync(string agentId)
        {
            try
            {
                var response = await _httpClient.DeleteAsync($"{_baseUrl}/api/admin/etl/agents/{agentId}");

                if (response.IsSuccessStatusCode)
                {
                    return (true, "Agent supprime avec succes");
                }

                var content = await response.Content.ReadAsStringAsync();
                return (false, $"Erreur {(int)response.StatusCode}: {content}");
            }
            catch (Exception ex)
            {
                return (false, ex.Message);
            }
        }

        /// <summary>
        /// Charge les tables a synchroniser pour un agent
        /// </summary>
        public async Task<List<TableConfig>> GetTablesAsync(string agentId, string apiKey)
        {
            var request = CreateAuthenticatedRequest(HttpMethod.Get, $"/api/agents/{agentId}/tables", agentId, apiKey);
            var response = await _httpClient.SendAsync(request);

            if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
            {
                return new List<TableConfig>();
            }

            response.EnsureSuccessStatusCode();

            var content = await response.Content.ReadAsStringAsync();
            var result = JsonConvert.DeserializeObject<TablesResponse>(content);

            return result?.Tables ?? new List<TableConfig>();
        }

        #endregion

        #region Heartbeat

        /// <summary>
        /// Envoie un heartbeat simple (ancien format)
        /// </summary>
        public async Task SendHeartbeatAsync(string agentId, string apiKey, string status, string? message = null)
        {
            var payload = new HeartbeatPayload
            {
                Status = status,
                CurrentTask = message,
                Hostname = Environment.MachineName,
                AgentVersion = "2.0.0"
            };

            await SendHeartbeatWithResponseAsync(agentId, apiKey, payload);
        }

        /// <summary>
        /// Envoie un heartbeat complet et retourne les commandes du serveur
        /// </summary>
        public async Task<HeartbeatResponse> SendHeartbeatWithResponseAsync(
            string agentId,
            string apiKey,
            HeartbeatPayload payload)
        {
            var request = CreateAuthenticatedRequest(
                HttpMethod.Post,
                $"/api/agents/{agentId}/heartbeat",
                agentId,
                apiKey);

            request.Content = new StringContent(
                JsonConvert.SerializeObject(payload),
                Encoding.UTF8,
                "application/json");

            try
            {
                var response = await _httpClient.SendAsync(request);
                response.EnsureSuccessStatusCode();

                var content = await response.Content.ReadAsStringAsync();
                var result = JsonConvert.DeserializeObject<HeartbeatResponse>(content);

                return result ?? new HeartbeatResponse { Success = true };
            }
            catch (Exception ex)
            {
                return new HeartbeatResponse
                {
                    Success = false,
                    Error = ex.Message
                };
            }
        }

        #endregion

        #region Commandes

        /// <summary>
        /// Accuse reception d'une commande
        /// </summary>
        public async Task AckCommandAsync(
            string agentId,
            string apiKey,
            int commandId,
            string status = "acknowledged")
        {
            var request = CreateAuthenticatedRequest(
                HttpMethod.Post,
                $"/api/agents/{agentId}/commands/{commandId}/ack",
                agentId,
                apiKey);

            var payload = new { status };
            request.Content = new StringContent(
                JsonConvert.SerializeObject(payload),
                Encoding.UTF8,
                "application/json");

            var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();
        }

        /// <summary>
        /// Marque une commande comme completee
        /// </summary>
        public async Task CompleteCommandAsync(
            string agentId,
            string apiKey,
            int commandId,
            bool success,
            string? error = null,
            object? result = null)
        {
            var request = CreateAuthenticatedRequest(
                HttpMethod.Post,
                $"/api/agents/{agentId}/commands/{commandId}/complete",
                agentId,
                apiKey);

            var payload = new CommandAckRequest
            {
                Status = success ? "completed" : "failed",
                Success = success,
                Error = error,
                Result = result
            };

            request.Content = new StringContent(
                JsonConvert.SerializeObject(payload),
                Encoding.UTF8,
                "application/json");

            var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();
        }

        /// <summary>
        /// Recupere les commandes en attente
        /// </summary>
        public async Task<List<AgentCommand>> GetPendingCommandsAsync(string agentId, string apiKey)
        {
            var request = CreateAuthenticatedRequest(
                HttpMethod.Get,
                $"/api/agents/{agentId}/commands",
                agentId,
                apiKey);

            try
            {
                var response = await _httpClient.SendAsync(request);
                if (!response.IsSuccessStatusCode)
                    return new List<AgentCommand>();

                var content = await response.Content.ReadAsStringAsync();
                var result = JsonConvert.DeserializeObject<ApiResponse<List<AgentCommand>>>(content);
                return result?.Data ?? new List<AgentCommand>();
            }
            catch
            {
                return new List<AgentCommand>();
            }
        }

        #endregion

        #region Synchronisation

        /// <summary>
        /// Envoie les donnees d'une table (ancien format)
        /// </summary>
        public async Task<int> SendTableDataAsync(
            string agentId,
            string apiKey,
            string tableName,
            List<Dictionary<string, object?>> data,
            bool truncateFirst = true)
        {
            var request = CreateAuthenticatedRequest(
                HttpMethod.Post,
                $"/api/etl/sync/{tableName}",
                agentId,
                apiKey);

            var payload = new
            {
                data,
                truncate_first = truncateFirst,
                batch_info = new
                {
                    total_rows = data.Count
                }
            };

            request.Content = new StringContent(
                JsonConvert.SerializeObject(payload),
                Encoding.UTF8,
                "application/json");

            var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();

            var content = await response.Content.ReadAsStringAsync();
            var result = JsonConvert.DeserializeObject<ApiResponse<SyncResponse>>(content);

            return result?.Data?.RowsInserted ?? data.Count;
        }

        /// <summary>
        /// Envoie les donnees avec support incremental complet
        /// </summary>
        public async Task<PushDataResponse> PushDataAsync(
            string agentId,
            string apiKey,
            PushDataRequest pushRequest)
        {
            var request = CreateAuthenticatedRequest(
                HttpMethod.Post,
                $"/api/agents/{agentId}/push-data",
                agentId,
                apiKey);

            request.Content = new StringContent(
                JsonConvert.SerializeObject(pushRequest),
                Encoding.UTF8,
                "application/json");

            try
            {
                var response = await _httpClient.SendAsync(request);
                response.EnsureSuccessStatusCode();

                var content = await response.Content.ReadAsStringAsync();
                var result = JsonConvert.DeserializeObject<PushDataResponse>(content);

                return result ?? new PushDataResponse { Success = true, RowsInserted = pushRequest.Data.Count };
            }
            catch (Exception ex)
            {
                return new PushDataResponse
                {
                    Success = false,
                    Error = ex.Message
                };
            }
        }

        #endregion

        #region Detection Suppressions

        /// <summary>
        /// Envoie les IDs source pour detection des suppressions
        /// </summary>
        public async Task<DeleteDetectionResponse> PushDeletionsAsync(
            string agentId,
            string apiKey,
            DeleteDetectionRequest deleteRequest)
        {
            var request = CreateAuthenticatedRequest(
                HttpMethod.Post,
                $"/api/agents/{agentId}/push-deletions",
                agentId,
                apiKey);

            request.Content = new StringContent(
                JsonConvert.SerializeObject(deleteRequest),
                Encoding.UTF8,
                "application/json");

            try
            {
                var response = await _httpClient.SendAsync(request);
                response.EnsureSuccessStatusCode();

                var content = await response.Content.ReadAsStringAsync();
                var result = JsonConvert.DeserializeObject<DeleteDetectionResponse>(content);

                return result ?? new DeleteDetectionResponse { Success = true };
            }
            catch (Exception ex)
            {
                return new DeleteDetectionResponse
                {
                    Success = false,
                    Error = ex.Message
                };
            }
        }

        #endregion

        #region Helpers

        /// <summary>
        /// Cree une requete HTTP authentifiee
        /// </summary>
        private HttpRequestMessage CreateAuthenticatedRequest(
            HttpMethod method,
            string endpoint,
            string agentId,
            string apiKey)
        {
            var url = endpoint.StartsWith("/") ? $"{_baseUrl}{endpoint}" : $"{_baseUrl}/{endpoint}";
            var request = new HttpRequestMessage(method, url);
            request.Headers.Add("X-Agent-ID", agentId);
            request.Headers.Add("X-API-Key", apiKey);
            if (!string.IsNullOrWhiteSpace(_dwhCode))
                request.Headers.Add("X-DWH-Code", _dwhCode);
            return request;
        }

        public void Dispose()
        {
            _httpClient?.Dispose();
        }

        #endregion
    }

    #region Response Classes

    internal class ApiResponse<T>
    {
        [JsonProperty("success")]
        public bool Success { get; set; }

        [JsonProperty("data")]
        public T? Data { get; set; }

        [JsonProperty("error")]
        public string? Error { get; set; }
    }

    internal class TablesResponse
    {
        [JsonProperty("success")]
        public bool Success { get; set; }

        [JsonProperty("tables")]
        public List<TableConfig>? Tables { get; set; }
    }

    internal class SyncResponse
    {
        [JsonProperty("rows_inserted")]
        public int RowsInserted { get; set; }

        [JsonProperty("rows_updated")]
        public int RowsUpdated { get; set; }
    }

    #endregion
}
