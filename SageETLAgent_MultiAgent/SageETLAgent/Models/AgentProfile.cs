using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace SageETLAgent.Models
{
    /// <summary>
    /// Profil d'un agent ETL (charge depuis le serveur)
    /// </summary>
    public class AgentProfile
    {
        [JsonProperty("id")]
        public int Id { get; set; }

        [JsonProperty("agent_id")]
        public string AgentId { get; set; } = "";

        [JsonProperty("dwh_code")]
        public string DwhCode { get; set; } = "";

        [JsonProperty("name")]
        public string Name { get; set; } = "";

        [JsonProperty("description")]
        public string Description { get; set; } = "";

        // Configuration Sage
        [JsonProperty("sage_server")]
        public string SageServer { get; set; } = ".";

        [JsonProperty("sage_database")]
        public string SageDatabase { get; set; } = "";

        [JsonProperty("sage_username")]
        public string SageUsername { get; set; } = "sa";

        [JsonProperty("sage_password")]
        public string SagePassword { get; set; } = "";

        // Configuration DWH
        [JsonProperty("dwh_server")]
        public string DwhServer { get; set; } = "";

        [JsonProperty("dwh_database")]
        public string DwhDatabase { get; set; } = "";

        [JsonProperty("dwh_username")]
        public string DwhUsername { get; set; } = "sa";

        [JsonProperty("dwh_password")]
        public string DwhPassword { get; set; } = "";

        // Sync settings
        [JsonProperty("sync_interval_seconds")]
        public int SyncIntervalSeconds { get; set; } = 300;

        [JsonProperty("batch_size")]
        public int BatchSize { get; set; } = 5000;

        // API Key (generalement pas retourne par l'API)
        [JsonProperty("api_key")]
        public string ApiKey { get; set; } = "";

        [JsonProperty("api_key_prefix")]
        public string ApiKeyPrefix { get; set; } = "";

        // Status
        [JsonProperty("status")]
        public string Status { get; set; } = "inactive";

        [JsonProperty("last_heartbeat")]
        public DateTime? LastHeartbeat { get; set; }

        [JsonProperty("last_sync")]
        public DateTime? LastSync { get; set; }

        [JsonProperty("last_sync_status")]
        public string LastSyncStatus { get; set; } = "";

        [JsonProperty("total_syncs")]
        public int TotalSyncs { get; set; }

        [JsonProperty("total_rows_synced")]
        public long TotalRowsSynced { get; set; }

        [JsonProperty("is_enabled")]
        public bool IsEnabled { get; set; } = true;

        [JsonProperty("is_active")]
        public bool IsActive { get; set; } = true;

        // Local state (not from API)
        [JsonIgnore]
        public bool IsSelected { get; set; } = true;

        public override string ToString() => $"{Name} ({DwhCode})";
    }

    /// <summary>
    /// Resultat de synchronisation pour une table
    /// </summary>
    public class TableSyncResult
    {
        public string TableName { get; set; } = "";
        public bool Success { get; set; }
        public int RowsSent { get; set; }
        public string? Error { get; set; }
        public double DurationSeconds { get; set; }
    }

    /// <summary>
    /// Resultat de synchronisation pour un agent
    /// </summary>
    public class AgentSyncResult
    {
        public string AgentId { get; set; } = "";
        public string AgentName { get; set; } = "";
        public bool Success { get; set; }
        public int TablesTotal { get; set; }
        public int TablesSuccess { get; set; }
        public int TotalRows { get; set; }
        public double DurationSeconds { get; set; }
        public string? Error { get; set; }
        public List<TableSyncResult> TableResults { get; set; } = new();
    }

    /// <summary>
    /// Configuration de table a synchroniser
    /// Mapping corrige pour correspondre au format API:
    /// - API retourne "name" -> TableName
    /// - API retourne "source_query" -> CustomQuery
    /// - API retourne "priority" comme string ou int
    /// - API retourne "delete_detection" comme 0/1 ou bool
    /// </summary>
    public class TableConfig
    {
        [JsonProperty("id")]
        public int Id { get; set; }

        // L'API retourne "name" au lieu de "table_name"
        [JsonProperty("name")]
        public string TableName { get; set; } = "";

        // L'API retourne "source_query" au lieu de "custom_query"
        [JsonProperty("source_query")]
        public string? CustomQuery { get; set; }

        [JsonProperty("target_table")]
        public string? TargetTable { get; set; }

        // L'API retourne "societe_code" pour identifier la societe
        [JsonProperty("societe_code")]
        public string? SocieteCode { get; set; }

        [JsonProperty("is_enabled")]
        public bool IsEnabled { get; set; } = true;

        // L'API retourne priority comme string ("normal", "high", etc.) ou int
        [JsonProperty("priority")]
        private object? _priorityRaw { get; set; } = "normal";

        [JsonIgnore]
        public int Priority
        {
            get
            {
                if (_priorityRaw is int i) return i;
                if (_priorityRaw is long l) return (int)l;
                if (_priorityRaw is string s)
                {
                    return s.ToLower() switch
                    {
                        "critical" => 1,
                        "high" => 10,
                        "normal" => 50,
                        "low" => 100,
                        _ => int.TryParse(s, out var p) ? p : 50
                    };
                }
                return 50;
            }
            set => _priorityRaw = value;
        }

        [JsonProperty("last_sync_date")]
        public string? LastSyncDate { get; set; }

        // Sync incremental
        [JsonProperty("sync_type")]
        public string SyncType { get; set; } = "full"; // "full" ou "incremental"

        [JsonProperty("timestamp_column")]
        public string? TimestampColumn { get; set; } // ex: "cbModification"

        [JsonProperty("interval_minutes")]
        public int IntervalMinutes { get; set; } = 5;

        [JsonProperty("primary_key_columns")]
        public string? PrimaryKeyColumns { get; set; } // CSV: "col1,col2"

        [JsonProperty("batch_size")]
        public int BatchSize { get; set; } = 5000;

        // Delete detection - L'API retourne 0/1 ou bool
        [JsonProperty("delete_detection")]
        private object? _deleteDetectionRaw { get; set; } = false;

        [JsonIgnore]
        public bool DeleteDetection
        {
            get
            {
                if (_deleteDetectionRaw is bool b) return b;
                if (_deleteDetectionRaw is int i) return i != 0;
                if (_deleteDetectionRaw is long l) return l != 0;
                return false;
            }
            set => _deleteDetectionRaw = value;
        }

        // Flags locaux (non serialises depuis API)
        [JsonIgnore]
        public bool SyncNow { get; set; } = false;

        [JsonIgnore]
        public bool ForceFullReload { get; set; } = false;
    }

    /// <summary>
    /// Evenement de progression
    /// </summary>
    public class SyncProgressEvent
    {
        public string AgentId { get; set; } = "";
        public string AgentName { get; set; } = "";
        public string CurrentTable { get; set; } = "";
        public int TableIndex { get; set; }
        public int TotalTables { get; set; }
        public int CurrentRows { get; set; }
        public double ProgressPercent { get; set; }
        public string Message { get; set; } = "";
    }
}
