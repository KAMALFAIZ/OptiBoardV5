using Newtonsoft.Json;

namespace SageETLAgent.Integration.Sage.Models
{
    /// <summary>
    /// Item de menu OptiBoard récupéré depuis /api/menus/flat
    /// </summary>
    public class OptiMenuItem
    {
        [JsonProperty("id")]
        public int Id { get; set; }

        [JsonProperty("nom")]
        public string Nom { get; set; } = "";

        [JsonProperty("code")]
        public string Code { get; set; } = "";

        [JsonProperty("type")]
        public string Type { get; set; } = "";  // folder, pivot, gridview, dashboard, page, url

        [JsonProperty("parent_id")]
        public int? ParentId { get; set; }

        [JsonProperty("actif")]
        public bool Actif { get; set; } = true;

        [JsonProperty("ordre")]
        public int Ordre { get; set; }

        /// <summary>
        /// True si l'item est une feuille (pas un dossier) → programme externe Sage
        /// </summary>
        [JsonIgnore]
        public bool IsLeaf => !string.Equals(Type, "folder", System.StringComparison.OrdinalIgnoreCase);
    }
}
