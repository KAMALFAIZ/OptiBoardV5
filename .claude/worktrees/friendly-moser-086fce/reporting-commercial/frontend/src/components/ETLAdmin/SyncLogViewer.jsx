import { useState, useEffect } from 'react'
import {
  X, RefreshCw, CheckCircle, XCircle, Clock, Filter,
  ChevronDown, ChevronUp, AlertTriangle
} from 'lucide-react'
import { getAgentLogs, getAgentHeartbeats } from '../../services/etlApi'

const tabs = [
  { id: 'syncs', label: 'Synchronisations' },
  { id: 'heartbeats', label: 'Heartbeats' }
]

const statusColors = {
  success: 'green',
  error: 'red',
  running: 'cyan',
  pending: 'gray'
}

export default function SyncLogViewer({ agent, onClose }) {
  const [activeTab, setActiveTab] = useState('syncs')
  const [logs, setLogs] = useState([])
  const [heartbeats, setHeartbeats] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedLog, setExpandedLog] = useState(null)

  // Filtres
  const [filterTable, setFilterTable] = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  useEffect(() => {
    loadData()
  }, [agent.agent_id, activeTab])

  const loadData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'syncs') {
        const params = {}
        if (filterTable) params.table_name = filterTable
        if (filterStatus) params.status = filterStatus

        const res = await getAgentLogs(agent.agent_id, params)
        setLogs(res.data.data || [])
      } else {
        const res = await getAgentHeartbeats(agent.agent_id, 100)
        setHeartbeats(res.data.data || [])
      }
    } catch (err) {
      console.error('Erreur chargement logs:', err)
    } finally {
      setLoading(false)
    }
  }

  const uniqueTables = [...new Set(logs.map(l => l.table_name))]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Logs - {agent.name}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">{agent.dwh_code}</p>
          </div>
          <button onClick={onClose} className="p-1 text-gray-500 hover:text-gray-700">
            <X size={20} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-700">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-primary-600 border-b-2 border-primary-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Filters (for syncs) */}
        {activeTab === 'syncs' && (
          <div className="p-3 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex gap-3">
            <select
              className="px-3 py-1.5 text-sm bg-white dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
              value={filterTable}
              onChange={(e) => setFilterTable(e.target.value)}
            >
              <option value="">Toutes les tables</option>
              {uniqueTables.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <select
              className="px-3 py-1.5 text-sm bg-white dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">Tous les status</option>
              <option value="success">Succes</option>
              <option value="error">Erreur</option>
              <option value="running">En cours</option>
            </select>
            <button
              className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 flex items-center gap-1"
              onClick={loadData}
            >
              <RefreshCw size={14} />
              Filtrer
            </button>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="animate-spin text-primary-600" size={24} />
            </div>
          ) : activeTab === 'syncs' ? (
            <div className="space-y-2">
              {logs.map(log => (
                <LogItem
                  key={log.id}
                  log={log}
                  expanded={expandedLog === log.id}
                  onToggle={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
                />
              ))}
              {logs.length === 0 && (
                <p className="text-center text-gray-500 py-8">Aucun log de synchronisation</p>
              )}
            </div>
          ) : (
            <div className="space-y-1">
              {heartbeats.map(hb => (
                <HeartbeatItem key={hb.id} heartbeat={hb} />
              ))}
              {heartbeats.length === 0 && (
                <p className="text-center text-gray-500 py-8">Aucun heartbeat</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function LogItem({ log, expanded, onToggle }) {
  const color = statusColors[log.status] || 'gray'
  const StatusIcon = log.status === 'success' ? CheckCircle
    : log.status === 'error' ? XCircle
    : log.status === 'running' ? RefreshCw
    : Clock

  return (
    <div className={`border rounded-lg overflow-hidden ${
      log.status === 'error' ? 'border-red-200 dark:border-red-800' : 'border-gray-200 dark:border-gray-700'
    }`}>
      <div
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <StatusIcon
            size={18}
            className={`text-${color}-500 ${log.status === 'running' ? 'animate-spin' : ''}`}
          />
          <div>
            <span className="font-medium text-gray-900 dark:text-white">{log.table_name}</span>
            <span className="text-gray-500 ml-2 text-sm">({log.societe_code})</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right text-sm">
            <div className="text-gray-900 dark:text-white">{formatDate(log.started_at)}</div>
            <div className="text-gray-500">
              {log.duration_seconds ? `${log.duration_seconds.toFixed(1)}s` : '-'}
            </div>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 min-w-[100px] text-right">
            {log.rows_extracted} extraites
          </div>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {expanded && (
        <div className="p-3 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-4 gap-4 text-sm mb-3">
            <div>
              <span className="text-gray-500">Lignes extraites</span>
              <p className="font-medium">{log.rows_extracted}</p>
            </div>
            <div>
              <span className="text-gray-500">Inserees</span>
              <p className="font-medium text-green-600">{log.rows_inserted}</p>
            </div>
            <div>
              <span className="text-gray-500">Mises a jour</span>
              <p className="font-medium text-primary-600">{log.rows_updated}</p>
            </div>
            <div>
              <span className="text-gray-500">En erreur</span>
              <p className="font-medium text-red-600">{log.rows_failed}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm mb-3">
            <div>
              <span className="text-gray-500">Debut</span>
              <p>{formatDate(log.started_at)}</p>
            </div>
            <div>
              <span className="text-gray-500">Fin</span>
              <p>{formatDate(log.completed_at)}</p>
            </div>
          </div>
          {log.error_message && (
            <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded text-sm">
              <div className="flex items-start gap-2">
                <AlertTriangle size={16} className="text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-red-800 dark:text-red-300">Erreur</p>
                  <p className="text-red-600 dark:text-red-400 mt-1">{log.error_message}</p>
                </div>
              </div>
            </div>
          )}
          {log.batch_id && (
            <div className="text-xs text-gray-500 mt-2">
              Batch ID: {log.batch_id}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function HeartbeatItem({ heartbeat }) {
  const statusColors = {
    idle: 'green',
    syncing: 'cyan',
    error: 'red',
    paused: 'yellow'
  }
  const color = statusColors[heartbeat.status] || 'gray'

  return (
    <div className="flex items-center justify-between p-2 text-sm border-b border-gray-100 dark:border-gray-700">
      <div className="flex items-center gap-3">
        <span className={`w-2 h-2 rounded-full bg-${color}-500`}></span>
        <span className="text-gray-900 dark:text-white">{formatDate(heartbeat.heartbeat_time)}</span>
        <span className={`text-${color}-600 font-medium`}>{heartbeat.status}</span>
        {heartbeat.current_task && (
          <span className="text-gray-500">- {heartbeat.current_task}</span>
        )}
      </div>
      <div className="flex items-center gap-4 text-gray-500">
        {heartbeat.cpu_usage != null && (
          <span title="CPU">CPU: {heartbeat.cpu_usage.toFixed(0)}%</span>
        )}
        {heartbeat.memory_usage != null && (
          <span title="Memoire">RAM: {heartbeat.memory_usage.toFixed(0)}%</span>
        )}
        {heartbeat.queue_size != null && (
          <span title="File d'attente">Queue: {heartbeat.queue_size}</span>
        )}
      </div>
    </div>
  )
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
