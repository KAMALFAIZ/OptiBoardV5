import { useState, useEffect } from 'react'
import { ShieldCheck, Smartphone, CheckCircle, XCircle, AlertCircle, Copy, RefreshCw } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

export default function Setup2FAPage() {
  const { user } = useAuth()
  const [status, setStatus]       = useState(null)   // {totp_enabled}
  const [setup, setSetup]         = useState(null)   // {qr_code_base64, secret, uri}
  const [code, setCode]           = useState('')
  const [loading, setLoading]     = useState(false)
  const [loadingSetup, setLoadingSetup] = useState(false)
  const [error, setError]         = useState(null)
  const [success, setSuccess]     = useState(null)
  const [copied, setCopied]       = useState(false)

  const isCentral = !user?.from_client_db
  const dwhCode   = (() => {
    try {
      const s = localStorage.getItem('currentDWH') || sessionStorage.getItem('currentDWH')
      return s ? JSON.parse(s)?.code : null
    } catch { return null }
  })()

  // Charger le statut 2FA actuel
  useEffect(() => {
    if (!user?.id) return
    api.get(`/auth/2fa/status/${user.id}`, { params: { is_central: isCentral, dwh_code: dwhCode } })
      .then(res => setStatus(res.data))
      .catch(() => {})
  }, [user?.id])

  const handleSetup = async () => {
    setLoadingSetup(true); setError(null)
    try {
      const res = await api.post('/auth/2fa/setup', { user_id: user.id, is_central: isCentral, dwh_code: dwhCode })
      setSetup(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la génération du QR code')
    } finally {
      setLoadingSetup(false)
    }
  }

  const handleActivate = async (e) => {
    e.preventDefault()
    if (code.length !== 6) { setError('Le code doit contenir 6 chiffres'); return }
    setLoading(true); setError(null)
    try {
      await api.post('/auth/2fa/activate', { user_id: user.id, totp_code: code, is_central: isCentral, dwh_code: dwhCode })
      setSuccess('Authentification à deux facteurs activée avec succès !')
      setStatus({ totp_enabled: true })
      setSetup(null); setCode('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Code invalide')
      setCode('')
    } finally {
      setLoading(false)
    }
  }

  const handleDisable = async () => {
    if (!code || code.length !== 6) { setError('Entrez votre code 2FA actuel pour désactiver'); return }
    setLoading(true); setError(null)
    try {
      await api.post('/auth/2fa/disable', { user_id: user.id, totp_code: code, is_central: isCentral, dwh_code: dwhCode })
      setSuccess('Authentification à deux facteurs désactivée.')
      setStatus({ totp_enabled: false })
      setSetup(null); setCode('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Code invalide')
      setCode('')
    } finally {
      setLoading(false)
    }
  }

  const copySecret = () => {
    if (setup?.secret) {
      navigator.clipboard.writeText(setup.secret)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900/30 rounded-xl flex items-center justify-center">
          <ShieldCheck className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Authentification à deux facteurs (2FA)</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Renforcez la sécurité de votre compte administrateur</p>
        </div>
      </div>

      {/* Statut actuel */}
      {status && (
        <div className={`flex items-center gap-3 p-4 rounded-xl border ${
          status.totp_enabled
            ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800'
            : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'
        }`}>
          {status.totp_enabled
            ? <CheckCircle className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
            : <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
          }
          <div>
            <div className={`font-semibold text-sm ${status.totp_enabled ? 'text-emerald-700 dark:text-emerald-300' : 'text-amber-700 dark:text-amber-300'}`}>
              {status.totp_enabled ? '2FA activé — votre compte est protégé' : '2FA non activé — votre compte est vulnérable'}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {status.totp_enabled
                ? 'Un code à 6 chiffres sera demandé à chaque connexion.'
                : 'Activez le 2FA pour sécuriser l\'accès administrateur.'}
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-emerald-700 dark:text-emerald-300 text-sm">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* Section activation */}
      {!status?.totp_enabled && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 space-y-5">
          <h2 className="font-semibold text-gray-900 dark:text-white">Activer le 2FA</h2>

          {!setup ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Vous aurez besoin d'une application d'authentification comme{' '}
                <strong>Google Authenticator</strong>, <strong>Authy</strong> ou <strong>Microsoft Authenticator</strong>.
              </p>
              <button
                onClick={handleSetup}
                disabled={loadingSetup}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-colors"
              >
                {loadingSetup
                  ? <><RefreshCw className="w-4 h-4 animate-spin" />Génération...</>
                  : <><Smartphone className="w-4 h-4" />Générer le QR code</>}
              </button>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Étape 1 : scanner */}
              <div>
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Étape 1 — Scannez ce QR code avec votre application
                </div>
                <div className="flex flex-col sm:flex-row gap-5 items-start">
                  {setup.qr_code_base64 ? (
                    <img
                      src={`data:image/png;base64,${setup.qr_code_base64}`}
                      alt="QR Code 2FA"
                      className="w-40 h-40 border border-gray-200 dark:border-gray-600 rounded-lg"
                    />
                  ) : (
                    <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs font-mono break-all text-gray-600 dark:text-gray-400 max-w-xs">
                      {setup.uri}
                    </div>
                  )}
                  <div className="space-y-2">
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Si vous ne pouvez pas scanner le QR code, entrez cette clé manuellement dans votre application :
                    </p>
                    <div className="flex items-center gap-2">
                      <code className="text-xs font-mono bg-gray-100 dark:bg-gray-900 px-3 py-1.5 rounded-lg text-gray-800 dark:text-gray-200 tracking-wider">
                        {setup.secret}
                      </code>
                      <button onClick={copySecret} className="text-gray-400 hover:text-indigo-600 transition-colors" title="Copier">
                        {copied ? <CheckCircle className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Étape 2 : valider */}
              <div>
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Étape 2 — Entrez le code affiché par votre application pour confirmer
                </div>
                <form onSubmit={handleActivate} className="flex gap-3">
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={code}
                    onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    autoFocus
                    className="w-36 px-4 py-2.5 border border-indigo-300 dark:border-indigo-600 rounded-lg focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-white text-center text-xl font-mono tracking-widest"
                  />
                  <button
                    type="submit"
                    disabled={loading || code.length !== 6}
                    className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-colors"
                  >
                    {loading
                      ? <><RefreshCw className="w-4 h-4 animate-spin" />Activation...</>
                      : <><CheckCircle className="w-4 h-4" />Activer</>}
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Section désactivation */}
      {status?.totp_enabled && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-red-200 dark:border-red-900 p-6 space-y-4">
          <h2 className="font-semibold text-red-700 dark:text-red-400">Désactiver le 2FA</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Entrez votre code 2FA actuel pour confirmer la désactivation.
          </p>
          <div className="flex gap-3">
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              className="w-36 px-4 py-2.5 border border-red-300 dark:border-red-600 rounded-lg focus:ring-2 focus:ring-red-500 dark:bg-gray-700 dark:text-white text-center text-xl font-mono tracking-widest"
            />
            <button
              onClick={handleDisable}
              disabled={loading || code.length !== 6}
              className="flex items-center gap-2 px-5 py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-colors"
            >
              {loading
                ? <><RefreshCw className="w-4 h-4 animate-spin" />Désactivation...</>
                : <><XCircle className="w-4 h-4" />Désactiver</>}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
