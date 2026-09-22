/** Helpers partages par LastSyncNotice (toast) et LastSyncIndicator (badge header). */

export function formatSyncAbsolute(iso, withYear = true) {
  if (!iso) return null
  const d = new Date(iso)
  if (isNaN(d.getTime())) return null
  return d.toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit',
    ...(withYear ? { year: 'numeric' } : {}),
    hour: '2-digit', minute: '2-digit',
  })
}

export function formatSyncRelative(ageSeconds) {
  if (ageSeconds == null || ageSeconds < 0) return null
  const min = Math.floor(ageSeconds / 60)
  if (min < 1) return "a l'instant"
  if (min < 60) return `il y a ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return `il y a ${h} h`
  const j = Math.floor(h / 24)
  return j === 1 ? 'il y a 1 jour' : `il y a ${j} jours`
}

/**
 * Normalise la reponse /api/client/last-sync en un etat d'affichage unique.
 * severity : 'ok' | 'warn' | 'error'
 */
export function describeLastSync(data) {
  if (!data) return null
  const failed = String(data.status || '').toLowerCase() === 'error'
  const never = !data.last_sync

  if (never) {
    const hb = formatSyncAbsolute(data.last_heartbeat)
    return {
      severity: 'warn',
      label: 'Jamais synchronise',
      title: 'Donnees non synchronisees',
      detail: hb
        ? `Agent ${data.agent_name || 'ETL'} vu le ${hb}, mais aucune synchronisation enregistree.`
        : "Aucune synchronisation des donnees n'a encore ete effectuee.",
    }
  }

  const absolute = formatSyncAbsolute(data.last_sync)
  const relative = formatSyncRelative(data.age_seconds)
  const stale = data.age_seconds != null && data.age_seconds > 24 * 3600
  const extras = []
  if (data.tables_synced) extras.push(`${data.tables_synced} tables`)
  if (data.agent_name) extras.push(data.agent_name)

  return {
    severity: failed ? 'error' : (stale ? 'warn' : 'ok'),
    label: formatSyncAbsolute(data.last_sync, false) || '—',
    title: failed ? 'Derniere synchronisation en erreur' : 'Derniere synchronisation des donnees',
    detail: [
      absolute ? `Le ${absolute}${relative ? ` (${relative})` : ''}` : relative,
      extras.length ? extras.join(' - ') : null,
    ].filter(Boolean).join('\n'),
  }
}
