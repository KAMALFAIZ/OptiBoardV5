/**
 * MobileReportActions — FAB flottant sur les pages rapport (mobile)
 * Actions : Partager · Exporter · Plein écran · Sauvegarder filtres
 */
import { useState, useCallback, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import {
  Share2, Download, Maximize2, Minimize2, Bookmark, BookmarkCheck,
  Check, X, MoreVertical, Printer, Copy,
} from 'lucide-react'
import { useGlobalFilters } from '../../context/GlobalFilterContext'

const SAVED_FILTERS_PREFIX = 'report_filters_v1_'

function getReportType(pathname) {
  if (pathname.startsWith('/view/')) return 'dashboard'
  if (pathname.startsWith('/grid/')) return 'grid'
  if (pathname.startsWith('/pivot-v2/')) return 'pivot'
  return null
}

// ─── Toast léger ─────────────────────────────────────────────────────────────
function Toast({ message, show }) {
  return (
    <div
      className={`fixed left-1/2 -translate-x-1/2 z-[200] transition-all duration-300 pointer-events-none ${
        show ? 'bottom-24 opacity-100' : 'bottom-16 opacity-0'
      }`}
    >
      <div className="flex items-center gap-2 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs font-semibold px-4 py-2 rounded-full shadow-lg">
        <Check className="w-3.5 h-3.5 flex-shrink-0" />
        {message}
      </div>
    </div>
  )
}

// ─── Bannière "filtres sauvegardés" ──────────────────────────────────────────
export function FilterRestoreBanner({ pathname, onRestore, onDismiss }) {
  const key = SAVED_FILTERS_PREFIX + pathname
  const saved = (() => { try { return JSON.parse(localStorage.getItem(key)) } catch { return null } })()
  if (!saved) return null

  return (
    <div className="mx-3 mt-2 mb-0 flex items-center gap-2 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800/40 rounded-xl px-3 py-2">
      <BookmarkCheck className="w-4 h-4 text-primary-500 flex-shrink-0" />
      <p className="flex-1 text-xs text-primary-700 dark:text-primary-300 font-medium">Filtres sauvegardés disponibles</p>
      <button onClick={() => onRestore(saved)} className="text-xs font-semibold text-primary-600 dark:text-primary-400 px-2 py-0.5 rounded hover:bg-primary-100 dark:hover:bg-primary-800/30">
        Restaurer
      </button>
      <button onClick={onDismiss} className="p-0.5 text-primary-400 hover:text-primary-600">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

// ─── FAB principal ────────────────────────────────────────────────────────────
export default function MobileReportActions({ fullscreen, onFullscreenToggle }) {
  const location = useLocation()
  const { filters, updateFilters } = useGlobalFilters()
  const [open, setOpen] = useState(false)
  const [toast, setToast] = useState({ show: false, message: '' })
  const [filtersSaved, setFiltersSaved] = useState(false)

  const reportType = getReportType(location.pathname)
  const filterKey  = SAVED_FILTERS_PREFIX + location.pathname

  // Vérifier si des filtres sont déjà sauvegardés pour cette page
  useEffect(() => {
    setOpen(false)
    const saved = (() => { try { return localStorage.getItem(filterKey) } catch { return null } })()
    setFiltersSaved(!!saved)
  }, [location.pathname, filterKey])

  // Masquer si pas sur une page rapport
  if (!reportType) return null

  const showToast = (msg) => {
    setToast({ show: true, message: msg })
    setTimeout(() => setToast({ show: false, message: '' }), 2000)
  }

  // ── Partager ────────────────────────────────────────────────────────────
  const handleShare = async () => {
    setOpen(false)
    const url = window.location.href
    const title = document.title
    if (navigator.share) {
      try { await navigator.share({ title, url }) } catch { /* annulé */ }
    } else {
      try {
        await navigator.clipboard.writeText(url)
        showToast('Lien copié !')
      } catch {
        showToast('Lien non copié')
      }
    }
  }

  // ── Exporter ─────────────────────────────────────────────────────────────
  const handleExport = () => {
    setOpen(false)
    if (reportType === 'grid') {
      // Signal à GridViewDisplay via événement custom
      window.dispatchEvent(new CustomEvent('mobile:export:csv'))
    } else {
      // Dashboard / pivot → impression
      window.print()
    }
  }

  // ── Plein écran ──────────────────────────────────────────────────────────
  const handleFullscreen = () => {
    setOpen(false)
    onFullscreenToggle?.()
  }

  // ── Sauvegarder filtres ──────────────────────────────────────────────────
  const handleSaveFilters = () => {
    setOpen(false)
    const toSave = {
      dateDebut: filters.dateDebut,
      dateFin: filters.dateFin,
      annee: filters.annee,
      savedAt: new Date().toISOString(),
    }
    localStorage.setItem(filterKey, JSON.stringify(toSave))
    setFiltersSaved(true)
    showToast('Filtres sauvegardés !')
  }

  // ── Effacer filtres sauvegardés ──────────────────────────────────────────
  const handleClearSaved = () => {
    setOpen(false)
    localStorage.removeItem(filterKey)
    setFiltersSaved(false)
    showToast('Filtres effacés')
  }

  const actions = [
    {
      icon: Share2,
      label: 'Partager le lien',
      onClick: handleShare,
      color: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-50 dark:bg-blue-900/20',
    },
    {
      icon: reportType === 'grid' ? Download : Printer,
      label: reportType === 'grid' ? 'Exporter CSV' : 'Imprimer / PDF',
      onClick: handleExport,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    },
    {
      icon: fullscreen ? Minimize2 : Maximize2,
      label: fullscreen ? 'Quitter le plein écran' : 'Plein écran',
      onClick: handleFullscreen,
      color: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-50 dark:bg-purple-900/20',
    },
    filtersSaved
      ? {
          icon: BookmarkCheck,
          label: 'Effacer les filtres sauvegardés',
          onClick: handleClearSaved,
          color: 'text-amber-600 dark:text-amber-400',
          bg: 'bg-amber-50 dark:bg-amber-900/20',
        }
      : {
          icon: Bookmark,
          label: 'Sauvegarder les filtres',
          onClick: handleSaveFilters,
          color: 'text-amber-600 dark:text-amber-400',
          bg: 'bg-amber-50 dark:bg-amber-900/20',
        },
  ]

  return (
    <>
      {/* Overlay pour fermer */}
      {open && (
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
      )}

      {/* Sheet d'actions */}
      <div
        className={`fixed right-4 z-50 flex flex-col-reverse items-end gap-2 transition-all duration-200 ${open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
        style={{ bottom: fullscreen ? '16px' : '76px' }}
      >
        {actions.map(({ icon: Icon, label, onClick, color, bg }) => (
          <button
            key={label}
            onClick={onClick}
            className={`flex items-center gap-2.5 ${bg} rounded-full pl-3 pr-4 py-2 shadow-lg border border-white/50 dark:border-gray-600/50 backdrop-blur-sm`}
          >
            <Icon className={`w-4 h-4 ${color} flex-shrink-0`} />
            <span className={`text-xs font-semibold ${color} whitespace-nowrap`}>{label}</span>
          </button>
        ))}
      </div>

      {/* FAB principal */}
      <button
        onClick={() => setOpen(o => !o)}
        className={`fixed right-4 z-50 w-11 h-11 rounded-full shadow-lg flex items-center justify-center transition-all duration-200 ${
          open
            ? 'bg-gray-700 dark:bg-gray-200 rotate-90'
            : 'bg-primary-600 dark:bg-primary-500'
        }`}
        style={{ bottom: fullscreen ? '16px' : '76px' }}
      >
        {open
          ? <X className="w-5 h-5 text-white dark:text-gray-900" />
          : <MoreVertical className="w-5 h-5 text-white" />
        }
      </button>

      {/* Toast */}
      <Toast message={toast.message} show={toast.show} />
    </>
  )
}
