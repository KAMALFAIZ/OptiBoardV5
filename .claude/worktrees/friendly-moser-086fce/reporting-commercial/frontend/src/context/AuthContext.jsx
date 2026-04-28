import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'

const AuthContext = createContext(null)

const IDLE_TIMEOUT_MS = 30 * 60 * 1000  // 30 minutes d'inactivité → déconnexion
const WARN_BEFORE_MS  =  2 * 60 * 1000  // Avertissement 2 min avant

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sessionWarning, setSessionWarning] = useState(false) // Avertissement expiration
  const idleTimerRef = useRef(null)
  const warnTimerRef = useRef(null)

  // ── Lecture initiale depuis localStorage ou sessionStorage ────────────────
  useEffect(() => {
    const savedUser  = localStorage.getItem('user')  || sessionStorage.getItem('user')
    const savedToken = localStorage.getItem('token') || sessionStorage.getItem('token')

    if (savedUser && savedToken) {
      try {
        setUser(JSON.parse(savedUser))
      } catch (e) {
        localStorage.removeItem('user');  localStorage.removeItem('token')
        sessionStorage.removeItem('user'); sessionStorage.removeItem('token')
      }
    }
    setLoading(false)
  }, [])

  // ── Déconnexion ───────────────────────────────────────────────────────────
  const logout = useCallback((reason = 'manual') => {
    setUser(null)
    setSessionWarning(false)
    localStorage.removeItem('user');  localStorage.removeItem('token')
    sessionStorage.removeItem('user'); sessionStorage.removeItem('token')
    if (reason === 'idle') {
      // Petite notification dans le titre de page
      document.title = 'Session expirée - OptiBoard'
    }
  }, [])

  // ── Réinitialisation du timer d'inactivité ────────────────────────────────
  const resetIdleTimer = useCallback(() => {
    if (!user) return
    setSessionWarning(false)
    clearTimeout(idleTimerRef.current)
    clearTimeout(warnTimerRef.current)

    // Avertissement 2 min avant
    warnTimerRef.current = setTimeout(() => {
      setSessionWarning(true)
    }, IDLE_TIMEOUT_MS - WARN_BEFORE_MS)

    // Déconnexion automatique
    idleTimerRef.current = setTimeout(() => {
      logout('idle')
    }, IDLE_TIMEOUT_MS)
  }, [user, logout])

  // ── Écoute des événements utilisateur (activité) ──────────────────────────
  useEffect(() => {
    if (!user) {
      clearTimeout(idleTimerRef.current)
      clearTimeout(warnTimerRef.current)
      return
    }
    const EVENTS = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart']
    EVENTS.forEach(e => window.addEventListener(e, resetIdleTimer, { passive: true }))
    resetIdleTimer()

    return () => {
      EVENTS.forEach(e => window.removeEventListener(e, resetIdleTimer))
      clearTimeout(idleTimerRef.current)
      clearTimeout(warnTimerRef.current)
    }
  }, [user, resetIdleTimer])

  // ── Écoute de l'événement 401 depuis l'intercepteur API ──────────────────
  useEffect(() => {
    const handleSessionExpired = () => logout('expired')
    window.addEventListener('auth:session-expired', handleSessionExpired)
    return () => window.removeEventListener('auth:session-expired', handleSessionExpired)
  }, [logout])

  // ── Login ─────────────────────────────────────────────────────────────────
  const login = useCallback((userData) => {
    setUser(userData)
    setSessionWarning(false)
  }, [])

  const _isAdminRole = (role) => role === 'admin' || role === 'superadmin'

  // Support both old format (user.role) and new format (user.role_global / user.role_dwh)
  const _effectiveRole = (u) => u?.role_global || u?.role_dwh || u?.role

  const hasAccess = (pageCode) => {
    if (!user) return false
    if (_isAdminRole(_effectiveRole(user))) return true
    return user.pages_autorisees?.includes(pageCode)
  }

  const hasSocieteAccess = (societeCode) => {
    if (!user) return false
    if (_isAdminRole(_effectiveRole(user))) return true
    return user.societes?.includes(societeCode)
  }

  const isAdmin   = () => _isAdminRole(_effectiveRole(user))
  const isEditor  = () => _effectiveRole(user) === 'editeur'

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      login,
      logout,
      hasAccess,
      hasSocieteAccess,
      isAdmin,
      isEditor,
      isAuthenticated: !!user,
      sessionWarning,
      resetIdleTimer,
    }}>
      {/* Bandeau d'avertissement session */}
      {sessionWarning && user && (
        <div
          className="fixed top-0 left-0 right-0 z-[9999] bg-amber-500 text-white text-sm
                     flex items-center justify-between px-4 py-2 shadow-lg"
        >
          <span>⚠️ Votre session expire dans 2 minutes en raison d'inactivité.</span>
          <button
            onClick={resetIdleTimer}
            className="ml-4 px-3 py-1 bg-white text-amber-600 font-semibold rounded hover:bg-amber-50 text-xs"
          >
            Rester connecté
          </button>
        </div>
      )}
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
