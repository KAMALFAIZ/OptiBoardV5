import { useEffect, useRef } from 'react'
import { useDWH } from '../../context/DWHContext'
import { useToast } from './Toast'
import { getClientLastSync } from '../../services/api'

/**
 * Affiche, une seule fois par session et par DWH, un toast rappelant la date
 * de la derniere synchronisation ETL (agent Sage -> DWH).
 * Silencieux en cas d'erreur : ce message est informatif, jamais bloquant.
 */

const STORAGE_PREFIX = 'optiboard.lastSyncNotice.'

function formatAbsolute(iso) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return null
  return d.toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatRelative(ageSeconds) {
  if (ageSeconds == null || ageSeconds < 0) return null
  const min = Math.floor(ageSeconds / 60)
  if (min < 1) return "a l'instant"
  if (min < 60) return `il y a ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return `il y a ${h} h`
  const j = Math.floor(h / 24)
  return j === 1 ? 'il y a 1 jour' : `il y a ${j} jours`
}

export default function LastSyncNotice() {
  const { currentDWH, hasDWH } = useDWH()
  const toast = useToast()
  const shownFor = useRef(null)

  useEffect(() => {
    const code = currentDWH?.code
    if (!hasDWH || !code) return
    if (shownFor.current === code) return

    const storageKey = STORAGE_PREFIX + code
    try {
      if (sessionStorage.getItem(storageKey)) {
        shownFor.current = code
        return
      }
    } catch { /* sessionStorage indisponible : on affiche quand meme */ }

    let cancelled = false
    shownFor.current = code

    ;(async () => {
      try {
        const res = await getClientLastSync()
        if (cancelled) return
        const data = res?.data?.data
        if (!data) return

        try { sessionStorage.setItem(storageKey, '1') } catch { /* ignore */ }

        if (!data.last_sync) {
          toast.warning("Aucune synchronisation des donnees n'a encore ete effectuee.", {
            title: 'Donnees non synchronisees',
            duration: 7000,
          })
          return
        }

        const absolute = formatAbsolute(data.last_sync)
        const relative = formatRelative(data.age_seconds)
        const details = []
        if (data.tables_synced) details.push(`${data.tables_synced} tables`)
        if (data.agent_name) details.push(data.agent_name)

        const message = [
          absolute ? `Le ${absolute}${relative ? ` (${relative})` : ''}` : relative,
          details.length ? details.join(' - ') : null,
        ].filter(Boolean).join('\n')

        const stale = data.age_seconds != null && data.age_seconds > 24 * 3600
        const failed = String(data.status || '').toLowerCase() === 'error'
        const type = failed || stale ? 'warning' : 'info'

        toast[type](message, {
          title: failed
            ? 'Derniere synchronisation en erreur'
            : 'Derniere synchronisation des donnees',
          duration: 7000,
        })
      } catch {
        // Endpoint indisponible (ancien backend, ETL non configure) : on ignore.
      }
    })()

    return () => { cancelled = true }
  }, [hasDWH, currentDWH?.code]) // eslint-disable-line react-hooks/exhaustive-deps

  return null
}
