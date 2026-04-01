import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Key, Plus, Search, Filter } from 'lucide-react'
import { StatusBadge } from './Dashboard'
import api from '../services/api'

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('fr-FR')
}

function daysUntil(d) {
  if (!d) return 0
  return Math.ceil((new Date(d) - new Date()) / (1000 * 60 * 60 * 24))
}

export default function Licenses() {
  const [licenses, setLicenses] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get('/licenses')
        setLicenses(res.data.data)
      } catch (e) { console.error(e) }
      finally { setLoading(false) }
    }
    load()
  }, [])

  const filtered = licenses.filter(l => {
    const matchSearch = (l.client_name?.toLowerCase().includes(search.toLowerCase()) ||
      l.client_code?.toLowerCase().includes(search.toLowerCase()) ||
      l.hostname?.toLowerCase().includes(search.toLowerCase()))
    const matchStatus = filterStatus === 'all' || l.status === filterStatus
    return matchSearch && matchStatus
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Key className="w-6 h-6 text-blue-400" /> Licences
          </h1>
          <p className="text-gray-500 text-sm mt-1">{licenses.length} licences au total</p>
        </div>
        <Link
          to="/licenses/generate"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" /> Generer une licence
        </Link>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher par client, code, machine..."
            className="w-full pl-10 pr-4 py-2.5 bg-gray-900 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
          />
        </div>
        <div className="flex items-center gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
          {['all', 'valid', 'expired', 'suspended', 'revoked'].map(s => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                filterStatus === s
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {s === 'all' ? 'Tous' : s}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800 bg-gray-900/50">
                <th className="text-left p-4 font-medium">Client</th>
                <th className="text-left p-4 font-medium">Plan</th>
                <th className="text-left p-4 font-medium">Mode</th>
                <th className="text-left p-4 font-medium">Users / DWH</th>
                <th className="text-left p-4 font-medium">Machine</th>
                <th className="text-left p-4 font-medium">Expiration</th>
                <th className="text-left p-4 font-medium">Jours rest.</th>
                <th className="text-left p-4 font-medium">Statut</th>
                <th className="text-left p-4 font-medium">Checks</th>
                <th className="p-4"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(lic => {
                const days = daysUntil(lic.expiry_date)
                return (
                  <tr key={lic.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="p-4">
                      <div>
                        <span className="font-medium text-white">{lic.client_name}</span>
                        <p className="text-xs text-gray-500 font-mono">{lic.client_code}</p>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="px-2 py-0.5 rounded-full text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 capitalize">
                        {lic.plan}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded-full text-xs border ${
                        lic.deployment_mode === 'saas'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                      }`}>
                        {lic.deployment_mode === 'saas' ? '☁️ SaaS' : '🖥️ On-Prem'}
                      </span>
                    </td>
                    <td className="p-4 text-gray-400">{lic.max_users} / {lic.max_dwh}</td>
                    <td className="p-4">
                      <div>
                        <span className="text-gray-400 text-xs">{lic.hostname || '-'}</span>
                        {lic.ip_address && <p className="text-xs text-gray-600 font-mono">{lic.ip_address}</p>}
                      </div>
                    </td>
                    <td className="p-4 text-gray-400">{formatDate(lic.expiry_date)}</td>
                    <td className="p-4">
                      <span className={`font-medium ${
                        days <= 0 ? 'text-red-400' : days <= 30 ? 'text-orange-400' : 'text-gray-400'
                      }`}>
                        {days <= 0 ? 'Expire' : `${days}j`}
                      </span>
                    </td>
                    <td className="p-4"><StatusBadge status={lic.status} /></td>
                    <td className="p-4 text-gray-500">{lic.check_count || 0}</td>
                    <td className="p-4">
                      <Link to={`/licenses/${lic.id}`} className="text-blue-400 hover:text-blue-300 text-xs font-medium">
                        Gerer
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div className="p-8 text-center text-gray-600">Aucune licence trouvee</div>
          )}
        </div>
      </div>
    </div>
  )
}
