/**
 * useNetworkStatus — Détecte l'état réseau + accessibilité de l'API
 * Retourne : { isOnline, isApiReachable, lastOnlineAt }
 */
import { useState, useEffect, useRef, useCallback } from 'react'

const PING_URL = '/api/health'
const PING_INTERVAL_MS = 30_000   // vérifier toutes les 30s
const PING_TIMEOUT_MS  = 5_000    // timeout 5s

export default function useNetworkStatus() {
  const [isOnline,      setIsOnline]      = useState(navigator.onLine)
  const [isApiReachable, setIsApiReachable] = useState(true)
  const [lastOnlineAt,  setLastOnlineAt]  = useState(null)
  const abortRef = useRef(null)

  const pingApi = useCallback(async () => {
    if (!navigator.onLine) {
      setIsApiReachable(false)
      return
    }
    // Annuler le ping précédent si toujours en cours
    abortRef.current?.abort()
    abortRef.current = new AbortController()
    try {
      const res = await fetch(PING_URL, {
        method: 'GET',
        signal: AbortSignal.timeout ? AbortSignal.timeout(PING_TIMEOUT_MS) : abortRef.current.signal,
        cache: 'no-store',
      })
      if (res.ok) {
        setIsApiReachable(true)
        setLastOnlineAt(new Date())
      } else {
        setIsApiReachable(false)
      }
    } catch {
      setIsApiReachable(false)
    }
  }, [])

  useEffect(() => {
    const handleOnline  = () => { setIsOnline(true);  pingApi() }
    const handleOffline = () => { setIsOnline(false); setIsApiReachable(false) }

    window.addEventListener('online',  handleOnline)
    window.addEventListener('offline', handleOffline)

    // Premier ping au montage
    pingApi()
    const interval = setInterval(pingApi, PING_INTERVAL_MS)

    return () => {
      window.removeEventListener('online',  handleOnline)
      window.removeEventListener('offline', handleOffline)
      clearInterval(interval)
      abortRef.current?.abort()
    }
  }, [pingApi])

  return { isOnline, isApiReachable, lastOnlineAt }
}
