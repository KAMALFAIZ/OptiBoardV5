import { useState } from 'react'
import {
  Server, CheckCircle, XCircle, AlertTriangle, Clock,
  RefreshCw, Pause, Play, Eye, Activity, Zap, Wifi, WifiOff,
  Trash2, Database, Download
} from 'lucide-react'

const statusConfig = {
  active: { color: 'green', icon: CheckCircle, label: 'Actif' },
  syncing: { color: 'cyan', icon: RefreshCw, label: 'Synchronisation' },
  error: { color: 'red', icon: XCircle, label: 'Erreur' },
  inactive: { color: 'gray', icon: Clock, label: 'Inactif' },
  paused: { color: 'yellow', icon: Pause, label: 'En pause' }
}

const healthConfig = {
  'En ligne': { color: 'green', icon: Wifi },
  'Hors ligne': { color: 'red', icon: WifiOff },
  'Erreur': { color: 'red', icon: AlertTriangle },
  'Jamais connecte': { color: 'gray', icon: Clock },
  'Desactive': { color: 'gray', icon: Pause },
  'Synchronisation': { color: 'cyan', icon: RefreshCw }
}

function formatDate(dateStr) {
  if (!dateStr) return 'Jamais'
  const date = new Date(dateStr)
  return date.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

function AgentCard({ agent, onAgentClick, onViewLogs, onTriggerSync, onPauseResume, onSyncTables, onDelete }) {
  const [actionLoading, setActionLoading] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const status = statusConfig[agent.status] || statusConfig.inactive
  const health = healthConfig[agent.health_status] || healthConfig['Hors ligne']
  const StatusIcon = status.icon
  const HealthIcon = health.icon

  const handleAction = async (action, handler) => {
    setActionLoading(action)
    try {
      await handler(agent)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 p-4 hover:shadow-lg transition-shadow cursor-pointer"
      onClick={() => onAgentClick(agent)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-${status.color}-100 dark:bg-${status.color}-900/30`}>
            <Server className={`text-${status.color}-600 dark:text-${status.color}-400`} size={24} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">{agent.name}</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">{agent.dwh_name || agent.dwh_code}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-${status.color}-100 text-${status.color}-700 dark:bg-${status.color}-900/30 dark:text-${status.color}-400`}>
            <StatusIcon size={12} className={agent.status === 'syncing' ? 'animate-spin' : ''} />
            {status.label}
          </span>
          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-${health.color}-100 text-${health.color}-700 dark:bg-${health.color}-900/30 dark:text-${health.color}-400`}>
            <HealthIcon size={12} />
          </span>
        </div>
      </div>

      {/* Info */}
      <div className="grid grid-cols-2 gap-2 text-sm mb-3">
        <div>
          <span className="text-gray-500 dark:text-gray-400">Dernier heartbeat:</span>
          <p className="text-gray-900 dark:text-white font-medium">{formatDate(agent.last_heartbeat)}</p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">Derniere sync:</span>
          <p className="text-gray-900 dark:text-white font-medium">{formatDate(agent.last_sync)}</p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">Tables:</span>
          <p className="text-gray-900 dark:text-white font-medium">{agent.tables_count || 0}</p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">Total syncs:</span>
          <p className="text-gray-900 dark:text-white font-medium">{agent.total_syncs || 0}</p>
        </div>
      </div>

      {/* Machine info */}
      {(agent.hostname || agent.ip_address) && (
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
          <Activity size={12} />
          {agent.hostname && <span>{agent.hostname}</span>}
          {agent.ip_address && <span>({agent.ip_address})</span>}
        </div>
      )}

      {/* Erreur */}
      {agent.last_error && agent.status === 'error' && (
        <div className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded mb-3 truncate">
          {agent.last_error}
        </div>
      )}

      {/* Actions ligne 1 */}
      <div className="flex gap-2 pt-3 border-t border-gray-200 dark:border-gray-700" onClick={(e) => e.stopPropagation()}>
        <button
          className="flex-1 px-3 py-1.5 text-sm bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400 rounded hover:bg-primary-200 dark:hover:bg-primary-900/50 flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
          onClick={() => handleAction('sync', onTriggerSync)}
          disabled={actionLoading === 'sync' || agent.status === 'syncing'}
          title="Déclencher une synchronisation Sage maintenant"
        >
          <Zap size={14} className={actionLoading === 'sync' ? 'animate-pulse' : ''} />
          Sync
        </button>
        <button
          className="flex-1 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center justify-center gap-1 transition-colors"
          onClick={() => onViewLogs(agent)}
          title="Voir les logs de synchronisation"
        >
          <Eye size={14} />
          Logs
        </button>
        <button
          className={`flex-1 px-3 py-1.5 text-sm rounded flex items-center justify-center gap-1 transition-colors ${
            agent.status === 'active' || agent.status === 'syncing'
              ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 hover:bg-yellow-200'
              : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 hover:bg-green-200'
          }`}
          onClick={() => handleAction('pauseResume', onPauseResume)}
          disabled={actionLoading === 'pauseResume'}
        >
          {agent.status === 'active' || agent.status === 'syncing' ? (
            <><Pause size={14} />Pause</>
          ) : (
            <><Play size={14} />Resume</>
          )}
        </button>
      </div>

      {/* Actions ligne 2 — Supprimer (masqué pour agents démo) */}
      {!(agent.dwh_code === 'KA' || agent.is_demo) && (
      <div className="flex gap-2 mt-2" onClick={(e) => e.stopPropagation()}>
        {!confirmDelete ? (
          <button
            className="flex-1 px-3 py-1.5 text-sm bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400 rounded hover:bg-red-100 dark:hover:bg-red-900/40 flex items-center justify-center gap-1 transition-colors"
            onClick={() => setConfirmDelete(true)}
            title="Supprimer cet agent"
          >
            <Trash2 size={14} />
            Supprimer
          </button>
        ) : (
          <div className="flex-1 flex gap-1">
            <button
              className="flex-1 px-2 py-1.5 text-xs bg-red-600 text-white rounded hover:bg-red-700 flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
              onClick={() => { handleAction('delete', onDelete); setConfirmDelete(false) }}
              disabled={actionLoading === 'delete'}
            >
              <Trash2 size={12} />
              Confirmer
            </button>
            <button
              className="flex-1 px-2 py-1.5 text-xs bg-gray-200 text-gray-700 dark:bg-gray-600 dark:text-gray-200 rounded hover:bg-gray-300 transition-colors"
              onClick={() => setConfirmDelete(false)}
            >
              Annuler
            </button>
          </div>
        )}
      </div>
      )}
    </div>
  )
}

export default function AgentList({ agents, onAgentClick, onViewLogs, onTriggerSync, onPauseResume, onSyncTables, onDelete }) {
  if (!agents || agents.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center">
        <Server size={48} className="mx-auto text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          Aucun agent configure
        </h3>
        <p className="text-gray-500 dark:text-gray-400">
          Creez un nouvel agent pour commencer la synchronisation des donnees.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {agents.map(agent => (
        <AgentCard
          key={agent.agent_id}
          agent={agent}
          onAgentClick={onAgentClick}
          onViewLogs={onViewLogs}
          onTriggerSync={onTriggerSync}
          onPauseResume={onPauseResume}
          onSyncTables={onSyncTables}
          onDelete={onDelete}
        />
      ))}
    </div>
  )
}
