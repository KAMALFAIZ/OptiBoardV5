import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Key, Copy, CheckCircle, XCircle, Pause, RefreshCw, Clock, Monitor, Globe, Activity } from 'lucide-react'
import { StatusBadge } from './Dashboard'
import api from '../services/api'

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

function daysUntil(d) {
  if (!d) return 0
  return Math.ceil((new Date(d) - new Date()) / (1000 * 60 * 60 * 24))
}

export default function LicenseDetail() {
  const { id } = useParams()
  const [license, setLicense] = useState(null)
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const [copied, setCopied] = useState(false)
  const [renewDays, setRenewDays] = useState(365)
  const [showRenew, setShowRenew] = useState(false)

  const load = async () => {
    try {
      const res = await api.get(`/licenses/${id}`)
      setLicense(res.data.data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [id])

  const handleStatusChange = async (newStatus) => {
    const messages = {
      valid: 'Reactiver cette licence ?',
      suspended: 'Suspendre cette licence ? Le client ne pourra plus utiliser l\'application.',
      revoked: 'REVOQUER cette licence ? Cette action est definitive.'
    }
    if (!confirm(messages[newStatus])) return
    setActing(true)
    try {
      await api.put(`/licenses/${id}/status`, { status: newStatus })
      load()
    } catch (e) { alert('Erreur: ' + e.message) }
    finally { setActing(false) }
  }

  const handleRenew = async () => {
    setActing(true)
    try {
      const res = await api.put(`/licenses/${id}/renew`, { expiry_days: renewDays })
      alert(res.data.message + '\n\nNouvelle cle:\n' + res.data.new_license_key)
      setShowRenew(false)
      load()
    } catch (e) { alert('Erreur: ' + e.message) }
    finally { setActing(false) }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(license.license_key)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    )
  }

  if (!license) {
    return <div className="p-8 text-red-400">Licence non trouvee</div>
  }

  const days = daysUntil(license.expiry_date)
  const features = license.features ? JSON.parse(license.features) : []

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <Link to="/licenses" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" /> Retour
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-purple-600/20 rounded-xl flex items-center justify-center">
            <Key className="w-7 h-7 text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">{license.client_name}</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className="px-2 py-0.5 rounded-full text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 capitalize">
                {license.plan}
              </span>
              <StatusBadge status={license.status} />
              {days > 0 && days <= 30 && (
                <span className="px-2 py-0.5 rounded-full text-xs bg-orange-500/10 text-orange-400 border border-orange-500/20">
                  Expire dans {days}j
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        {license.status !== 'valid' && (
          <button onClick={() => handleStatusChange('valid')} disabled={acting}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-400 border border-emerald-500/20 rounded-lg text-sm transition-colors disabled:opacity-50">
            <CheckCircle className="w-4 h-4" /> Reactiver
          </button>
        )}
        {license.status === 'valid' && (
          <button onClick={() => handleStatusChange('suspended')} disabled={acting}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600/10 hover:bg-orange-600/20 text-orange-400 border border-orange-500/20 rounded-lg text-sm transition-colors disabled:opacity-50">
            <Pause className="w-4 h-4" /> Suspendre
          </button>
        )}
        {license.status !== 'revoked' && (
          <button onClick={() => handleStatusChange('revoked')} disabled={acting}
            className="flex items-center gap-2 px-4 py-2 bg-red-600/10 hover:bg-red-600/20 text-red-400 border border-red-500/20 rounded-lg text-sm transition-colors disabled:opacity-50">
            <XCircle className="w-4 h-4" /> Revoquer
          </button>
        )}
        <button onClick={() => setShowRenew(!showRenew)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/20 rounded-lg text-sm transition-colors">
          <RefreshCw className="w-4 h-4" /> Renouveler
        </button>
      </div>

      {/* Renew Panel */}
      {showRenew && (
        <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-5">
          <h3 className="font-medium text-blue-400 mb-3">Renouveler la licence</h3>
          <div className="flex items-end gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Duree (jours)</label>
              <input type="number" min={1} value={renewDays}
                onChange={e => setRenewDays(parseInt(e.target.value) || 365)}
                className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white w-32 focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
            </div>
            <button onClick={handleRenew} disabled={acting}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
              Confirmer le renouvellement
            </button>
            <button onClick={() => setShowRenew(false)} className="px-4 py-2 text-gray-400 text-sm hover:text-white">
              Annuler
            </button>
          </div>
          <p className="text-xs text-gray-600 mt-2">
            Une nouvelle cle sera generee. Vous devrez la transmettre au client.
          </p>
        </div>
      )}

      {/* Info Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">Max utilisateurs</p>
          <p className="text-xl font-bold">{license.max_users || '∞'}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">Max DWH</p>
          <p className="text-xl font-bold">{license.max_dwh || '∞'}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">Expiration</p>
          <p className="text-sm font-medium">{formatDate(license.expiry_date)}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">Validations</p>
          <p className="text-xl font-bold">{license.check_count || 0}</p>
        </div>
      </div>

      {/* Machine Info */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="font-medium mb-4 flex items-center gap-2">
          <Monitor className="w-4 h-4 text-blue-400" /> Machine associee
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-500">Machine ID</p>
            <p className="text-gray-300 font-mono text-xs mt-1">{license.machine_id === '*' ? 'Non liee' : license.machine_id || 'Non liee'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Hostname</p>
            <p className="text-gray-300 mt-1">{license.hostname || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Adresse IP</p>
            <p className="text-gray-300 font-mono mt-1">{license.ip_address || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Derniere validation</p>
            <p className="text-gray-300 mt-1">{formatDate(license.last_check)}</p>
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="font-medium mb-3">Fonctionnalites</h3>
        <div className="flex flex-wrap gap-2">
          {features.map(f => (
            <span key={f} className="px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-lg text-xs capitalize">
              {f}
            </span>
          ))}
        </div>
      </div>

      {/* License Key */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium">Cle de licence</h3>
          <button onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs transition-colors">
            {copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copie !' : 'Copier'}
          </button>
        </div>
        <div className="bg-black/40 border border-gray-700 rounded-lg p-3 font-mono text-xs text-gray-400 break-all max-h-24 overflow-auto">
          {license.license_key}
        </div>
      </div>

      {/* Logs */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl">
        <div className="p-5 border-b border-gray-800">
          <h3 className="font-medium flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-400" /> Historique des validations
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left p-3 font-medium text-xs">Action</th>
                <th className="text-left p-3 font-medium text-xs">Statut</th>
                <th className="text-left p-3 font-medium text-xs">Machine</th>
                <th className="text-left p-3 font-medium text-xs">IP</th>
                <th className="text-left p-3 font-medium text-xs">Message</th>
                <th className="text-left p-3 font-medium text-xs">Date</th>
              </tr>
            </thead>
            <tbody>
              {license.logs?.map((log, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/20">
                  <td className="p-3 text-xs">{log.action}</td>
                  <td className="p-3"><StatusBadge status={log.status} /></td>
                  <td className="p-3 text-xs text-gray-500 font-mono">{log.hostname || log.machine_id?.substring(0, 12) || '-'}</td>
                  <td className="p-3 text-xs text-gray-500 font-mono">{log.ip_address || '-'}</td>
                  <td className="p-3 text-xs text-gray-500 max-w-xs truncate">{log.message}</td>
                  <td className="p-3 text-xs text-gray-500">{formatDate(log.date_action)}</td>
                </tr>
              ))}
              {(!license.logs || license.logs.length === 0) && (
                <tr><td colSpan={6} className="p-6 text-center text-gray-600 text-xs">Aucun log</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
