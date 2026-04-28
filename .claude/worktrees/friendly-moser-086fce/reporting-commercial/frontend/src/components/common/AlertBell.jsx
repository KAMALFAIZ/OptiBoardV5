import { useState, useEffect, useRef } from 'react'
import { Bell, AlertTriangle, AlertCircle, Info, CheckCheck, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'

const NIVEAU_STYLES = {
  critical: {
    bg: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    icon: <AlertTriangle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />,
    dot: 'bg-red-500',
    badge: 'bg-red-500',
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
    icon: <AlertCircle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />,
    dot: 'bg-amber-500',
    badge: 'bg-amber-500',
  },
  info: {
    bg: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    icon: <Info className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" />,
    dot: 'bg-blue-500',
    badge: 'bg-blue-500',
  },
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const diff = Math.floor((Date.now() - date) / 1000)
  if (diff < 60) return 'à l\'instant'
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)} h`
  return `il y a ${Math.floor(diff / 86400)} j`
}

export default function AlertBell() {
  const [count, setCount] = useState(0)
  const [open, setOpen] = useState(false)
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef(null)
  const navigate = useNavigate()

  // Polling du compteur toutes les 5 minutes
  useEffect(() => {
    fetchCount()
    const interval = setInterval(fetchCount, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  // Fermer si clic extérieur
  useEffect(() => {
    function handleClick(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  async function fetchCount() {
    try {
      const res = await api.get('/alerts/count')
      if (res.data?.success) setCount(res.data.count)
    } catch {
      // silencieux si l'endpoint n'est pas encore dispo
    }
  }

  async function fetchAlerts() {
    setLoading(true)
    try {
      const res = await api.get('/alerts/history?limit=10&unread_only=true')
      if (res.data?.success) setAlerts(res.data.data || [])
    } catch {
      setAlerts([])
    } finally {
      setLoading(false)
    }
  }

  function handleOpen() {
    setOpen(prev => {
      if (!prev) fetchAlerts()
      return !prev
    })
  }

  async function acknowledgeAll() {
    try {
      await api.post('/alerts/history/acknowledge-all')
      setAlerts([])
      setCount(0)
    } catch { /* silent */ }
  }

  const badgeColor = alerts.some(a => a.niveau === 'critical')
    ? 'bg-red-500'
    : alerts.some(a => a.niveau === 'warning')
    ? 'bg-amber-500'
    : 'bg-blue-500'

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bouton cloche */}
      <button
        onClick={handleOpen}
        className="relative p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        title="Alertes KPI"
      >
        <Bell className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
        {count > 0 && (
          <span
            className={`absolute -top-0.5 -right-0.5 flex items-center justify-center
              min-w-[14px] h-[14px] px-1 rounded-full text-white text-[9px] font-bold ${badgeColor}`}
          >
            {count > 99 ? '99+' : count}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 mt-1 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50">
          {/* Header dropdown */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700">
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              Alertes KPI {count > 0 && <span className="text-xs text-gray-500">({count} non lue{count > 1 ? 's' : ''})</span>}
            </span>
            <div className="flex items-center gap-1">
              {count > 0 && (
                <button
                  onClick={acknowledgeAll}
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  title="Tout marquer comme lu"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={() => { setOpen(false); navigate('/admin/alerts') }}
                className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                title="Voir toutes les alertes"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Liste alertes */}
          <div className="max-h-72 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-6">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600" />
              </div>
            ) : alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-6 text-gray-400">
                <Bell className="w-6 h-6 mb-2 opacity-40" />
                <p className="text-xs">Aucune alerte non lue</p>
              </div>
            ) : (
              <div className="p-2 space-y-1">
                {alerts.map(alert => {
                  const style = NIVEAU_STYLES[alert.niveau] || NIVEAU_STYLES.info
                  return (
                    <div
                      key={alert.id}
                      className={`flex items-start gap-2 p-2 rounded-md border text-xs ${style.bg}`}
                    >
                      {style.icon}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 dark:text-white truncate">
                          {alert.rule_nom || 'Alerte'}
                        </p>
                        <p className="text-gray-600 dark:text-gray-300 line-clamp-2 mt-0.5">
                          {alert.message}
                        </p>
                        <p className="text-gray-400 mt-0.5">
                          {formatRelativeTime(alert.triggered_at)}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => { setOpen(false); navigate('/admin/alerts') }}
              className="w-full text-xs text-center py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              style={{ color: 'var(--color-primary-600)' }}
            >
              Gérer toutes les alertes →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
