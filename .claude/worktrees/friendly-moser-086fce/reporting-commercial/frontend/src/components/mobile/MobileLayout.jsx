import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useCallback, useState, useEffect, useRef, useMemo } from 'react'
import MobileHeader from './MobileHeader'
import BottomNavBar from './BottomNavBar'
import DesktopOnlyPage from './DesktopOnlyPage'
import MobileMenuDrawer from './MobileMenuDrawer'
import MobileReportActions, { FilterRestoreBanner } from './MobileReportActions'
import MobileNetworkBanner from './MobileNetworkBanner'
import useNetworkStatus from '../../hooks/useNetworkStatus'
import { useAuth } from '../../context/AuthContext'
import { useDWH } from '../../context/DWHContext'
import { useGlobalFilters } from '../../context/GlobalFilterContext'
import { getUserMenus } from '../../services/api'
import api from '../../services/api'
import { withCache } from '../../services/apiCache'

import DashboardView from '../../pages/DashboardView'
import GridViewDisplay from '../../pages/GridViewDisplay'
import PivotViewerV2 from '../../pages/PivotViewerV2'
import MobileHomePage from '../../pages/mobile/MobileHomePage'
import MobileProfilePage from '../../pages/mobile/MobileProfilePage'
import MobileChatPage from '../../pages/mobile/MobileChatPage'

// ─── Utilitaires menus ────────────────────────────────────────────────────────
function getUrl(menu) {
  if (menu.type === 'dashboard' && menu.target_id) return `/view/${menu.target_id}`
  if (menu.type === 'gridview' && menu.target_id) return `/grid/${menu.target_id}`
  if ((menu.type === 'pivot' || menu.type === 'pivot-v2') && menu.target_id) return `/pivot-v2/${menu.target_id}`
  if (menu.type === 'page' && menu.url) return menu.url
  return null
}
function flattenMenus(menus, result = []) {
  for (const m of menus) {
    if (m.children?.length) flattenMenus(m.children, result)
    else { const url = getUrl(m); if (url) result.push(m) }
  }
  return result
}

// ─── Pull indicator ───────────────────────────────────────────────────────────
function PullIndicator({ distance, refreshing }) {
  const size = 22, r = 9, circ = 2 * Math.PI * r
  const pct = Math.min(distance / 60, 1)
  return (
    <div
      className="absolute left-0 right-0 flex justify-center items-center z-10 pointer-events-none"
      style={{ top: -size - 4, transform: `translateY(${distance}px)`, transition: distance === 0 ? 'transform 0.2s' : 'none' }}
    >
      <div className="bg-white dark:bg-gray-800 rounded-full shadow-md p-1.5">
        {refreshing ? (
          <svg className="animate-spin" width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#e5e7eb" strokeWidth="2.5" />
            <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--color-primary-500,#3b82f6)"
              strokeWidth="2.5" strokeDasharray={`${circ*.25} ${circ*.75}`} strokeLinecap="round" />
          </svg>
        ) : (
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}
            style={{ transform: `rotate(${pct*360}deg)`, transition: 'transform 0.1s' }}>
            <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#e5e7eb" strokeWidth="2.5" />
            <circle cx={size/2} cy={size/2} r={r} fill="none"
              stroke={pct>=1 ? 'var(--color-primary-500,#3b82f6)' : '#9ca3af'}
              strokeWidth="2.5" strokeDasharray={`${circ*pct} ${circ}`} strokeLinecap="round"
              style={{ transform:'rotate(-90deg)', transformOrigin:'50% 50%' }} />
          </svg>
        )}
      </div>
    </div>
  )
}

// ─── Route protégée ───────────────────────────────────────────────────────────
function ProtectedMobileRoute({ children, pageCode }) {
  const { isAuthenticated, hasAccess, loading } = useAuth()
  if (loading) return <div className="flex-1 flex items-center justify-center"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600" /></div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (pageCode && !hasAccess(pageCode)) return <div className="flex-1 flex items-center justify-center p-6 text-center"><p className="text-gray-500 dark:text-gray-400 text-sm">Accès refusé.</p></div>
  return children
}

// ─── Layout principal ─────────────────────────────────────────────────────────
export default function MobileLayout({ appName }) {
  const { user } = useAuth()
  const { currentDWH } = useDWH()
  const location = useLocation()
  const { filters, updateFilters } = useGlobalFilters()

  const [refreshing, setRefreshing] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)
  const [menus, setMenus] = useState([])
  const [fullscreen, setFullscreen] = useState(false)
  const { isOnline, isApiReachable, lastOnlineAt } = useNetworkStatus()
  const [filterBannerDismissed, setFilterBannerDismissed] = useState(false)

  // ── Récents ───────────────────────────────────────────────────────────────
  const RECENTS_KEY = `recent_reports_${user?.id}`
  const [recents, setRecents] = useState(() => {
    try { return JSON.parse(localStorage.getItem(`recent_reports_${user?.id}`)) || [] } catch { return [] }
  })
  const allLeaves = useMemo(() => flattenMenus(menus), [menus])

  useEffect(() => {
    if (!menus.length || location.pathname === '/') return
    const match = allLeaves.find(m => getUrl(m) === location.pathname)
    if (!match) return
    setRecents(prev => {
      const entry = { id: match.id, nom: match.nom, type: match.type, icon: match.icon, url: location.pathname, visitedAt: Date.now() }
      const updated = [entry, ...prev.filter(r => r.url !== location.pathname)].slice(0, 8)
      localStorage.setItem(RECENTS_KEY, JSON.stringify(updated))
      return updated
    })
  }, [location.pathname, menus.length])

  // ── Bannière filtres sauvegardés (reset au changement de page) ────────────
  useEffect(() => {
    setFilterBannerDismissed(false)
    setFullscreen(false) // quitter le plein écran en changeant de page
  }, [location.pathname])

  // ── Charger les menus ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!user?.id) return
    withCache(
      `menus_${user.id}_${currentDWH?.code || 'default'}`,
      () => getUserMenus(user.id, currentDWH?.code || null),
      2 * 60 * 60 * 1000   // 2 heures
    )
      .then(r => setMenus(r.data?.data || r.data?.data || r.data || []))
      .catch(() => setMenus([]))
  }, [user?.id, currentDWH?.code])

  // ── Refresh ───────────────────────────────────────────────────────────────
  const handleRefresh = useCallback(async () => {
    if (refreshing) return
    setRefreshing(true)
    try {
      await api.post('/cache/clear')
      setRefreshKey(prev => prev + 1)
    } catch (e) {
      console.error('Erreur rafraîchissement:', e)
    } finally {
      setTimeout(() => setRefreshing(false), 500)
    }
  }, [refreshing])

  // ── Pull-to-refresh ───────────────────────────────────────────────────────
  const mainRef = useRef(null)
  const touchStartY = useRef(0)
  const isTouching = useRef(false)
  const [pullDistance, setPullDistance] = useState(0)
  const PULL_THRESHOLD = 60

  const onTouchStart = useCallback((e) => {
    if (mainRef.current?.scrollTop > 0) return
    touchStartY.current = e.touches[0].clientY
    isTouching.current = true
  }, [])

  const onTouchMove = useCallback((e) => {
    if (!isTouching.current || mainRef.current?.scrollTop > 0) return
    const delta = e.touches[0].clientY - touchStartY.current
    setPullDistance(delta > 0 ? Math.min(delta * 0.55, 80) : 0)
  }, [])

  const onTouchEnd = useCallback(async () => {
    isTouching.current = false
    if (pullDistance >= PULL_THRESHOLD) {
      setPullDistance(30)
      await handleRefresh()
    }
    setPullDistance(0)
  }, [pullDistance, handleRefresh])

  // ── Restaurer filtres sauvegardés ─────────────────────────────────────────
  const handleRestoreFilters = useCallback((saved) => {
    updateFilters({ dateDebut: saved.dateDebut, dateFin: saved.dateFin, annee: saved.annee })
    setFilterBannerDismissed(true)
  }, [updateFilters])

  const isOnReport = location.pathname !== '/' && location.pathname !== '/profil/password' && location.pathname !== '/chat'

  return (
    <div className={`h-screen flex flex-col bg-gray-50 dark:bg-gray-900 overflow-hidden`}>
      {/* Header — masqué en plein écran */}
      {!fullscreen && (
        <MobileHeader
          appName={appName}
          onRefresh={handleRefresh}
          refreshing={refreshing}
          onMenuOpen={() => setMenuOpen(true)}
          menus={menus}
        />
      )}

      <MobileMenuDrawer
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        menus={menus}
        appName={appName}
      />

      {/* Bannière réseau */}
      <MobileNetworkBanner
        isOnline={isOnline}
        isApiReachable={isApiReachable}
        lastOnlineAt={lastOnlineAt}
      />

      {/* Zone principale */}
      <main
        ref={mainRef}
        className="flex-1 overflow-y-auto overflow-x-hidden relative"
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <PullIndicator distance={pullDistance} refreshing={refreshing && pullDistance > 0} />

        {/* Bannière filtres sauvegardés */}
        {isOnReport && !filterBannerDismissed && (
          <FilterRestoreBanner
            pathname={location.pathname}
            onRestore={handleRestoreFilters}
            onDismiss={() => setFilterBannerDismissed(true)}
          />
        )}

        <Routes>
          <Route path="/" element={
            <ProtectedMobileRoute pageCode="dashboard">
              <MobileHomePage key={refreshKey} menus={menus} recents={recents} />
            </ProtectedMobileRoute>
          } />
          <Route path="/view/:id" element={
            <ProtectedMobileRoute pageCode="dashboard">
              <DashboardView key={refreshKey} />
            </ProtectedMobileRoute>
          } />
          <Route path="/grid/:id" element={
            <ProtectedMobileRoute pageCode="dashboard">
              <GridViewDisplay key={refreshKey} />
            </ProtectedMobileRoute>
          } />
          <Route path="/pivot-v2/:id" element={
            <ProtectedMobileRoute pageCode="dashboard">
              <PivotViewerV2 key={refreshKey} />
            </ProtectedMobileRoute>
          } />
          <Route path="/chat" element={
            <ProtectedMobileRoute>
              <MobileChatPage />
            </ProtectedMobileRoute>
          } />
          <Route path="/profil" element={
            <ProtectedMobileRoute>
              <MobileProfilePage />
            </ProtectedMobileRoute>
          } />
          <Route path="/profil/password" element={<Navigate to="/profil" replace />} />
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="*" element={<ProtectedMobileRoute><DesktopOnlyPage /></ProtectedMobileRoute>} />
        </Routes>
      </main>

      {/* Bottom nav — masqué en plein écran */}
      {!fullscreen && <BottomNavBar onMenuOpen={() => setMenuOpen(true)} />}

      {/* FAB Actions rapport */}
      <MobileReportActions
        fullscreen={fullscreen}
        onFullscreenToggle={() => setFullscreen(f => !f)}
      />

      {/* Bouton "Quitter plein écran" overlay */}
      {fullscreen && (
        <button
          onClick={() => setFullscreen(false)}
          className="fixed top-3 right-3 z-[60] flex items-center gap-1.5 bg-black/60 text-white text-xs font-semibold px-3 py-1.5 rounded-full backdrop-blur-sm"
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M8 3v3a2 2 0 01-2 2H3m18 0h-3a2 2 0 01-2-2V3m0 18v-3a2 2 0 012-2h3M3 16h3a2 2 0 012 2v3" />
          </svg>
          Quitter
        </button>
      )}
    </div>
  )
}
