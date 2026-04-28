import { useState, useEffect } from 'react'
import { Shield, Key, AlertTriangle, CheckCircle, Copy, RefreshCw, XCircle } from 'lucide-react'
import { useLicense } from '../context/LicenseContext'
import api from '../services/api'

export default function LicensePage({ onActivated }) {
  const { activateLicense, isLicensed, license, error } = useLicense()
  const [licenseKey, setLicenseKey] = useState('')
  const [machineId, setMachineId] = useState('')
  const [activating, setActivating] = useState(false)
  const [message, setMessage] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const fetchMachineId = async () => {
      try {
        const res = await api.get('/license/machine-id')
        setMachineId(res.data.machine_id)
      } catch (e) {
        console.error('Erreur machine ID:', e)
      }
    }
    fetchMachineId()
  }, [])

  const handleActivate = async () => {
    if (!licenseKey.trim()) {
      setMessage({ type: 'error', text: 'Veuillez saisir une cle de licence' })
      return
    }

    setActivating(true)
    setMessage(null)

    const result = await activateLicense(licenseKey.trim())

    if (result.success) {
      setMessage({ type: 'success', text: result.message })
      setTimeout(() => {
        if (onActivated) onActivated()
      }, 1500)
    } else {
      setMessage({ type: 'error', text: result.message })
    }

    setActivating(false)
  }

  const handleCopyMachineId = () => {
    navigator.clipboard.writeText(machineId)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-blue-600/20 rounded-2xl mb-4">
            <Shield className="w-10 h-10 text-blue-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">OptiBoard</h1>
          <p className="text-blue-300/70">Activation de la licence</p>
        </div>

        {/* Card */}
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8">
          {/* Machine ID */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-blue-300/70 mb-2">
              Identifiant machine
            </label>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-black/30 border border-white/10 rounded-lg px-4 py-3 text-white/60 font-mono text-sm truncate">
                {machineId || 'Chargement...'}
              </div>
              <button
                onClick={handleCopyMachineId}
                className="flex-shrink-0 p-3 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 rounded-lg text-blue-400 transition-colors"
                title="Copier l'identifiant"
              >
                {copied ? <CheckCircle className="w-5 h-5 text-green-400" /> : <Copy className="w-5 h-5" />}
              </button>
            </div>
            <p className="text-xs text-white/30 mt-1">
              Communiquez cet identifiant a votre fournisseur pour obtenir une licence
            </p>
          </div>

          {/* License Key Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-blue-300/70 mb-2">
              <Key className="w-4 h-4 inline mr-1" />
              Cle de licence
            </label>
            <textarea
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              placeholder="Collez votre cle de licence ici..."
              rows={4}
              className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/20 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 resize-none"
            />
          </div>

          {/* Message */}
          {message && (
            <div className={`mb-6 p-4 rounded-lg flex items-start gap-3 ${
              message.type === 'success'
                ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                : 'bg-red-500/10 border border-red-500/30 text-red-400'
            }`}>
              {message.type === 'success'
                ? <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                : <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              }
              <span className="text-sm">{message.text}</span>
            </div>
          )}

          {/* Activate Button */}
          <button
            onClick={handleActivate}
            disabled={activating || !licenseKey.trim()}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/30 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {activating ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                Activation en cours...
              </>
            ) : (
              <>
                <Shield className="w-5 h-5" />
                Activer la licence
              </>
            )}
          </button>

          {/* Expiry Warning (if already licensed) */}
          {isLicensed && license && (
            <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <span className="text-green-400 font-medium">Licence active</span>
              </div>
              <div className="text-sm text-white/50 space-y-1">
                <p>Organisation: <span className="text-white/80">{license.organization}</span></p>
                <p>Plan: <span className="text-white/80 capitalize">{license.plan}</span></p>
                <p>Expire le: <span className="text-white/80">{license.expiry_date ? new Date(license.expiry_date).toLocaleDateString('fr-FR') : '-'}</span></p>
                <p>Jours restants: <span className={`font-medium ${license.days_remaining <= 30 ? 'text-orange-400' : 'text-white/80'}`}>{license.days_remaining}</span></p>
              </div>
            </div>
          )}

          {/* Grace Mode Warning */}
          {license?.grace_mode && (
            <div className="mt-4 p-3 bg-orange-500/10 border border-orange-500/30 rounded-lg flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-orange-300">
                <p className="font-medium">Mode grace actif</p>
                <p className="text-orange-300/70">Serveur de licences injoignable. {license.grace_days_remaining} jours restants.</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-6">
          <p className="text-white/20 text-xs">
            OptiBoard v1.0.0 - Reporting Commercial
          </p>
        </div>
      </div>
    </div>
  )
}
