// Résolution du code client (tenant) pour le SaaS.
//
// Le tenant est porté UNIQUEMENT par le sous-domaine : xxxx.kasoft.ma ⇒ code = "XXXX".
// En local (localhost / 127.0.0.1:PORT), une instance ne sert qu'un client → pas de
// code (null) : le DWH est choisi au login. Le domaine de base est configurable au
// build via VITE_BASE_DOMAIN (défaut : kasoft.ma). Les sous-domaines réservés
// (www, app, api…) ne sont PAS des tenants.

const BASE_DOMAIN = (import.meta.env.VITE_BASE_DOMAIN || 'kasoft.ma').toLowerCase()
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

/** Code client courant — porté par le sous-domaine ({client}.kasoft.ma), ou null. */
export function getClientCode() {
  return _subdomainCode()
}

/** True si le client est porté par le sous-domaine (l'URL encode déjà le tenant). */
export function hasSubdomainClient() {
  return _subdomainCode() !== null
}
