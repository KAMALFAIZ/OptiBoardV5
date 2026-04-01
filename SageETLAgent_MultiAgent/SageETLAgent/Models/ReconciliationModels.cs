using System;
using System.Collections.Generic;

namespace SageETLAgent.Models
{
    /// <summary>
    /// Rapport global de pointage source vs DWH
    /// </summary>
    public class ReconciliationReport
    {
        public string AgentName { get; set; } = "";
        public string SageDatabase { get; set; } = "";
        public string DwhDatabase { get; set; } = "";
        public DateTime StartTime { get; set; }
        public DateTime EndTime { get; set; }
        public double DurationSeconds { get; set; }
        public int TablesChecked { get; set; }
        public int TablesOk { get; set; }
        public int TablesWithDiffs { get; set; }
        public int TablesError { get; set; }
        public List<TableReconciliationResult> Tables { get; set; } = new();
    }

    /// <summary>
    /// Resultat de pointage pour une table
    /// </summary>
    public class TableReconciliationResult
    {
        public string TableName { get; set; } = "";
        /// <summary>OK, ECART, ERREUR</summary>
        public string Status { get; set; } = "";

        // Comptages
        public int SourceCount { get; set; }
        public int DwhCount { get; set; }
        public int CountDifference { get; set; }

        // Comparaison PKs
        public bool HasPrimaryKey { get; set; }
        public int MissingInDwh { get; set; }
        public int OrphansInDwh { get; set; }

        // Diagnostic
        public string? ErrorMessage { get; set; }
        public double DurationSeconds { get; set; }
    }
}
