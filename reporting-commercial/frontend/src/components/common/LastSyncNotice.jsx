import { useEffect, useRef } from 'react'
import { useDWH } from '../../context/DWHContext'
import { useToast } from './Toast'
import { getClientLastSync } from '../../services/api'
import { describeLastSync } from './lastSyncUtils'

/**
 * Toast rappelant la date de la derniere synchronisation ETL, affiche une fois
 * par CONNEXION et par DWH (la cle inclut le session_token : une deconnexion /
 * reconnexion rejoue donc le message, contrairement a un simple F5).
 * Silencieux en cas d'erreur : ce message est informatif, jamais bloquant.
 */

const STORAGE_PREFIX = 'optiboard.lastSyncNotice.'

function currentSessionKey() {
  try {
    const t = localStorage.getItem('session_token') || sessionStorage.getItem('session_token') || ''
    return t.slice(-12) || 'anon'
  } catch {
    return 'anon'
  }
}

export default function LastSyncNotice() {
  const { currentDWH, hasDWH } = useDWH()
  const toast = useToast()
  const shownFor = useRef(null)

  useEffect(() => {
    const code = currentDWH?.code
    if (!hasDWH || !code) return

    const storageKey = `${STORAGE_PREFIX}${currentSessionKey()}.${code}`
    if (shownFor.current === storageKey) return
    try {
      if (sessionStorage.getItem(storageKey)) {
        shownFor.current = storageKey
        return
      }
    } catch { /* sessionStorage indisponible : on affiche quand meme */ }

    let cancelled = false
    shownFor.current = storageKey

    ;(async () => {
      try {
        const res = await getClientLastSync()
        if (cancelled) return
        const info = describeLastSync(res?.data?.data)
        if (!info) return

        try { sessionStorage.setItem(storageKey, '1') } catch { /* ignore */ }

        const type = info.severity === 'error' ? 'error'
          : info.severity === 'warn' ? 'warning' : 'info'
        toast[type](info.detail, { title: info.title, duration: 8000 })
      } catch (e) {
        // Endpoint indisponible (ancien backend) : informatif, on n'alerte pas
        // l'utilisateur, mais on trace pour le diagnostic.
        console.warn('[LastSyncNotice] lecture impossible:', e?.message || e)
      }
    })()

    return () => { cancelled = true }
  }, [hasDWH, currentDWH?.code]) // eslint-disable-line react-hooks/exhaustive-deps

  return null
}
