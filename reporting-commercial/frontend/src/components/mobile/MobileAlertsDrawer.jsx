import { useState, useEffect, useRef } from 'react'
import { Bell, AlertTriangle, AlertCircle, Info, X, CheckCheck } from 'lucide-react'
import api from '../../services/api'

const NIVEAU_STYLES = {
  critical: {
    bg: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    icon: <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />,
    badge: 'bg-red-500',
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
    icon: <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0" />,
    badge: 'bg-amber-500',
  },
  info: {
    bg: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    icon: <Info className="w-4 h-4 text-blue-500 flex-shrink-0" />,
    badge: 'bg-blue-500',
  },
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return ''
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000)
  if (diff < 60) return "à l'instant"
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)} h`
  return `il y a ${Math.floor(diff / 86400)} j`
}

// ─── Badge compteur (exporté séparément) ─────────────────────────────────────
export function useAlertCount() {
  const [count, setCount] = useState(0)
  const prevCount = useRef(0)

  useEffect(() => {
    const fetchCount = async () => {
      try {
        const res = await api.get('/alerts/count')
        if (!res.data?.success) return
        const newCount = res.data.count || 0
        // Notification push si nouvelles alertes + permission accordée
        if (newCount > prevCount.current && prevCount.current >= 0 && Notification?.permission === 'granted') {
          const diff = newCount - prevCount.current
          new Notification('⚠️ OptiBoard — Nouvelle alerte KPI', {
            body: `${diff} nouvelle${diff > 1 ? 's' : ''} alerte${diff > 1 ? 's' : ''} KPI non lue${diff > 1 ? 's' : ''}`,
            icon: '/favicon.ico',
            tag: 'kpi-alert',
          })
        }
        prevCount.current = newCount
        setCount(newCount)
      } catch { /* silencieux */ }
    }
    fetchCount()
    const id = setInterval(fetchCount, 5 * 60 * 1000)
    return () => clearInterval(id)
  }, [])

  const reset = () => setCount(0)
  return { count, reset }
}

// ─── Drawer alertes ───────────────────────────────────────────────────────────
export default function MobileAlertsDrawer({ open, onClose, onRead }) {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    const fetch = async () => {
      setLoading(true)
      try {
        const res = await api.get('/alerts/history?limit=20&unread_only=true')
        if (res.data?.success) setAlerts(res.data.data || [])
      } catch {
        setAlerts([])
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [open])

  const acknowledgeAll = async () => {
    try {
      await api.post('/alerts/history/acknowledge-all')
      setAlerts([])
      onRead?.()
    } catch { /* silencieux */ }
  }

  const badgeColor = alerts.some(a => a.niveau === 'critical')
    ? 'bg-red-500'
    : alerts.some(a => a.niveau === 'warning')
    ? 'bg-amber-500'
    : 'bg-blue-500'

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      {/* Drawer slide-up */}
      <div
        className={`fixed inset-x-0 bottom-0 z-50 flex flex-col bg-white dark:bg-gray-900 rounded-t-2xl shadow-2xl transition-transform duration-300 ease-out ${
          open ? 'translate-y-0' : 'translate-y-full'
        }`}
        style={{ maxHeight: '80vh' }}
      >
        {/* Handle */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full bg-gray-300 dark:bg-gray-600" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            <span className="font-semibold text-gray-900 dark:text-white text-base">Alertes KPI</span>
            {alerts.length > 0 && (
              <span className={`text-xs text-white font-bold px-2 py-0.5 rounded-full ${badgeColor}`}>
                {alerts.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {alerts.length > 0 && (
              <button
                onClick={acknowledgeAll}
                className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 font-medium px-2 py-1 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-900/20 active:bg-primary-100 transition-colors"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                Tout lire
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {loading ? (
            <div className="flex justify-center py-10">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600" />
            </div>
          ) : alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <Bell className="w-8 h-8 mb-3 opacity-30" />
              <p className="text-sm">Aucune alerte non lue</p>
            </div>
          ) : (
            alerts.map(alert => {
              const style = NIVEAU_STYLES[alert.niveau] || NIVEAU_STYLES.info
              return (
                <div
                  key={alert.id}
                  className={`flex gap-3 p-3 rounded-xl border ${style.bg}`}
                >
                  {style.icon}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                      {alert.rule_name || alert.metric || '—'}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 line-clamp-2">
                      {alert.message}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {formatRelativeTime(alert.triggered_at || alert.created_at)}
                    </p>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Safe area bottom padding */}
        <div className="safe-area-pb" />
      </div>
    </>
  )
}
