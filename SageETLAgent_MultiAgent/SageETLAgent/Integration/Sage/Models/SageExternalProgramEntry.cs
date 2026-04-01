namespace SageETLAgent.Integration.Sage.Models
{
    /// <summary>
    /// Représente un programme externe à enregistrer dans le registre Sage.
    /// Correspond à une sous-clé sous HKCU\software\Sage\{version}\{sageVersion}\Personnalisation\Programmes externes\{Id}\
    /// </summary>
    public class SageExternalProgramEntry
    {
        /// <summary>
        /// Identifiant unique aléatoire (10000–99999) utilisé comme nom de sous-clé registre.
        /// Généré par SageExternalProgramBuilder pour éviter les collisions.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Libellé affiché dans le menu Sage (valeur "Nom").
        /// </summary>
        public string Caption { get; set; } = "";

        /// <summary>
        /// Paramètre transmis à l'exécutable au lancement.
        /// Format : "{AgentId} $(Dossier.InitialCatalog)"
        /// La macro Sage $(Dossier.InitialCatalog) injecte le nom de la base active.
        /// </summary>
        public string Parameters { get; set; } = "";

        /// <summary>
        /// Chemin absolu vers l'exécutable OptiBoard / SageETLAgent.
        /// Calculé depuis AppContext.BaseDirectory.
        /// </summary>
        public string ExecutablePath { get; set; } = "";

        /// <summary>
        /// URL du lien Internet (type Lien Internet = 1970433056).
        /// Si renseignée, la clé "Url" est écrite dans le registre à la place de "Path".
        /// </summary>
        public string Url { get; set; } = "";

        /// <summary>
        /// Valeur Sage identifiant le type :
        ///   1718185061 (0x665F4265) = Programme externe (exe)
        ///   1970433056 (0x75726c20) = Lien Internet (url)
        /// </summary>
        public int SageType { get; set; } = 1718185061;

        /// <summary>
        /// Code contexte Sage (2000 = menu standard).
        /// </summary>
        public int Context { get; set; } = 2000;

        /// <summary>
        /// Si true, Sage attend la fermeture du programme avant de continuer.
        /// </summary>
        public int WaitForExit { get; set; } = 0;

        /// <summary>
        /// Fermer le dossier Sage avant lancement (0 = non).
        /// </summary>
        public int CloseDossier { get; set; } = 0;

        /// <summary>
        /// ID de l'AgentProfile source (pour traçabilité).
        /// </summary>
        public string SourceAgentId { get; set; } = "";

    }
}
