import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Sun, Moon, RefreshCw, Bell, Menu, ChevronLeft, ChevronRight } from 'lucide-react'
import { useTheme } from '../../context/ThemeContext'
import MobileAlertsDrawer, { useAlertCount } from './MobileAlertsDrawer'

// ─── Trouver le chemin vers un menu depuis son URL ────────────────────────────
function getUrl(menu) {
  if (menu.type === 'dashboard' && menu.target_id) return `/view/${menu.target_id}`
  if (menu.type === 'gridview' && menu.target_id) return `/grid/${menu.target_id}`
  if ((menu.type === 'pivot' || menu.type === 'pivot-v2') && menu.target_id) return `/pivot-v2/${menu.target_id}`
  if (menu.type === 'page' && menu.url) return menu.url
  return null
}

function findMenuPath(menus, url, path = []) {
  for (const m of menus) {
    const mUrl = getUrl(m)
    if (mUrl === url) return [...path, m.nom]
    if (m.children?.length) {
      const found = findMenuPath(m.children, url, [...path, m.nom])
      if (found) return found
    }
  }
  return null
}

// ─── Breadcrumb ───────────────────────────────────────────────────────────────
function Breadcrumb({ path }) {
  if (!path || path.length === 0) return null

  // Limiter l'affichage : si > 2 niveaux, montrer "... > parent > rapport"
  const display = path.length > 2 ? ['…', ...path.slice(-2)] : path

  return (
    <div className="flex items-center gap-1 min-w-0 flex-1">
      {display.map((seg, i) => (
        <span key={i} className="flex items-center gap-1 min-w-0">
          {i > 0 && <ChevronRight className="w-3 h-3 text-gray-300 dark:text-gray-600 flex-shrink-0" />}
          <span
            className={`text-xs truncate ${
              i === display.length - 1
                ? 'font-semibold text-gray-800 dark:text-gray-100'
                : 'text-gray-400 dark:text-gray-500'
            }`}
          >
            {seg}
          </span>
        </span>
      ))}
    </div>
  )
}

// ─── Header ───────────────────────────────────────────────────────────────────
export default function MobileHeader({ appName, onRefresh, refreshing, onMenuOpen, menus = [] }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { darkMode, setDarkMode } = useTheme()
  const [alertsOpen, setAlertsOpen] = useState(false)
  const { count, reset } = useAlertCount()

  const isHome = location.pathname === '/'
  const isAccount = location.pathname === '/profil' || location.pathname === '/profil/password'

  // Breadcrumb depuis les menus
  const breadcrumbPath = !isHome && !isAccount && menus.length > 0
    ? findMenuPath(menus, location.pathname)
    : null

  return (
    <>
      <header className="flex-shrink-0 sticky top-0 z-40 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-3 py-2.5 flex items-center gap-2">

        {/* Bouton gauche : hamburger sur l'accueil, retour sinon */}
        {isHome ? (
          <button
            onClick={onMenuOpen}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex-shrink-0"
          >
            <Menu className="w-5 h-5" />
          </button>
        ) : (
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex-shrink-0"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        )}

        {/* Titre / Breadcrumb */}
        <div className="flex-1 min-w-0 flex flex-col justify-center">
          {isHome ? (
            /* Accueil : nom de l'app */
            <span className="font-bold text-primary-600 dark:text-primary-400 text-base leading-tight truncate">
              {appName || 'OptiBoard'}
            </span>
          ) : isAccount ? (
            <span className="font-semibold text-gray-800 dark:text-gray-100 text-sm">Mon Compte</span>
          ) : breadcrumbPath ? (
            /* Sur un rapport : fil d'Ariane */
            <>
              <span className="text-[10px] text-primary-500 dark:text-primary-400 font-semibold leading-tight truncate">
                {appName || 'OptiBoard'}
              </span>
              <Breadcrumb path={breadcrumbPath} />
            </>
          ) : (
            /* Fallback : type de page */
            <span className="font-semibold text-gray-800 dark:text-gray-100 text-sm">
              {location.pathname.startsWith('/view/') ? 'Dashboard'
                : location.pathname.startsWith('/grid/') ? 'GridView'
                : location.pathname.startsWith('/pivot-v2/') ? 'Pivot'
                : 'OptiBoard'}
            </span>
          )}
        </div>

        {/* Actions droite */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={refreshing}
              className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          )}

          <button
            onClick={() => setAlertsOpen(true)}
            className="relative p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <Bell className="w-4 h-4" />
            {count > 0 && (
              <span className="absolute top-1 right-1 min-w-[16px] h-4 flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold leading-none px-1">
                {count > 99 ? '99+' : count}
              </span>
            )}
          </button>

          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </header>

      <MobileAlertsDrawer
        open={alertsOpen}
        onClose={() => setAlertsOpen(false)}
        onRead={reset}
      />
    </>
  )
}
