namespace SageETLAgent.Logging
{
    /// <summary>
    /// Categories metier correspondant aux phases ETL
    /// </summary>
    public enum LogCategory
    {
        /// <summary>Lecture depuis la base Sage SQL</summary>
        EXTRACTION,

        /// <summary>Selection de strategie, filtrage incremental, CTE</summary>
        TRANSFORMATION,

        /// <summary>Ecriture DWH: MERGE, BulkCopy, DELETE+INSERT</summary>
        CHARGEMENT,

        /// <summary>Detection des suppressions: comparaison PKs source vs DWH</summary>
        DETECTION,

        /// <summary>Gestion des cycles, scheduling, sync parallele</summary>
        ORCHESTRATION,

        /// <summary>Test connexion, retry, backoff exponentiel</summary>
        CONNEXION,

        /// <summary>Heartbeat, commandes serveur, appels API</summary>
        COMMUNICATION,

        /// <summary>Demarrage, arret, configuration, divers</summary>
        GENERAL,

        /// <summary>Pointage: comparaison source vs DWH</summary>
        POINTAGE
    }
}
