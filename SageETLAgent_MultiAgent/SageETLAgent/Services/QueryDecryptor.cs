using System;
using System.Security.Cryptography;
using System.Text;
using SageETLAgent.Logging;

namespace SageETLAgent.Services
{
    /// <summary>
    /// Déchiffre les source_query stockées en AES-256-GCM dans APP_ETL_Agent_Tables.
    /// Format : $enc1$&lt;Base64(nonce[12] + ciphertext + tag[16])&gt;
    /// Clé symétrique partagée avec le backend Python (query_crypto.py).
    /// Les valeurs sans préfixe sont retournées telles quelles (plaintext legacy).
    /// </summary>
    public static class QueryDecryptor
    {
        private const string Prefix = "$enc1$";

        // Même clé que query_crypto.py : "optiboard-query-encrypt-2026-ks!" (32 ASCII bytes)
        private static readonly byte[] Key =
            Encoding.ASCII.GetBytes("optiboard-query-encrypt-2026-ks!");

        private static readonly SyncLogger Log = SyncLogger.Instance;

        /// <summary>
        /// Déchiffre une source_query si elle commence par $enc1$.
        /// Retourne la valeur originale si elle est vide ou non chiffrée.
        /// </summary>
        public static string? Decrypt(string? value)
        {
            if (string.IsNullOrEmpty(value))
                return value;

            if (!value.StartsWith(Prefix, StringComparison.Ordinal))
                return value; // plaintext legacy — pas touché

            try
            {
                var b64 = value[Prefix.Length..];
                var raw = Convert.FromBase64String(b64);

                // Layout : nonce(12) | ciphertext | tag(16)
                if (raw.Length < 12 + 16)
                    throw new CryptographicException("Données chiffrées trop courtes");

                var nonce      = raw[..12];
                var tag        = raw[^16..];
                var ciphertext = raw[12..^16];

                var plainBytes = new byte[ciphertext.Length];

                using var aes = new AesGcm(Key, AesGcm.TagByteSizes.MaxSize);
                aes.Decrypt(nonce, ciphertext, tag, plainBytes);

                return Encoding.UTF8.GetString(plainBytes);
            }
            catch (Exception ex)
            {
                Log.Warn(LogCategory.GENERAL,
                    $"[QueryDecryptor] Échec déchiffrement source_query: {ex.Message}");
                return null; // table ignorée en sécurité
            }
        }

        /// <summary>
        /// Retourne true si la valeur est chiffrée (préfixe $enc1$).
        /// </summary>
        public static bool IsEncrypted(string? value) =>
            !string.IsNullOrEmpty(value) &&
            value.StartsWith(Prefix, StringComparison.Ordinal);
    }
}
