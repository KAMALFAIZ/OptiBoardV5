import { useEffect, useState, useCallback } from 'react'
import { RefreshCw, AlertTriangle, Database } from 'lucide-react'
import { useDWH } from '../../context/DWHContext'
import { getClientLastSync } from '../../services/api'
import { describeLastSync } from './lastSyncUtils'

/**
 * Badge permanent de l'en-tete : date de la derniere synchronisation ETL du DWH
 * courant. Se rafraichit au changement de DWH et toutes les 5 minutes.
 * Ne s'affiche pas tant qu'aucune donnee n'a pu etre lue (aucun encombrement
 * visuel si le backend ne connait pas l'endpoint).
 */

const REFRESH_MS = 5 * 60 * 1000

const STYLES = {
  ok:    'text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700/60',
  warn:  'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30',
  error: 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/30',
}

export default function LastSyncIndicator() {
  const { currentDWH, hasDWH } = useDWH()
  const [info, setInfo] = useState(null)

  const load = useCallback(async () => {
    if (!hasDWH || !currentDWH?.code) return
    try {
      const res = await getClientLastSync()
      setInfo(describeLastSync(res?.data?.data))
    } catch {
      setInfo(null)
    }
  }, [hasDWH, currentDWH?.code])

  useEffect(() => {
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => clearInterval(id)
  }, [load])

  if (!info) return null

  const Icon = info.severity === 'ok' ? Database
    : info.severity === 'error' ? AlertTriangle : RefreshCw

  return (
    <div
      className={`hidden md:flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${STYLES[info.severity]}`}
      title={`${info.title}\n${info.detail}`}
    >
      <Icon className="w-3.5 h-3.5 flex-shrink-0" />
      <span className="whitespace-nowrap">Sync : {info.label}</span>
    </div>
  )
}
