namespace SageETLAgent.Integration.Sage.Models
{
    /// <summary>
    /// Représente une entrée de la ComboBox de sélection de version Sage.
    /// Ex : "Gestion commerciale 100c — 12.11"
    /// </summary>
    public class SageVersionItem
    {
        public string Label       { get; set; } = "";
        public string VersionPath { get; set; } = "";
        public SageModule Module  { get; set; }
        public string SubVersion  { get; set; } = "";

        public override string ToString() => Label;
    }
}
