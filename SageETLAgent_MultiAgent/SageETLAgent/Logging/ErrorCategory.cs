namespace SageETLAgent.Logging
{
    /// <summary>
    /// Types d'erreurs pour classification automatique
    /// </summary>
    public enum ErrorCategory
    {
        /// <summary>Echec connexion SQL, reseau, timeout</summary>
        Connection,

        /// <summary>Syntaxe SQL, schema, contraintes</summary>
        SQL,

        /// <summary>Aucune table configuree, donnees vides, PKs manquantes</summary>
        Business,

        /// <summary>Configuration manquante, chaine de connexion invalide</summary>
        Config,

        /// <summary>Erreurs HTTP du serveur de coordination</summary>
        API,

        /// <summary>Erreurs systeme de fichiers (logs)</summary>
        IO,

        /// <summary>Erreurs non classifiees</summary>
        Unknown
    }
}
