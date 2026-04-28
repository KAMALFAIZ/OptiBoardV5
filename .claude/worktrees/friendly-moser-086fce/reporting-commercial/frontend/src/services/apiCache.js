/**
 * apiCache — Cache léger pour les réponses API (localStorage + TTL)
 * Utilisé en mode hors-ligne pour servir les dernières données connues.
 */

const PREFIX  = 'apicache_'
const DEFAULT_TTL = 60 * 60 * 1000   // 1 heure par défaut

// ─── Primitives ───────────────────────────────────────────────────────────────
export function cacheSet(key, data) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify({ data, ts: Date.now() }))
  } catch { /* localStorage plein — silencieux */ }
}

export function cacheGet(key, maxAge = DEFAULT_TTL) {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    if (!raw) return null
    const { data, ts } = JSON.parse(raw)
    if (Date.now() - ts > maxAge) return null   // expiré
    return data
  } catch { return null }
}

export function cacheGetStale(key) {
  // Retourne les données même expirées (pour le mode hors-ligne)
  try {
    const raw = localStorage.getItem(PREFIX + key)
    if (!raw) return null
    return JSON.parse(raw).data
  } catch { return null }
}

export function cacheClear(key) {
  try { localStorage.removeItem(PREFIX + key) } catch {}
}

export function cacheAge(key) {
  // Retourne l'âge en ms (ou Infinity si absent)
  try {
    const raw = localStorage.getItem(PREFIX + key)
    if (!raw) return Infinity
    return Date.now() - JSON.parse(raw).ts
  } catch { return Infinity }
}

// ─── Wrapper principal ────────────────────────────────────────────────────────
/**
 * withCache(key, fetchFn, ttlMs?)
 * - Essaie d'exécuter fetchFn()
 * - En cas de succès : met en cache + retourne les données fraîches
 * - En cas d'échec hors-ligne : retourne les données en cache (stale OK)
 * - En cas d'échec en ligne : propage l'erreur
 */
export async function withCache(key, fetchFn, ttlMs = DEFAULT_TTL) {
  // Vérifier le cache frais d'abord
  const fresh = cacheGet(key, ttlMs)
  if (fresh !== null) return { data: fresh, fromCache: false }

  try {
    const result = await fetchFn()
    // Extraire les data selon la forme de la réponse axios ou plain object
    const payload = result?.data !== undefined ? result.data : result
    cacheSet(key, payload)
    return { data: payload, fromCache: false }
  } catch (err) {
    // Hors-ligne → retourner le cache périmé plutôt que planter
    const stale = cacheGetStale(key)
    if (stale !== null && !navigator.onLine) {
      return { data: stale, fromCache: true }
    }
    throw err
  }
}

// ─── Helpers formatage de l'âge ──────────────────────────────────────────────
export function formatCacheAge(ms) {
  if (ms === Infinity || ms == null) return null
  const s = Math.floor(ms / 1000)
  if (s < 60)   return 'à l\'instant'
  if (s < 3600) return `il y a ${Math.floor(s / 60)} min`
  if (s < 86400) return `il y a ${Math.floor(s / 3600)} h`
  return `il y a ${Math.floor(s / 86400)} j`
}
