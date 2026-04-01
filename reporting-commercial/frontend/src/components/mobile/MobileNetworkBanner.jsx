/**
 * MobileNetworkBanner — Bannière de statut réseau
 * Affichages :
 *   • Hors-ligne (réseau coupé)
 *   • Serveur inaccessible (réseau OK mais API down)
 *   • Reconnecté (bref message vert)
 *   • Données en cache (indicateur discret sur la home)
 */
import { useState, useEffect, useRef } from 'react'
import { WifiOff, ServerCrash, Wifi, Database } from 'lucide-react'

export default function MobileNetworkBanner({ isOnline, isApiReachable, lastOnlineAt }) {
  const [visible,     setVisible]     = useState(false)
  const [reconnected, setReconnected] = useState(false)
  const wasDown = useRef(false)
  const reconnectTimer = useRef(null)

  useEffect(() => {
    const down = !isOnline || !isApiReachable

    if (down) {
      wasDown.current = true
      setReconnected(false)
      setVisible(true)
      clearTimeout(reconnectTimer.current)
    } else if (wasDown.current) {
      // Vient de se reconnecter
      setReconnected(true)
      setVisible(true)
      reconnectTimer.current = setTimeout(() => {
        setVisible(false)
        setReconnected(false)
        wasDown.current = false
      }, 3000)
    }

    return () => clearTimeout(reconnectTimer.current)
  }, [isOnline, isApiReachable])

  if (!visible) return null

  const isDown = !isOnline || !isApiReachable

  if (reconnected) {
    return (
      <div className="flex items-center justify-center gap-2 px-4 py-2 bg-green-500 text-white text-xs font-semibold animate-pulse-once">
        <Wifi className="w-3.5 h-3.5" />
        <span>Connexion rétablie</span>
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold ${
      !isOnline
        ? 'bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900'
        : 'bg-amber-500 text-white'
    }`}>
      {!isOnline
        ? <WifiOff className="w-3.5 h-3.5 flex-shrink-0" />
        : <ServerCrash className="w-3.5 h-3.5 flex-shrink-0" />}
      <span className="flex-1">
        {!isOnline
          ? 'Vous êtes hors-ligne'
          : 'Serveur inaccessible'}
      </span>
      {lastOnlineAt && !isOnline && (
        <span className="opacity-70 text-[10px] flex-shrink-0">
          dernière synchro {formatRelative(lastOnlineAt)}
        </span>
      )}
      <Database className="w-3.5 h-3.5 flex-shrink-0 opacity-60" title="Données en cache" />
    </div>
  )
}

// ─── Indicateur "cache" discret (pour la home quand données stale) ─────────────
export function CacheIndicator({ fromCache, cacheAge }) {
  if (!fromCache) return null
  return (
    <div className="mx-3 mb-2 flex items-center gap-1.5 text-[11px] text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-lg px-3 py-1.5">
      <Database className="w-3 h-3 flex-shrink-0" />
      <span>Données en cache {cacheAge ? `· ${cacheAge}` : ''}</span>
    </div>
  )
}

function formatRelative(date) {
  const diff = Math.floor((Date.now() - date.getTime()) / 1000)
  if (diff < 60)   return 'à l\'instant'
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`
  return `il y a ${Math.floor(diff / 3600)} h`
}
