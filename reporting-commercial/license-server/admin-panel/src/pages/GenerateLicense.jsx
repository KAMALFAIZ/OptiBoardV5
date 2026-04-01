import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { ArrowLeft, Key, Copy, CheckCircle, Zap } from 'lucide-react'
import api from '../services/api'

const PLANS = [
  { value: 'trial', label: 'Trial', desc: '30 jours, toutes fonctionnalites', color: 'gray' },
  { value: 'standard', label: 'Standard', desc: 'Modules de base', color: 'blue' },
  { value: 'premium', label: 'Premium', desc: 'Tous modules + ETL', color: 'purple' },
  { value: 'enterprise', label: 'Enterprise', desc: 'Illimite, multi-DWH', color: 'orange' },
]

const FEATURES = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'ventes', label: 'Ventes' },
  { key: 'stocks', label: 'Stocks' },
  { key: 'recouvrement', label: 'Recouvrement' },
  { key: 'admin', label: 'Administration' },
  { key: 'etl', label: 'ETL / Synchronisation' },
  { key: 'export', label: 'Export (Excel/PDF/PPT)' },
  { key: 'pivot', label: 'Pivot Tables' },
  { key: 'builder', label: 'Dashboard Builder' },
  { key: 'scheduler', label: 'Report Scheduler' },
  { key: 'all', label: 'TOUTES les fonctionnalites' },
]

export default function GenerateLicense() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState(null)
  const [copied, setCopied] = useState(false)

  const preselectedClient = searchParams.get('client_id')

  const [form, setForm] = useState({
    client_id: preselectedClient || '',
    plan: 'standard',
    max_users: 5,
    max_dwh: 1,
    expiry_days: 365,
    machine_id: '',
    features: ['dashboard', 'ventes', 'stocks', 'recouvrement'],
    deployment_mode: 'on-premise'
  })

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get('/clients')
        setClients(res.data.data)
      } catch (e) { console.error(e) }
      finally { setLoading(false) }
    }
    load()
  }, [])

  // Auto-configure features based on plan
  const handlePlanChange = (plan) => {
    let features, maxUsers, maxDwh, expiryDays
    switch (plan) {
      case 'trial':
        features = ['all']; maxUsers = 3; maxDwh = 1; expiryDays = 30; break
      case 'standard':
        features = ['dashboard', 'ventes', 'stocks', 'recouvrement', 'export']
        maxUsers = 5; maxDwh = 1; expiryDays = 365; break
      case 'premium':
        features = ['all']; maxUsers = 20; maxDwh = 3; expiryDays = 365; break
      case 'enterprise':
        features = ['all']; maxUsers = 0; maxDwh = 0; expiryDays = 365; break
      default:
        features = form.features; maxUsers = form.max_users; maxDwh = form.max_dwh; expiryDays = form.expiry_days
    }
    setForm({ ...form, plan, features, max_users: maxUsers, max_dwh: maxDwh, expiry_days: expiryDays })
  }

  const toggleFeature = (key) => {
    if (key === 'all') {
      setForm({ ...form, features: form.features.includes('all') ? [] : ['all'] })
      return
    }
    const features = form.features.filter(f => f !== 'all')
    if (features.includes(key)) {
      setForm({ ...form, features: features.filter(f => f !== key) })
    } else {
      setForm({ ...form, features: [...features, key] })
    }
  }

  const handleGenerate = async () => {
    if (!form.client_id) { alert('Selectionnez un client'); return }
    setGenerating(true)
    try {
      const res = await api.post('/licenses/generate', {
        client_id: parseInt(form.client_id),
        plan: form.plan,
        max_users: form.max_users,
        max_dwh: form.max_dwh,
        features: form.features,
        expiry_days: form.expiry_days,
        machine_id: form.deployment_mode === 'saas' ? null : (form.machine_id || null),
        deployment_mode: form.deployment_mode
      })
      setResult(res.data)
    } catch (e) {
      alert(e.response?.data?.detail || 'Erreur generation')
    } finally { setGenerating(false) }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(result.license_key)
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

  // Result screen
  if (result) {
    return (
      <div className="p-6 max-w-2xl mx-auto space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-500/20 rounded-2xl mb-4">
            <CheckCircle className="w-8 h-8 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold">Licence generee !</h1>
          <p className="text-gray-500 mt-1">{result.message}</p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Client</span>
            <span className="font-medium">{result.client}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Plan</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 capitalize">{result.plan}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Mode</span>
            <span className={`px-2 py-0.5 rounded-full text-xs border ${
              result.deployment_mode === 'saas'
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
            }`}>
              {result.deployment_mode === 'saas' ? '☁️ SaaS' : '🖥️ On-Premise'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Expiration</span>
            <span className="font-medium">{result.expiry_date}</span>
          </div>

          <div className="pt-4 border-t border-gray-800">
            <label className="block text-xs text-gray-400 mb-2">Cle de licence</label>
            <div className="relative">
              <textarea
                readOnly
                value={result.license_key}
                rows={4}
                className="w-full px-4 py-3 bg-black/40 border border-gray-700 rounded-lg text-sm text-emerald-400 font-mono resize-none"
              />
              <button
                onClick={handleCopy}
                className="absolute top-2 right-2 p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
              >
                {copied ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-gray-400" />}
              </button>
            </div>
            <p className="text-xs text-gray-600 mt-2">
              Copiez cette cle et envoyez-la au client pour activer OptiBoard.
            </p>
          </div>
        </div>

        <div className="flex justify-center gap-3">
          <button onClick={() => setResult(null)}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors">
            Generer une autre
          </button>
          <Link to="/licenses"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors">
            Voir toutes les licences
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <Link to="/licenses" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" /> Retour
      </Link>

      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Zap className="w-6 h-6 text-blue-400" /> Generer une licence
        </h1>
        <p className="text-gray-500 text-sm mt-1">Creez une nouvelle licence pour un client</p>
      </div>

      <div className="space-y-6">
        {/* Client */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <label className="block text-sm font-medium mb-3">Client *</label>
          <select
            value={form.client_id}
            onChange={e => setForm({ ...form, client_id: e.target.value })}
            className="w-full px-3 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
          >
            <option value="">-- Selectionnez un client --</option>
            {clients.map(c => (
              <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
            ))}
          </select>
        </div>

        {/* Deployment Mode */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <label className="block text-sm font-medium mb-3">Mode de deploiement *</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setForm({ ...form, deployment_mode: 'on-premise' })}
              className={`p-4 rounded-lg border text-left transition-all ${
                form.deployment_mode === 'on-premise'
                  ? 'bg-blue-600/15 border-blue-500/40 text-blue-400'
                  : 'bg-gray-800/50 border-gray-700 text-gray-400 hover:border-gray-600'
              }`}
            >
              <span className="block text-sm font-bold">🖥️ On-Premise</span>
              <span className="block text-xs opacity-60 mt-1">Installe chez le client. Lie a une machine specifique.</span>
            </button>
            <button
              onClick={() => setForm({ ...form, deployment_mode: 'saas', machine_id: '' })}
              className={`p-4 rounded-lg border text-left transition-all ${
                form.deployment_mode === 'saas'
                  ? 'bg-emerald-600/15 border-emerald-500/40 text-emerald-400'
                  : 'bg-gray-800/50 border-gray-700 text-gray-400 hover:border-gray-600'
              }`}
            >
              <span className="block text-sm font-bold">☁️ SaaS</span>
              <span className="block text-xs opacity-60 mt-1">Heberge sur votre serveur. Pas de binding machine.</span>
            </button>
          </div>
        </div>

        {/* Plan */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <label className="block text-sm font-medium mb-3">Plan</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {PLANS.map(p => (
              <button
                key={p.value}
                onClick={() => handlePlanChange(p.value)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  form.plan === p.value
                    ? 'bg-blue-600/15 border-blue-500/40 text-blue-400'
                    : 'bg-gray-800/50 border-gray-700 text-gray-400 hover:border-gray-600'
                }`}
              >
                <span className="block text-sm font-medium capitalize">{p.label}</span>
                <span className="block text-xs opacity-60 mt-0.5">{p.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Limits */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <label className="block text-sm font-medium mb-3">Limites</label>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Max utilisateurs</label>
              <input type="number" min={0} value={form.max_users}
                onChange={e => setForm({ ...form, max_users: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
              <p className="text-xs text-gray-600 mt-1">0 = illimite</p>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Max DWH</label>
              <input type="number" min={0} value={form.max_dwh}
                onChange={e => setForm({ ...form, max_dwh: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
              <p className="text-xs text-gray-600 mt-1">0 = illimite</p>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Duree (jours)</label>
              <input type="number" min={1} value={form.expiry_days}
                onChange={e => setForm({ ...form, expiry_days: parseInt(e.target.value) || 365 })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
            </div>
          </div>
        </div>

        {/* Machine ID - Only for On-Premise */}
        {form.deployment_mode === 'on-premise' && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <label className="block text-sm font-medium mb-1.5">Machine ID (optionnel)</label>
            <input value={form.machine_id}
              onChange={e => setForm({ ...form, machine_id: e.target.value })}
              placeholder="Laissez vide pour lier automatiquement a la premiere activation"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/30 font-mono" />
            <p className="text-xs text-gray-600 mt-1">Le client peut voir son Machine ID sur la page d'activation</p>
          </div>
        )}

        {/* SaaS Info */}
        {form.deployment_mode === 'saas' && (
          <div className="bg-emerald-900/20 border border-emerald-500/20 rounded-xl p-5">
            <p className="text-sm text-emerald-400 font-medium">☁️ Mode SaaS</p>
            <p className="text-xs text-emerald-400/60 mt-1">
              La licence ne sera pas liee a une machine. Elle peut etre activee sur n'importe quel serveur.
              Ideal pour votre hebergement centralise.
            </p>
          </div>
        )}

        {/* Features */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <label className="block text-sm font-medium mb-3">Fonctionnalites</label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {FEATURES.map(f => (
              <button
                key={f.key}
                onClick={() => toggleFeature(f.key)}
                className={`px-3 py-2 rounded-lg text-xs font-medium text-left transition-all border ${
                  form.features.includes(f.key) || form.features.includes('all')
                    ? 'bg-blue-600/15 border-blue-500/30 text-blue-400'
                    : 'bg-gray-800/50 border-gray-700 text-gray-500 hover:border-gray-600'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Generate */}
        <button
          onClick={handleGenerate}
          disabled={generating || !form.client_id}
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/30 disabled:cursor-not-allowed rounded-xl text-sm font-semibold transition-colors flex items-center justify-center gap-2"
        >
          {generating ? (
            <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> Generation...</>
          ) : (
            <><Key className="w-5 h-5" /> Generer la licence</>
          )}
        </button>
      </div>
    </div>
  )
}
