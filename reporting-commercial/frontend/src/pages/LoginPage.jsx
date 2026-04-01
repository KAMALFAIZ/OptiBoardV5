import { useState, useEffect } from 'react'
import { Eye, EyeOff, LogIn, AlertCircle, XCircle, KeyRound, ShieldCheck } from 'lucide-react'
import { login, getClientInfo, getDwhList, extractErrorMessage, setFirstPassword } from '../services/api'

// ── Écran d'erreur pleine page (code invalide ou base absente) ──────────────
function EcranErreurClient({ code, message }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 p-4">
      <div className="w-full max-w-md text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-white/20 rounded-full mb-6">
          <XCircle className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-2">Accès impossible</h1>
        <p className="text-primary-200 mb-6">{message}</p>
        <p className="text-primary-300 text-sm">
          Code : <span className="font-mono font-bold text-white">{code}</span>
        </p>
        <p className="text-primary-400 text-xs mt-6">
          Contactez l'administrateur OptiBoard pour obtenir une URL valide.
        </p>
      </div>
    </div>
  )
}

// ── Formulaire de création du mot de passe (premier login) ──────────────────
function SetPasswordForm({ userId, dwhCode, clientInfo, onDone }) {
  const [newPwd, setNewPwd]       = useState('')
  const [confirmPwd, setConfirm]  = useState('')
  const [showPwd, setShowPwd]     = useState(false)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (newPwd.length < 6) { setError('Le mot de passe doit contenir au moins 6 caractères'); return }
    if (newPwd !== confirmPwd) { setError('Les mots de passe ne correspondent pas'); return }
    setLoading(true); setError(null)
    try {
      await setFirstPassword(userId, dwhCode, newPwd)
      onDone(newPwd)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la définition du mot de passe'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
      <div className="flex flex-col items-center mb-6">
        <div className="w-14 h-14 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center mb-3">
          <KeyRound className="w-7 h-7 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white text-center">Bienvenue !</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center mt-1">
          Créez votre mot de passe pour accéder à {clientInfo?.nom || 'OptiBoard'}
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Nouveau mot de passe</label>
          <div className="relative">
            <input
              type={showPwd ? 'text' : 'password'}
              value={newPwd}
              onChange={e => setNewPwd(e.target.value)}
              required autoFocus minLength={6}
              placeholder="Minimum 6 caractères"
              className="w-full px-4 py-2.5 pr-12 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
            />
            <button type="button" onClick={() => setShowPwd(!showPwd)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              {showPwd ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Confirmer le mot de passe</label>
          <input
            type={showPwd ? 'text' : 'password'}
            value={confirmPwd}
            onChange={e => setConfirm(e.target.value)}
            required minLength={6}
            placeholder="Répétez le mot de passe"
            className="w-full px-4 py-2.5 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
          />
        </div>
        <button type="submit" disabled={loading || !newPwd || !confirmPwd}
          className="w-full py-2.5 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg flex items-center justify-center gap-2 transition-colors">
          {loading
            ? <><div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />Enregistrement...</>
            : <><ShieldCheck className="w-5 h-5" />Définir mon mot de passe</>}
        </button>
      </form>
    </div>
  )
}

// ── Page de login principale ─────────────────────────────────────────────────
export default function LoginPage({ onLogin, appName }) {
  const clientCode = new URLSearchParams(window.location.search).get('client')?.toUpperCase() || null

  const [username, setUsername]         = useState('')
  const [password, setPassword]         = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe]     = useState(true)   // "Se souvenir de moi"
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)
  // Premier login
  const [firstLoginUserId, setFirstLoginUserId] = useState(null)
  const [firstLoginDone, setFirstLoginDone]     = useState(false)

  // Infos branding client
  const [clientInfo, setClientInfo]         = useState(null)
  const [clientLoading, setClientLoading]   = useState(!!clientCode)
  const [clientNotFound, setClientNotFound] = useState(false)

  useEffect(() => {
    if (!clientCode) return
    getClientInfo(clientCode)
      .then(res => setClientInfo(res.data))
      .catch(() => setClientNotFound(true))
      .finally(() => setClientLoading(false))
  }, [clientCode])

  // Auto-login après création du mot de passe
  useEffect(() => {
    if (!firstLoginDone || !password || !username) return
    setFirstLoginDone(false)
    // Déclencher le submit automatiquement
    const credentials = { username, password }
    if (clientCode) credentials.dwh_code = clientCode
    setLoading(true)
    login(credentials).then(response => {
      if (response.data.success) {
        store('user', JSON.stringify(response.data.user))
        store('token', response.data.token)
        if (clientCode) store('currentDWH', JSON.stringify({ code: clientCode, nom: clientInfo?.nom || clientCode }))
        onLogin(response.data.user)
      }
    }).catch(() => setError('Erreur lors de la connexion automatique')).finally(() => setLoading(false))
  }, [firstLoginDone]) // eslint-disable-line

  // ── A0) Premier login : afficher le formulaire de création de mot de passe ─
  if (firstLoginUserId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-full shadow-lg mb-4">
              <span className="text-primary-600 font-extrabold text-3xl">K</span>
            </div>
            <h1 className="text-2xl font-bold text-white">{clientInfo?.nom || 'OptiBoard'}</h1>
            <p className="text-primary-200 mt-1">Reporting Commercial</p>
          </div>
          <SetPasswordForm
            userId={firstLoginUserId}
            dwhCode={clientCode}
            clientInfo={clientInfo}
            onDone={(newPwd) => {
              // Re-login automatique avec le nouveau mot de passe
              setFirstLoginUserId(null)
              setPassword(newPwd)
              setFirstLoginDone(true)
            }}
          />
          <p className="text-center text-primary-200 text-sm mt-6">© 2026 KAsoft — Reporting Commercial</p>
        </div>
      </div>
    )
  }

  // ── A) Code invalide → écran d'erreur immédiat ──────────────────────────
  if (clientCode && !clientLoading && clientNotFound) {
    return (
      <EcranErreurClient
        code={clientCode}
        message={`Le code client "${clientCode}" n'existe pas dans le système.`}
      />
    )
  }

  // ── Stockage selon "Se souvenir de moi" ──────────────────────────────────
  const store = (key, value) => {
    if (rememberMe) {
      localStorage.setItem(key, value)
      sessionStorage.removeItem(key)
    } else {
      sessionStorage.setItem(key, value)
      localStorage.removeItem(key)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const credentials = { username, password }
      if (clientCode) credentials.dwh_code = clientCode

      const response = await login(credentials)
      if (response.data.success) {
        // ── Premier login : forcer création mot de passe ──────────────────────
        if (response.data.must_change_password) {
          setFirstLoginUserId(response.data.first_login_user_id)
          return
        }

        // ── B) Base OptiBoard_CODE absente → erreur sans passer au dashboard ──
        if (clientCode && response.data.has_client_db === false) {
          setError(
            `La base de données OptiBoard_${clientCode} n'a pas encore été créée. ` +
            `Contactez l'administrateur.`
          )
          return
        }

        store('user',  JSON.stringify(response.data.user))
        store('token', response.data.token)

        // ── C) Toujours écrire currentDWH complet si clientCode présent ──────
        if (clientCode) {
          store('currentDWH', JSON.stringify({
            code: clientCode,
            nom: clientInfo?.nom || clientCode,
          }))
        }

        // ── D) Admin central sans clientCode ────────────────────────────────
        // Le superadmin NE doit PAS avoir de currentDWH par défaut :
        // il accède à la base maître et choisit lui-même le client à consulter.
        // Un non-superadmin (admin_client) auto-sélectionne son DWH.
        if (!clientCode) {
          const isSuperadmin = response.data.user?.role_global === 'superadmin' || response.data.user?.role === 'superadmin'
          if (!isSuperadmin) {
            try {
              const dwhRes = await getDwhList(response.data.user.id)
              const list = dwhRes.data || []
              if (list.length > 0) {
                const def = list.find(d => d.is_default) || list[0]
                store('currentDWH', JSON.stringify({
                  code: def.code,
                  nom: def.nom || def.raison_sociale || def.code,
                }))
              }
            } catch (e) { /* ignore */ }
          } else {
            // Superadmin : effacer currentDWH pour repartir en mode maître
            localStorage.removeItem('currentDWH')
            sessionStorage.removeItem('currentDWH')
          }
        }

        onLogin(response.data.user)
      } else {
        setError('Identifiants incorrects')
      }
    } catch (err) {
      console.error('Login error:', err)
      setError(extractErrorMessage(err, 'Erreur de connexion'))
    } finally {
      setLoading(false)
    }
  }

  // Nom affiché dans le titre
  const displayName = clientInfo?.nom
    ? clientInfo.nom
    : (appName ? appName.split(' - ')[0] : 'OptiBoard')
  const displaySub = clientInfo?.nom
    ? 'Reporting Commercial'
    : (appName && appName.includes(' - ') ? appName.split(' - ').slice(1).join(' - ') : 'Reporting')

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 p-4">
      <div className="w-full max-w-md">
        {/* Logo et titre */}
        <div className="text-center mb-8">
          {clientInfo?.logo_url ? (
            <div className="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-4 overflow-hidden">
              <img src={clientInfo.logo_url} alt={displayName} className="w-16 h-16 object-contain" />
            </div>
          ) : (
            <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-full shadow-lg mb-4">
              <span className="text-primary-600 font-extrabold text-3xl">K</span>
            </div>
          )}
          <h1 className="text-2xl font-bold text-white">
            {clientLoading ? <span className="opacity-50">Chargement...</span> : displayName}
          </h1>
          <p className="text-primary-200 mt-1">{displaySub}</p>
        </div>

        {/* Formulaire */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 text-center">
            Connexion
          </h2>

          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Nom d'utilisateur */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Nom d'utilisateur
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                placeholder="Entrez votre identifiant"
                className="w-full px-4 py-2.5 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-white transition-colors"
              />
            </div>

            {/* Mot de passe */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Mot de passe
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Entrez votre mot de passe"
                  className="w-full px-4 py-2.5 pr-12 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-white transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Se souvenir de moi */}
            <div className="flex items-center gap-2">
              <input
                id="rememberMe"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
              />
              <label htmlFor="rememberMe" className="text-sm text-gray-600 dark:text-gray-400 cursor-pointer select-none">
                Se souvenir de moi
              </label>
              <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">
                {rememberMe ? '🔒 Session persistante' : '🕐 Session temporaire'}
              </span>
            </div>

            {/* Bouton connexion */}
            <button
              type="submit"
              disabled={loading || !username || clientLoading}
              className="w-full py-2.5 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Connexion...
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  Se connecter
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Contactez l'administrateur si vous avez oublié vos identifiants
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-primary-200 text-sm mt-6">
          © 2026 KAsoft — Reporting Commercial
        </p>
      </div>
    </div>
  )
}
