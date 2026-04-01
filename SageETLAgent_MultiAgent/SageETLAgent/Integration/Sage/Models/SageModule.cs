using System;

namespace SageETLAgent.Integration.Sage.Models
{
    /// <summary>
    /// Modules Sage supportés pour l'intégration registre.
    /// Chaque valeur correspond à une sous-clé dans HKCU\software\Sage\.
    /// </summary>
    public enum SageModule
    {
        CIAL,   // Gestion commerciale
        CPTA,   // Comptabilité
        IMMO,   // Immobilisations
        PAIE,   // Paie
        TRES    // Trésorerie
    }

    /// <summary>
    /// Constantes associées aux modules Sage.
    /// Les noms de clés registre varient selon la locale — on détecte par Contains().
    /// </summary>
    public static class SageModuleInfo
    {
        // Fragments de noms attendus dans le registre (insensibles à la casse)
        public const string KeyCial = "Gestion commerciale";
        public const string KeyCpta = "Comptabilité";
        public const string KeyImmo = "Immobilisations";
        public const string KeyPaie = "Paie";
        public const string KeyTres = "Trésorerie";

        // Noms de processus Sage (utilisés par SageProcessDetector)
        public const string ProcessNameBase = "Sage";

        /// <summary>
        /// Tente de résoudre le module depuis le nom d'une clé registre Sage.
        /// Retourne null si le nom ne correspond à aucun module connu.
        /// </summary>
        public static SageModule? FromRegistryKey(string keyName)
        {
            if (string.IsNullOrWhiteSpace(keyName)) return null;

            // Ordre important : vérifier "Moyens de paiement" AVANT "Paie"
            // pour éviter le faux positif ("paiement" contient "paie")
            if (keyName.Contains("Moyens de paiement", StringComparison.OrdinalIgnoreCase)) return null; // hors scope
            if (keyName.Contains(KeyCial, StringComparison.OrdinalIgnoreCase)) return SageModule.CIAL;
            if (keyName.Contains(KeyCpta, StringComparison.OrdinalIgnoreCase)) return SageModule.CPTA;
            if (keyName.Contains(KeyImmo, StringComparison.OrdinalIgnoreCase)) return SageModule.IMMO;
            if (keyName.Contains(KeyPaie, StringComparison.OrdinalIgnoreCase)) return SageModule.PAIE;
            if (keyName.Contains(KeyTres, StringComparison.OrdinalIgnoreCase)) return SageModule.TRES;

            return null;
        }

        /// <summary>
        /// Retourne le libellé lisible d'un module.
        /// </summary>
        public static string ToLabel(SageModule module) => module switch
        {
            SageModule.CIAL => "Gestion commerciale",
            SageModule.CPTA => "Comptabilité",
            SageModule.IMMO => "Immobilisations",
            SageModule.PAIE => "Paie",
            SageModule.TRES => "Trésorerie",
            _               => module.ToString()
        };
    }
}
