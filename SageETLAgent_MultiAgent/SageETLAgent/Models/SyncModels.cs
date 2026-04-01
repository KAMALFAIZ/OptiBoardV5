using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace SageETLAgent.Models
{
    /// <summary>
    /// Commande recue du serveur via heartbeat
    /// </summary>
    public class AgentCommand
    {
        [JsonProperty("id")]
        public int Id { get; set; }

        [JsonProperty("command_type")]
        public string CommandType { get; set; } = "";

        [JsonProperty("command_data")]
        public Dictionary<string, object>? CommandData { get; set; }

        [JsonProperty("priority")]
        public int Priority { get; set; } = 5;

        [JsonProperty("created_at")]
        public DateTime? CreatedAt { get; set; }

        [JsonProperty("expires_at")]
        public DateTime? ExpiresAt { get; set; }
    }

    /// <summary>
    /// Payload envoye au serveur lors du heartbeat
    /// </summary>
    public class HeartbeatPayload
    {
        [JsonProperty("status")]
        public string Status { get; set; } = "active";

        [JsonProperty("current_task")]
        public string? CurrentTask { get; set; }

        [JsonProperty("cpu_usage")]
        public float? CpuUsage { get; set; }

        [JsonProperty("memory_usage")]
        public float? MemoryUsage { get; set; }

        [JsonProperty("disk_usage")]
        public float? DiskUsage { get; set; }

        [JsonProperty("queue_size")]
        public int QueueSize { get; set; } = 0;

        [JsonProperty("hostname")]
        public string? Hostname { get; set; }

        [JsonProperty("ip_address")]
        public string? IpAddress { get; set; }

        [JsonProperty("os_info")]
        public string? OsInfo { get; set; }

        [JsonProperty("agent_version")]
        public string AgentVersion { get; set; } = "2.0.0";
    }

    /// <summary>
    /// Reponse du serveur au heartbeat (contient les commandes)
    /// </summary>
    public class HeartbeatResponse
    {
        [JsonProperty("success")]
        public bool Success { get; set; }

        [JsonProperty("commands")]
        public List<AgentCommand> Commands { get; set; } = new();

        [JsonProperty("error")]
        public string? Error { get; set; }
    }

    /// <summary>
    /// Requete de detection des suppressions
    /// </summary>
    public class DeleteDetectionRequest
    {
        [JsonProperty("table_name")]
        public string TableName { get; set; } = "";

        [JsonProperty("target_table")]
        public string? TargetTable { get; set; }

        [JsonProperty("societe_code")]
        public string SocieteCode { get; set; } = "";

        [JsonProperty("primary_key")]
        public List<string> PrimaryKey { get; set; } = new();

        [JsonProperty("source_ids")]
        public List<object> SourceIds { get; set; } = new();

        [JsonProperty("source_count")]
        public int SourceCount { get; set; }
    }

    /// <summary>
    /// Reponse de detection des suppressions
    /// </summary>
    public class DeleteDetectionResponse
    {
        [JsonProperty("success")]
        public bool Success { get; set; }

        [JsonProperty("deleted_count")]
        public int DeletedCount { get; set; }

        [JsonProperty("error")]
        public string? Error { get; set; }
    }

    /// <summary>
    /// Etat de synchronisation d'un agent
    /// </summary>
    public class SyncState
    {
        public string AgentId { get; set; } = "";
        public string AgentName { get; set; } = "";

        /// <summary>
        /// Derniere sync par table (cle = nom table)
        /// </summary>
        public ConcurrentDictionary<string, DateTime> TableLastSync { get; } = new();

        /// <summary>
        /// Agent en pause
        /// </summary>
        public bool IsPaused { get; set; } = false;

        /// <summary>
        /// Statut actuel: active, syncing, paused, error, offline
        /// </summary>
        public string Status { get; set; } = "active";

        /// <summary>
        /// Tache en cours (ex: "Sync F_COMPTET")
        /// </summary>
        public string? CurrentTask { get; set; }

        /// <summary>
        /// Dernier heartbeat envoye
        /// </summary>
        public DateTime? LastHeartbeat { get; set; }

        /// <summary>
        /// Derniere sync globale
        /// </summary>
        public DateTime? LastSync { get; set; }

        /// <summary>
        /// Compteur d'erreurs consecutives
        /// </summary>
        public int ConsecutiveErrors { get; set; } = 0;

        /// <summary>
        /// Reset le compteur d'erreurs
        /// </summary>
        public void ResetErrors() => ConsecutiveErrors = 0;

        /// <summary>
        /// Incremente le compteur d'erreurs
        /// </summary>
        public void IncrementErrors() => ConsecutiveErrors++;
    }

    /// <summary>
    /// Requete de push de donnees vers le serveur
    /// </summary>
    public class PushDataRequest
    {
        [JsonProperty("table_name")]
        public string TableName { get; set; } = "";

        [JsonProperty("target_table")]
        public string? TargetTable { get; set; }

        [JsonProperty("societe_code")]
        public string SocieteCode { get; set; } = "";

        [JsonProperty("sync_type")]
        public string SyncType { get; set; } = "incremental";

        [JsonProperty("primary_key")]
        public List<string> PrimaryKey { get; set; } = new();

        [JsonProperty("columns")]
        public List<string> Columns { get; set; } = new();

        [JsonProperty("rows_count")]
        public int RowsCount { get; set; }

        [JsonProperty("data")]
        public List<Dictionary<string, object?>> Data { get; set; } = new();

        [JsonProperty("batch_id")]
        public string? BatchId { get; set; }

        [JsonProperty("sync_timestamp_start")]
        public string? SyncTimestampStart { get; set; }

        [JsonProperty("sync_timestamp_end")]
        public string? SyncTimestampEnd { get; set; }
    }

    /// <summary>
    /// Reponse du push de donnees
    /// </summary>
    public class PushDataResponse
    {
        [JsonProperty("success")]
        public bool Success { get; set; }

        [JsonProperty("rows_inserted")]
        public int RowsInserted { get; set; }

        [JsonProperty("rows_updated")]
        public int RowsUpdated { get; set; }

        [JsonProperty("duration_seconds")]
        public double DurationSeconds { get; set; }

        [JsonProperty("error")]
        public string? Error { get; set; }
    }

    /// <summary>
    /// Requete d'accusation de commande
    /// </summary>
    public class CommandAckRequest
    {
        [JsonProperty("status")]
        public string Status { get; set; } = "completed";

        [JsonProperty("success")]
        public bool Success { get; set; } = true;

        [JsonProperty("result")]
        public object? Result { get; set; }

        [JsonProperty("error")]
        public string? Error { get; set; }
    }

    /// <summary>
    /// Mode de synchronisation
    /// </summary>
    public enum SyncMode
    {
        /// <summary>
        /// Mode manuel: sync declenchee par l'utilisateur
        /// </summary>
        Manual,

        /// <summary>
        /// Mode continu: sync automatique selon intervalles
        /// </summary>
        Continuous
    }

    /// <summary>
    /// Evenement de changement d'etat de l'agent
    /// </summary>
    public class AgentStateChangedEvent
    {
        public string AgentId { get; set; } = "";
        public string OldStatus { get; set; } = "";
        public string NewStatus { get; set; } = "";
        public DateTime Timestamp { get; set; } = DateTime.Now;
    }

    /// <summary>
    /// Evenement de reception de commande
    /// </summary>
    public class CommandReceivedEvent
    {
        public string AgentId { get; set; } = "";
        public AgentCommand Command { get; set; } = new();
        public DateTime Timestamp { get; set; } = DateTime.Now;
    }
}
