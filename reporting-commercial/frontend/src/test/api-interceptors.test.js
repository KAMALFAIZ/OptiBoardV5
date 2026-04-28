/**
 * Tests intercepteurs API & localStorage - OptiBoard
 * Vérifie que les headers sont correctement ajoutés à chaque requête.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Mock localStorage
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = String(value) },
    removeItem: (key) => { delete store[key] },
    clear: () => { store = {} },
  }
})()

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })
Object.defineProperty(globalThis, 'sessionStorage', { value: localStorageMock })

// ─────────────────────────────────────────────
// Logique d'intercepteur — extraite pour test
// ─────────────────────────────────────────────
function buildRequestHeaders(existingHeaders = {}) {
  const headers = { ...existingHeaders }

  // Token
  const token = localStorage.getItem('token') || sessionStorage.getItem('token')
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // DWH Code
  if (!headers['X-DWH-Code']) {
    try {
      const savedDWH = localStorage.getItem('currentDWH')
      if (savedDWH) {
        const parsed = JSON.parse(savedDWH)
        if (parsed?.code) headers['X-DWH-Code'] = parsed.code
      }
    } catch (e) { /* ignore */ }
  }

  // Data Source
  if (!headers['X-Data-Source']) {
    const ds = localStorage.getItem('dataSource')
    if (ds === 'sage') headers['X-Data-Source'] = 'sage'
  }

  // User ID
  if (!headers['X-User-Id']) {
    try {
      const savedUser = localStorage.getItem('user')
      if (savedUser) {
        const parsed = JSON.parse(savedUser)
        if (parsed?.id) headers['X-User-Id'] = String(parsed.id)
      }
    } catch (e) { /* ignore */ }
  }

  return headers
}

function handleUnauthorized(status) {
  if (status === 401) {
    localStorage.removeItem('user')
    localStorage.removeItem('token')
    sessionStorage.removeItem('user')
    sessionStorage.removeItem('token')
    window.dispatchEvent(new CustomEvent('auth:session-expired'))
    return true
  }
  return false
}

// ═══════════════════════════════════════════════════════════════════
// 1. Headers de requête
// ═══════════════════════════════════════════════════════════════════
describe('buildRequestHeaders — token', () => {
  beforeEach(() => localStorage.clear())

  it('ajoute le token Authorization si présent', () => {
    localStorage.setItem('token', 'mon_token_jwt')
    const headers = buildRequestHeaders()
    expect(headers['Authorization']).toBe('Bearer mon_token_jwt')
  })

  it('ne remplace pas un Authorization existant', () => {
    localStorage.setItem('token', 'token_ls')
    const headers = buildRequestHeaders({ 'Authorization': 'Bearer token_existant' })
    expect(headers['Authorization']).toBe('Bearer token_existant')
  })

  it('pas de header Authorization si pas de token', () => {
    const headers = buildRequestHeaders()
    expect(headers['Authorization']).toBeUndefined()
  })
})

describe('buildRequestHeaders — DWH Code', () => {
  beforeEach(() => localStorage.clear())

  it('ajoute X-DWH-Code depuis localStorage', () => {
    localStorage.setItem('currentDWH', JSON.stringify({ code: 'TEST_DWH', label: 'Test' }))
    const headers = buildRequestHeaders()
    expect(headers['X-DWH-Code']).toBe('TEST_DWH')
  })

  it('pas de X-DWH-Code si localStorage vide', () => {
    const headers = buildRequestHeaders()
    expect(headers['X-DWH-Code']).toBeUndefined()
  })

  it('ne remplace pas un X-DWH-Code déjà défini', () => {
    localStorage.setItem('currentDWH', JSON.stringify({ code: 'DWH_LS' }))
    const headers = buildRequestHeaders({ 'X-DWH-Code': 'DWH_EXISTANT' })
    expect(headers['X-DWH-Code']).toBe('DWH_EXISTANT')
  })

  it('gère un JSON malformé sans crash', () => {
    localStorage.setItem('currentDWH', 'json_invalide{')
    expect(() => buildRequestHeaders()).not.toThrow()
    const headers = buildRequestHeaders()
    expect(headers['X-DWH-Code']).toBeUndefined()
  })
})

describe('buildRequestHeaders — Data Source', () => {
  beforeEach(() => localStorage.clear())

  it('ajoute X-Data-Source: sage si dataSource=sage', () => {
    localStorage.setItem('dataSource', 'sage')
    const headers = buildRequestHeaders()
    expect(headers['X-Data-Source']).toBe('sage')
  })

  it('pas de X-Data-Source si dataSource=dwh', () => {
    localStorage.setItem('dataSource', 'dwh')
    const headers = buildRequestHeaders()
    expect(headers['X-Data-Source']).toBeUndefined()
  })

  it('pas de X-Data-Source si non défini', () => {
    const headers = buildRequestHeaders()
    expect(headers['X-Data-Source']).toBeUndefined()
  })
})

describe('buildRequestHeaders — User ID', () => {
  beforeEach(() => localStorage.clear())

  it('ajoute X-User-Id depuis localStorage', () => {
    localStorage.setItem('user', JSON.stringify({ id: 42, username: 'admin' }))
    const headers = buildRequestHeaders()
    expect(headers['X-User-Id']).toBe('42')
  })

  it('X-User-Id est toujours une chaîne', () => {
    localStorage.setItem('user', JSON.stringify({ id: 7 }))
    const headers = buildRequestHeaders()
    expect(typeof headers['X-User-Id']).toBe('string')
  })

  it('pas de X-User-Id si user absent', () => {
    const headers = buildRequestHeaders()
    expect(headers['X-User-Id']).toBeUndefined()
  })

  it('gère un user JSON malformé sans crash', () => {
    localStorage.setItem('user', 'pas_du_json')
    expect(() => buildRequestHeaders()).not.toThrow()
  })
})

// ═══════════════════════════════════════════════════════════════════
// 2. Gestion 401 — déconnexion automatique
// ═══════════════════════════════════════════════════════════════════
describe('handleUnauthorized — 401', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('user', JSON.stringify({ id: 1 }))
    localStorage.setItem('token', 'valid_token')
  })

  it('retourne true pour une erreur 401', () => {
    expect(handleUnauthorized(401)).toBe(true)
  })

  it('retourne false pour une erreur 500', () => {
    expect(handleUnauthorized(500)).toBe(false)
  })

  it('vide user et token du localStorage sur 401', () => {
    handleUnauthorized(401)
    expect(localStorage.getItem('user')).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('dispatch l\'événement auth:session-expired sur 401', () => {
    const eventSpy = vi.fn()
    window.addEventListener('auth:session-expired', eventSpy)
    handleUnauthorized(401)
    expect(eventSpy).toHaveBeenCalled()
    window.removeEventListener('auth:session-expired', eventSpy)
  })

  it('ne vide pas le localStorage sur erreur non-401', () => {
    handleUnauthorized(403)
    expect(localStorage.getItem('user')).not.toBeNull()
    expect(localStorage.getItem('token')).not.toBeNull()
  })
})

// ═══════════════════════════════════════════════════════════════════
// 3. Cohérence des headers — tous présents ensemble
// ═══════════════════════════════════════════════════════════════════
describe('buildRequestHeaders — cohérence complète', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('token', 'jwt_token_test')
    localStorage.setItem('currentDWH', JSON.stringify({ code: 'PROD_DWH' }))
    localStorage.setItem('user', JSON.stringify({ id: 99 }))
    localStorage.setItem('dataSource', 'sage')
  })

  it('tous les headers requis sont présents', () => {
    const headers = buildRequestHeaders()
    expect(headers['Authorization']).toBe('Bearer jwt_token_test')
    expect(headers['X-DWH-Code']).toBe('PROD_DWH')
    expect(headers['X-User-Id']).toBe('99')
    expect(headers['X-Data-Source']).toBe('sage')
  })

  it('les headers ne sont pas vides', () => {
    const headers = buildRequestHeaders()
    Object.values(headers).forEach(v => {
      expect(v).not.toBe('')
      expect(v).not.toBeNull()
    })
  })
})
