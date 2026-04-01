import { useState, useEffect } from 'react'
import { ScrollText, RefreshCw } from 'lucide-react'
import { StatusBadge } from './Dashboard'
import api from '../services/api'

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

export default function Logs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [limit, setLimit] = useState(100)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get(`/logs?limit=${limit}`)
      setLogs(res.data.data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [limit])

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ScrollText className="w-6 h-6 text-blue-400" /> Logs de validation
          </h1>
          <p className="text-gray-500 text-sm mt-1">{logs.length} entrees</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={limit} onChange={e => setLimit(parseInt(e.target.value))}
            className="px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-white focus:outline-none">
            <option value={50}>50 derniers</option>
            <option value={100}>100 derniers</option>
            <option value={200}>200 derniers</option>
            <option value={500}>500 derniers</option>
          </select>
          <button onClick={load} disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Rafraichir
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800 bg-gray-900/50">
                <th className="text-left p-4 font-medium">Date</th>
                <th className="text-left p-4 font-medium">Action</th>
                <th className="text-left p-4 font-medium">Statut</th>
                <th className="text-left p-4 font-medium">Hostname</th>
                <th className="text-left p-4 font-medium">IP</th>
                <th className="text-left p-4 font-medium">Version</th>
                <th className="text-left p-4 font-medium">Message</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/20">
                  <td className="p-4 text-gray-400 text-xs whitespace-nowrap">{formatDate(log.date_action)}</td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded text-xs font-mono ${
                      log.action === 'validate' ? 'bg-blue-500/10 text-blue-400' :
                      log.action === 'generate' ? 'bg-emerald-500/10 text-emerald-400' :
                      log.action === 'deactivate' ? 'bg-orange-500/10 text-orange-400' :
                      log.action?.startsWith('status_') ? 'bg-purple-500/10 text-purple-400' :
                      log.action === 'renew' ? 'bg-cyan-500/10 text-cyan-400' :
                      'bg-gray-500/10 text-gray-400'
                    }`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="p-4"><StatusBadge status={log.status} /></td>
                  <td className="p-4 text-gray-400 text-xs">{log.hostname || '-'}</td>
                  <td className="p-4 text-gray-500 font-mono text-xs">{log.ip_address || '-'}</td>
                  <td className="p-4 text-gray-500 text-xs">{log.app_version || '-'}</td>
                  <td className="p-4 text-gray-500 text-xs max-w-xs truncate" title={log.message}>{log.message || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {logs.length === 0 && (
            <div className="p-8 text-center text-gray-600">Aucun log enregistre</div>
          )}
        </div>
      </div>
    </div>
  )
}
