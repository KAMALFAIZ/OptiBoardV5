// Résolution du code client (tenant) pour le SaaS.
//
// Priorité :
//   1. Sous-domaine  →  xxxx.optiboard.kasoft.ma  ⇒  code = "XXXX"
//   2. Repli ?client=xxxx (dev local / localhost, sans sous-domaine)
//
// Le domaine de base est configurable au build via VITE_BASE_DOMAIN
// (défaut : optiboard.kasoft.ma). Les sous-domaines réservés (www, app, api…)
// ne sont PAS des tenants → on retombe sur ?client= ou null (login central).

const BASE_DOMAIN = (import.meta.env.VITE_BASE_DOMAIN || 'optiboard.kasoft.ma').toLowerCase()
const RESERVED_SUBDOMAINS = ['www', 'app', 'api', 'portal', 'admin', 'static', 'cdn', 'mail']

function _subdomainCode() {
  let host = ''
  try { host = (window.location.hostname || '').toLowerCase() } catch { return null }
  if (!host) return null
  // IP littérale ou localhost → pas de routage par sous-domaine
  if (host === 'localhost' || host.endsWith('.localhost')) return null
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return null
  // host doit finir par ".<BASE_DOMAIN>" et porter un label devant
  const suffix = '.' + BASE_DOMAIN
  if (!host.endsWith(suffix)) return null
  const left = host.slice(0, host.length - suffix.length) // labels avant le domaine de base
  if (!left) return null
  const sub = left.split('.')[0] // premier label uniquement
  if (!sub || RESERVED_SUBDOMAINS.includes(sub)) return null
  return sub.toUpperCase()
}

function _queryCode() {
  try {
    return new URLSearchParams(window.location.search).get('client')?.toUpperCase() || null
  } catch {
    return null
  }
}

/** Code client courant (sous-domaine prioritaire, puis ?client=), ou null. */
export function getClientCode() {
  return _subdomainCode() || _queryCode()
}

/** True si le client est porté par le sous-domaine (l'URL encode déjà le tenant). */
export function hasSubdomainClient() {
  return _subdomainCode() !== null
}
