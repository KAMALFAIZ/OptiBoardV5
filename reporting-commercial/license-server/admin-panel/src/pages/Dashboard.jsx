import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Key, Users, CheckCircle, XCircle, AlertTriangle, Clock, Activity, ArrowRight } from 'lucide-react'
import api from '../services/api'

function StatCard({ icon: Icon, label, value, color, sub }) {
  const colors = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    green: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    orange: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    gray: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  }
  return (
    <div className={`rounded-xl border p-5 ${colors[color]}`}>
      <div className="flex items-center justify-between mb-3">
        <Icon className="w-5 h-5 opacity-70" />
        {sub && <span className="text-xs opacity-50">{sub}</span>}
      </div>
      <p className="text-3xl font-bold">{value}</p>
      <p className="text-sm opacity-60 mt-1">{label}</p>
    </div>
  )
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get('/dashboard')
        setStats(res.data.data)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="p-8 text-center text-red-400">
        Erreur de connexion au serveur de licences
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Vue d'ensemble des licences OptiBoard</p>
        </div>
        <Link
          to="/licenses/generate"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
        >
          <Key className="w-4 h-4" />
          Generer une licence
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Clients" value={stats.total_clients} color="blue" />
        <StatCard icon={Key} label="Licences totales" value={stats.total_licenses} color="purple" />
        <StatCard icon={CheckCircle} label="Actives" value={stats.active_licenses} color="green" />
        <StatCard icon={AlertTriangle} label="Expirent bientot" value={stats.expiring_soon} color="orange" sub="< 30 jours" />
      </div>

      {/* Second Row */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard icon={Clock} label="Expirees" value={stats.expired_licenses} color="gray" />
        <StatCard icon={XCircle} label="Suspendues" value={stats.suspended_licenses} color="orange" />
        <StatCard icon={XCircle} label="Revoquees" value={stats.revoked_licenses} color="red" />
      </div>

      {/* Recent Checks */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl">
        <div className="flex items-center justify-between p-5 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" />
            <h2 className="font-semibold">Derniers checks de licence</h2>
          </div>
          <Link to="/logs" className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300">
            Voir tout <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left p-4 font-medium">Client</th>
                <th className="text-left p-4 font-medium">Plan</th>
                <th className="text-left p-4 font-medium">Machine</th>
                <th className="text-left p-4 font-medium">IP</th>
                <th className="text-left p-4 font-medium">Statut</th>
                <th className="text-left p-4 font-medium">Dernier check</th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_checks?.map((check, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="p-4 font-medium text-white">{check.client_name}</td>
                  <td className="p-4">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      {check.plan}
                    </span>
                  </td>
                  <td className="p-4 text-gray-400 font-mono text-xs">{check.hostname || '-'}</td>
                  <td className="p-4 text-gray-400 font-mono text-xs">{check.ip_address || '-'}</td>
                  <td className="p-4">
                    <StatusBadge status={check.status} />
                  </td>
                  <td className="p-4 text-gray-400">{formatDate(check.last_check)}</td>
                </tr>
              ))}
              {(!stats.recent_checks || stats.recent_checks.length === 0) && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-gray-600">
                    Aucun check enregistre
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export function StatusBadge({ status }) {
  const styles = {
    valid: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    expired: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
    suspended: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    revoked: 'bg-red-500/10 text-red-400 border-red-500/20',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs border ${styles[status] || styles.expired}`}>
      {status}
    </span>
  )
}
