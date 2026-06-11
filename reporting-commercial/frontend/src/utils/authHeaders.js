// En-tête de session pour les appels HTTP BRUTS (fetch SSE, axios global) qui
// ne passent pas par l'instance `api` — celle-ci injecte déjà X-Session-Token
// via son intercepteur (services/api.js).
//
// Depuis l'ajout du plancher d'authentification côté backend
// (middleware tenant_context), toute route /api/* non exemptée exige une
// session VALIDE véhiculée par X-Session-Token. Les appels bruts doivent donc
// joindre ce header eux-mêmes, sinon ils reçoivent 401.
//
// Usage : headers: { 'Content-Type': 'application/json', ...sessionHeaders() }
export function sessionHeaders() {
  const h = {}
  try {
    const st = localStorage.getItem('session_token') || sessionStorage.getItem('session_token')
    if (st) h['X-Session-Token'] = st
  } catch (e) { /* ignore */ }
  return h
}
