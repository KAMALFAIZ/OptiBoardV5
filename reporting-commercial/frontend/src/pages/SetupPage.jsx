import { useState } from 'react'
import {
  Database, Server, User, Lock, CheckCircle, XCircle, AlertCircle,
  Settings, Loader2, ChevronRight, ChevronLeft, Eye, EyeOff,
  Wifi, RefreshCw, Copy, Check, Shield, Sparkles, Building2,
  UserCog, Briefcase, Mail
} from 'lucide-react'
import api, { extractErrorMessage } from '../services/api'

const STEPS = [
  { id: 1, label: 'SQL',     icon: Server },
  { id: 2, label: 'Client',  icon: Building2 },
  { id: 3, label: 'Admin',   icon: UserCog },
  { id: 4, label: 'Sage',    icon: Briefcase },
  { id: 5, label: 'Test',    icon: Wifi },
  { id: 6, label: 'Terminé', icon: CheckCircle },
]

function StepIndicator({ current }) {
  return (
    <div className="flex items-center justify-center gap-0 mb-10">
      {STEPS.map((step, i) => {
        const Icon = step.icon
        const done    = current > step.id
        const active  = current === step.id
        return (
          <div key={step.id} className="flex items-center">
            <div className="flex flex-col items-center">
              <div className={`
                w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300
                ${done   ? 'bg-green-500 text-white shadow-lg shadow-green-200'
                         : active ? 'bg-white text-blue-600 shadow-lg ring-4 ring-blue-200'
                         : 'bg-blue-500/30 text-blue-200'}
              `}>
                {done ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
              </div>
              <span className={`text-[10px] mt-1.5 font-medium whitespace-nowrap
                ${active ? 'text-white' : done ? 'text-green-300' : 'text-blue-300'}`}>
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`w-8 h-0.5 mb-5 mx-1 transition-all duration-500
                ${current > step.id ? 'bg-green-400' : 'bg-blue-500/30'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function Field({ label, icon: Icon, children, hint }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5 flex items-center gap-1.5">
        {Icon && <Icon className="w-4 h-4 text-gray-400" />}
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  )
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const handle = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={handle}
      className="ml-2 p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
      {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

export default function SetupPage({ onConfigured }) {
  const [step, setStep]           = useState(1)
  const [loading, setLoading]     = useState(false)
  const [testing, setTesting]     = useState(false)
  const [testingSage, setTestingSage] = useState(false)
  const [showPwd, setShowPwd]     = useState(false)
  const [showAdminPwd, setShowAdminPwd] = useState(false)
  const [showSagePwd, setShowSagePwd]   = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [sageTestResult, setSageTestResult] = useState(null)
  const [databases, setDatabases]   = useState([])
  const [loadingDBs, setLoadingDBs] = useState(false)
  const [result, setResult]         = useState(null)

  const [cfg, setCfg] = useState({
    // SQL central
    server:   '',
    port:     '1433',
    database: 'OptiBoard_SaaS',
    username: '',
    password: '',
    app_name: 'OptiBoard',
    // Client (DWH)
    create_first_dwh: true,
    first_dwh_code:   'LOCAL',
    first_dwh_name:   'Mon Entreprise',
    // Admin client
    create_admin_client: true,
    admin_username: 'admin_client',
    admin_password: '',
    admin_email:    '',
    admin_nom:      'Administrateur',
    admin_prenom:   'Client',
    // Source Sage
    create_sage_source: false,
    sage_server:        '',
    sage_database:      '',
    sage_username:      'sa',
    sage_password:      '',
    sage_societe_code:  '',
    sage_societe_nom:   '',
  })

  const set = (k, v) => {
    setCfg(prev => ({ ...prev, [k]: v }))
    if (['server','database','username','password','port'].includes(k)) setTestResult(null)
    if (k.startsWith('sage_')) setSageTestResult(null)
  }

  const fullServer = cfg.port && cfg.port !== '1433'
    ? `${cfg.server},${cfg.port}`
    : cfg.server

  const canStep1 = cfg.server && cfg.database && cfg.username && cfg.password
  const canStep2 = !cfg.create_first_dwh || (cfg.first_dwh_code && cfg.first_dwh_name)
  const canStep3 = !cfg.create_admin_client || (
    cfg.admin_username && cfg.admin_username.length >= 3 &&
    cfg.admin_password && cfg.admin_password.length >= 4
  )
  const canStep4 = !cfg.create_sage_source || (
    cfg.sage_server && cfg.sage_database && cfg.sage_username
  )

  // ── Test connexion SQL central ───────────────────────────────────────────
  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await api.post('/setup/test-connection', {
        server:   fullServer,
        database: cfg.database,
        username: cfg.username,
        password: cfg.password,
      })
      setTestResult(res.data)
    } catch (err) {
      setTestResult({ success: false, error: extractErrorMessage(err, 'Erreur de connexion') })
    } finally {
      setTesting(false)
    }
  }

  // ── Test connexion Sage ──────────────────────────────────────────────────
  const handleTestSage = async () => {
    setTestingSage(true)
    setSageTestResult(null)
    try {
      const res = await api.post('/setup/test-sage-connection', {
        server:   cfg.sage_server,
        database: cfg.sage_database,
        username: cfg.sage_username,
        password: cfg.sage_password,
      })
      setSageTestResult(res.data)
    } catch (err) {
      setSageTestResult({ success: false, error: extractErrorMessage(err, 'Erreur de connexion Sage') })
    } finally {
      setTestingSage(false)
    }
  }

  // ── Charger les bases ────────────────────────────────────────────────────
  const handleLoadDBs = async () => {
    if (!cfg.server || !cfg.username || !cfg.password) return
    setLoadingDBs(true)
    try {
      const res = await api.get('/setup/databases', {
        params: { server: fullServer, username: cfg.username, password: cfg.password }
      })
      if (res.data.success) setDatabases(res.data.databases)
    } catch { /* silent */ } finally {
      setLoadingDBs(false)
    }
  }

  // ── Sauvegarder ──────────────────────────────────────────────────────────
  const handleSave = async () => {
    setLoading(true)
    try {
      const res = await api.post('/setup/configure', {
        server:   fullServer,
        database: cfg.database,
        username: cfg.username,
        password: cfg.password,
        app_name: cfg.app_name,
        // Client (DWH)
        create_first_dwh: cfg.create_first_dwh,
        first_dwh_code:   cfg.create_first_dwh ? cfg.first_dwh_code.toUpperCase() : null,
        first_dwh_name:   cfg.create_first_dwh ? cfg.first_dwh_name : null,
        // Admin client
        create_admin_client: cfg.create_admin_client,
        admin_username: cfg.create_admin_client ? cfg.admin_username : null,
        admin_password: cfg.create_admin_client ? cfg.admin_password : null,
        admin_email:    cfg.create_admin_client ? cfg.admin_email : null,
        admin_nom:      cfg.create_admin_client ? cfg.admin_nom : null,
        admin_prenom:   cfg.create_admin_client ? cfg.admin_prenom : null,
        // Source Sage
        create_sage_source: cfg.create_sage_source,
        sage_server:       cfg.create_sage_source ? cfg.sage_server : null,
        sage_database:     cfg.create_sage_source ? cfg.sage_database : null,
        sage_username:     cfg.create_sage_source ? cfg.sage_username : null,
        sage_password:     cfg.create_sage_source ? cfg.sage_password : null,
        sage_societe_code: cfg.create_sage_source ? (cfg.sage_societe_code || cfg.first_dwh_code).toUpperCase() : null,
        sage_societe_nom:  cfg.create_sage_source ? (cfg.sage_societe_nom || cfg.first_dwh_name) : null,
      })
      if (res.data.success) {
        setResult(res.data)
        setStep(6)
        if (onConfigured) setTimeout(() => onConfigured(), 6000)
      } else {
        setTestResult({ success: false, error: res.data.error || 'Erreur lors de la configuration' })
      }
    } catch (err) {
      setTestResult({ success: false, error: extractErrorMessage(err, 'Erreur lors de la sauvegarde') })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-700 via-blue-800 to-indigo-900 p-4">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-lg">
        {/* Logo + titre */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white/10 backdrop-blur-sm rounded-2xl shadow-xl mb-4 border border-white/20">
            <Settings className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Configuration OptiBoard</h1>
          <p className="text-blue-200 text-sm mt-1">Assistante de configuration initiale</p>
        </div>

        <StepIndicator current={step} />

        {/* Carte principale */}
        <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">

          {/* ── ÉTAPE 1 : Paramètres SQL ────────────────────────────────── */}
          {step === 1 && (
            <div className="p-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
                <Server className="w-5 h-5 text-blue-500" />
                Connexion SQL Server
              </h2>

              <div className="space-y-4">
                {/* Serveur + Port */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <Field label="Serveur" icon={Server}
                      hint="Nom d'hôte, IP ou alias SQL Server">
                      <input
                        value={cfg.server}
                        onChange={e => set('server', e.target.value)}
                        placeholder="localhost ou 192.168.1.10"
                        className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                    </Field>
                  </div>
                  <Field label="Port">
                    <input
                      value={cfg.port}
                      onChange={e => set('port', e.target.value)}
                      placeholder="1433"
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </Field>
                </div>

                <Field label="Utilisateur SQL" icon={User}>
                  <input
                    value={cfg.username}
                    onChange={e => set('username', e.target.value)}
                    placeholder="sa"
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </Field>

                <Field label="Mot de passe" icon={Lock}>
                  <div className="relative">
                    <input
                      type={showPwd ? 'text' : 'password'}
                      value={cfg.password}
                      onChange={e => set('password', e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2.5 pr-10 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                    <button type="button"
                      onClick={() => setShowPwd(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                      {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </Field>

                <Field label="Base de données" icon={Database}
                  hint="Sera créée automatiquement si elle n'existe pas">
                  <div className="flex gap-2">
                    <input
                      value={cfg.database}
                      onChange={e => set('database', e.target.value)}
                      list="db-list"
                      placeholder="OptiBoard_SaaS"
                      className="flex-1 px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleLoadDBs}
                      disabled={!cfg.server || !cfg.username || !cfg.password || loadingDBs}
                      title="Charger les bases disponibles"
                      className="px-3 py-2.5 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors text-gray-500"
                    >
                      {loadingDBs
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <RefreshCw className="w-4 h-4" />}
                    </button>
                    <datalist id="db-list">
                      {databases.map(db => <option key={db} value={db} />)}
                    </datalist>
                  </div>
                </Field>

                <Field label="Nom de l'application">
                  <input
                    value={cfg.app_name}
                    onChange={e => set('app_name', e.target.value)}
                    placeholder="OptiBoard"
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </Field>
              </div>

              <div className="mt-8 flex justify-end">
                <button
                  onClick={() => setStep(2)}
                  disabled={!canStep1}
                  className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium rounded-lg transition-colors text-sm"
                >
                  Suivant <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ── ÉTAPE 2 : Premier client (DWH local) ────────────────────── */}
          {step === 2 && (
            <div className="p-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-blue-500" />
                Premier client
              </h2>
              <p className="text-sm text-gray-500 mb-6">
                Créez automatiquement le premier client (entreprise) dans OptiBoard.
                Sa base de données sera créée sur le même serveur SQL.
              </p>

              <label className="flex items-start gap-3 p-4 mb-5 rounded-xl border border-gray-200 hover:border-blue-300 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={cfg.create_first_dwh}
                  onChange={e => set('create_first_dwh', e.target.checked)}
                  className="mt-0.5 w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">Créer un client par défaut</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Recommandé. Crée la base <code className="bg-gray-100 px-1 rounded">OptiBoard_{(cfg.first_dwh_code || 'CODE').toUpperCase()}</code>.
                  </p>
                </div>
              </label>

              {cfg.create_first_dwh && (
                <div className="space-y-4">
                  <Field label="Code client" icon={Building2}
                    hint="Identifiant court (lettres/chiffres). Ex: LOCAL, ACME, PARIS01">
                    <input
                      value={cfg.first_dwh_code}
                      onChange={e => set('first_dwh_code', e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, ''))}
                      placeholder="LOCAL"
                      maxLength={50}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm font-mono uppercase focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </Field>

                  <Field label="Nom de l'entreprise"
                    hint="Affiché dans l'interface (ex: Société XYZ)">
                    <input
                      value={cfg.first_dwh_name}
                      onChange={e => set('first_dwh_name', e.target.value)}
                      placeholder="Mon Entreprise"
                      maxLength={200}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </Field>

                  <div className="bg-blue-50 border border-blue-100 rounded-xl p-3 text-xs text-blue-700 flex items-start gap-2">
                    <Database className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div>
                      <p>Une nouvelle base sera créée :</p>
                      <p className="font-mono font-medium mt-1">
                        OptiBoard_{(cfg.first_dwh_code || 'CODE').toUpperCase()}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="mt-8 flex justify-between">
                <button onClick={() => setStep(1)}
                  className="flex items-center gap-1.5 px-4 py-2.5 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors text-sm">
                  <ChevronLeft className="w-4 h-4" /> Retour
                </button>
                <button onClick={() => setStep(3)} disabled={!canStep2}
                  className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium rounded-lg transition-colors text-sm">
                  Suivant <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ── ÉTAPE 3 : Admin du client ─────────────────────────────── */}
          {step === 3 && (
            <div className="p-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <UserCog className="w-5 h-5 text-blue-500" />
                Administrateur du client
              </h2>
              <p className="text-sm text-gray-500 mb-6">
                Créez un compte administrateur dédié à ce client.
                Il pourra gérer les utilisateurs, données et paramètres du DWH <code className="bg-gray-100 px-1 rounded">{cfg.first_dwh_code || 'LOCAL'}</code>.
              </p>

              <label className="flex items-start gap-3 p-4 mb-5 rounded-xl border border-gray-200 hover:border-blue-300 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={cfg.create_admin_client}
                  onChange={e => set('create_admin_client', e.target.checked)}
                  className="mt-0.5 w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">Créer un admin client</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Recommandé. Compte avec rôle <code className="bg-gray-100 px-1 rounded">admin</code> lié au DWH.
                  </p>
                </div>
              </label>

              {cfg.create_admin_client && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Nom" icon={User}>
                      <input
                        value={cfg.admin_nom}
                        onChange={e => set('admin_nom', e.target.value)}
                        placeholder="Dupont"
                        className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                    </Field>
                    <Field label="Prénom">
                      <input
                        value={cfg.admin_prenom}
                        onChange={e => set('admin_prenom', e.target.value)}
                        placeholder="Jean"
                        className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                    </Field>
                  </div>

                  <Field label="Identifiant (login)" icon={UserCog}
                    hint="Min. 3 caractères. Servira à se connecter.">
                    <input
                      value={cfg.admin_username}
                      onChange={e => set('admin_username', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                      placeholder="admin_client"
                      maxLength={50}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </Field>

                  <Field label="Email" icon={Mail}>
                    <input
                      type="email"
                      value={cfg.admin_email}
                      onChange={e => set('admin_email', e.target.value)}
                      placeholder="admin@entreprise.com"
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </Field>

                  <Field label="Mot de passe" icon={Lock}
                    hint="Min. 4 caractères. À changer après 1ère connexion.">
                    <div className="relative">
                      <input
                        type={showAdminPwd ? 'text' : 'password'}
                        value={cfg.admin_password}
                        onChange={e => set('admin_password', e.target.value)}
                        placeholder="••••••••"
                        className="w-full px-3 py-2.5 pr-10 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                      <button type="button"
                        onClick={() => setShowAdminPwd(v => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                        {showAdminPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </Field>
                </div>
              )}

              <div className="mt-8 flex justify-between">
                <button onClick={() => setStep(2)}
                  className="flex items-center gap-1.5 px-4 py-2.5 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors text-sm">
                  <ChevronLeft className="w-4 h-4" /> Retour
                </button>
                <button onClick={() => setStep(4)} disabled={!canStep3}
                  className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium rounded-lg transition-colors text-sm">
                  Suivant <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ── ÉTAPE 4 : Source Sage ─────────────────────────────────── */}
          {step === 4 && (
            <div className="p-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-blue-500" />
                Base Sage source
              </h2>
              <p className="text-sm text-gray-500 mb-6">
                Connectez la base Sage du client. Les données (ventes, stocks, clients) seront
                synchronisées dans OptiBoard via l'ETL.
              </p>

              <label className="flex items-start gap-3 p-4 mb-5 rounded-xl border border-gray-200 hover:border-blue-300 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={cfg.create_sage_source}
                  onChange={e => set('create_sage_source', e.target.checked)}
                  className="mt-0.5 w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">Configurer la source Sage maintenant</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Optionnel. Vous pouvez la configurer plus tard depuis l'admin du DWH.
                  </p>
                </div>
              </label>

              {cfg.create_sage_source && (
                <div className="space-y-4">
                  <Field label="Serveur Sage" icon={Server}
                    hint="Peut être le même que SQL central, ou un autre serveur">
                    <input
                      value={cfg.sage_server}
                      onChange={e => set('sage_server', e.target.value)}
                      placeholder="localhost ou 192.168.1.20"
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </Field>

                  <Field label="Base Sage" icon={Database}
                    hint="Nom de la base Sage (ex: BIJOU, COMPTA, SOC01)">
                    <input
                      value={cfg.sage_database}
                      onChange={e => set('sage_database', e.target.value)}
                      placeholder="BIJOU"
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </Field>

                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Utilisateur SQL" icon={User}>
                      <input
                        value={cfg.sage_username}
                        onChange={e => set('sage_username', e.target.value)}
                        placeholder="sa"
                        className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                    </Field>
                    <Field label="Mot de passe" icon={Lock}>
                      <div className="relative">
                        <input
                          type={showSagePwd ? 'text' : 'password'}
                          value={cfg.sage_password}
                          onChange={e => set('sage_password', e.target.value)}
                          placeholder="••••••••"
                          className="w-full px-3 py-2.5 pr-10 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                        />
                        <button type="button"
                          onClick={() => setShowSagePwd(v => !v)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                          {showSagePwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </Field>
                  </div>

                  <div className="bg-amber-50 border border-amber-100 rounded-xl p-3 text-xs text-amber-700 flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <span>Testez la connexion Sage avant de continuer pour valider les identifiants.</span>
                  </div>

                  {/* Test Sage */}
                  <div className="flex justify-end">
                    <button
                      onClick={handleTestSage}
                      disabled={testingSage || !cfg.sage_server || !cfg.sage_database || !cfg.sage_username}
                      className="flex items-center gap-2 px-4 py-2 border border-gray-300 hover:bg-gray-50 disabled:opacity-50 text-gray-700 font-medium rounded-lg transition-colors text-sm"
                    >
                      {testingSage
                        ? <><Loader2 className="w-4 h-4 animate-spin" /> Test...</>
                        : <><Wifi className="w-4 h-4" /> Tester Sage</>}
                    </button>
                  </div>

                  {sageTestResult && (
                    <div className={`p-3 rounded-xl border text-sm
                      ${sageTestResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                      <div className="flex items-start gap-2">
                        {sageTestResult.success
                          ? <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                          : <XCircle    className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />}
                        <div className="flex-1">
                          <p className={`font-medium ${sageTestResult.success ? 'text-green-700' : 'text-red-700'}`}>
                            {sageTestResult.success ? sageTestResult.message : sageTestResult.error}
                          </p>
                          {sageTestResult.success && sageTestResult.is_sage_db && (
                            <p className="text-green-600 mt-1 text-xs">
                              ✓ Base Sage détectée ({sageTestResult.sage_tables_found} tables Sage / {sageTestResult.table_count} tables)
                            </p>
                          )}
                          {sageTestResult.warning && (
                            <p className="text-amber-600 mt-1 text-xs flex items-center gap-1">
                              <AlertCircle className="w-3.5 h-3.5" /> {sageTestResult.warning}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="mt-8 flex justify-between">
                <button onClick={() => setStep(3)}
                  className="flex items-center gap-1.5 px-4 py-2.5 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors text-sm">
                  <ChevronLeft className="w-4 h-4" /> Retour
                </button>
                <button onClick={() => setStep(5)} disabled={!canStep4}
                  className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium rounded-lg transition-colors text-sm">
                  Suivant <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ── ÉTAPE 5 : Test + Confirmation ─────────────────────────── */}
          {step === 5 && (
            <div className="p-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
                <Wifi className="w-5 h-5 text-blue-500" />
                Test &amp; Installation
              </h2>

              {/* Résumé */}
              <div className="bg-gray-50 rounded-xl p-4 mb-6 text-sm space-y-3">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">SQL Central</p>
                  <div className="space-y-1 pl-2">
                    <div className="flex justify-between"><span className="text-gray-500">Serveur</span><span className="font-mono text-gray-800">{fullServer}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">Base</span><span className="font-mono text-gray-800">{cfg.database}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">User</span><span className="font-mono text-gray-800">{cfg.username}</span></div>
                  </div>
                </div>

                {cfg.create_first_dwh && (
                  <div className="border-t border-gray-200 pt-2">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Client DWH</p>
                    <div className="space-y-1 pl-2">
                      <div className="flex justify-between"><span className="text-gray-500">Code</span><span className="font-mono text-gray-800">{cfg.first_dwh_code}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">Nom</span><span className="text-gray-800">{cfg.first_dwh_name}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">Base</span><span className="font-mono text-gray-800">OptiBoard_{cfg.first_dwh_code}</span></div>
                    </div>
                  </div>
                )}

                {cfg.create_admin_client && (
                  <div className="border-t border-gray-200 pt-2">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Admin client</p>
                    <div className="space-y-1 pl-2">
                      <div className="flex justify-between"><span className="text-gray-500">Login</span><span className="font-mono text-gray-800">{cfg.admin_username}</span></div>
                      {cfg.admin_email && <div className="flex justify-between"><span className="text-gray-500">Email</span><span className="text-gray-800">{cfg.admin_email}</span></div>}
                    </div>
                  </div>
                )}

                {cfg.create_sage_source && (
                  <div className="border-t border-gray-200 pt-2">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Source Sage</p>
                    <div className="space-y-1 pl-2">
                      <div className="flex justify-between"><span className="text-gray-500">Serveur</span><span className="font-mono text-gray-800">{cfg.sage_server}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">Base</span><span className="font-mono text-gray-800">{cfg.sage_database}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">User</span><span className="font-mono text-gray-800">{cfg.sage_username}</span></div>
                    </div>
                  </div>
                )}
              </div>

              {/* Résultat test */}
              {testResult && (
                <div className={`mb-5 p-4 rounded-xl border text-sm
                  ${testResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                  <div className="flex items-start gap-2">
                    {testResult.success
                      ? <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                      : <XCircle    className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />}
                    <div className="flex-1">
                      <p className={`font-medium ${testResult.success ? 'text-green-700' : 'text-red-700'}`}>
                        {testResult.success ? testResult.message : testResult.error}
                      </p>
                      {testResult.success && testResult.database_exists === false && (
                        <p className="text-amber-600 mt-1 flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5" />
                          La base sera créée automatiquement
                        </p>
                      )}
                      {testResult.success && testResult.server_info?.table_count !== undefined && (
                        <p className="text-green-600 mt-1">Base existante — {testResult.server_info.table_count} table(s)</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {!testResult && (
                <div className="mb-5 p-3 bg-blue-50 border border-blue-100 rounded-xl text-xs text-blue-600 flex items-start gap-2">
                  <Shield className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>Testez la connexion avant d'installer.</span>
                </div>
              )}

              <div className="flex justify-between items-center">
                <button onClick={() => { setStep(4); setTestResult(null) }}
                  className="flex items-center gap-1.5 px-4 py-2.5 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors text-sm">
                  <ChevronLeft className="w-4 h-4" /> Retour
                </button>

                <div className="flex gap-3">
                  <button onClick={handleTest} disabled={testing}
                    className="flex items-center gap-2 px-5 py-2.5 border border-gray-300 hover:bg-gray-50 disabled:opacity-50 text-gray-700 font-medium rounded-lg transition-colors text-sm">
                    {testing
                      ? <><Loader2 className="w-4 h-4 animate-spin" /> Test...</>
                      : <><Wifi className="w-4 h-4" /> Tester</>}
                  </button>
                  <button onClick={handleSave} disabled={loading || !testResult?.success}
                    className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium rounded-lg transition-colors text-sm">
                    {loading
                      ? <><Loader2 className="w-4 h-4 animate-spin" /> Installation...</>
                      : <><Sparkles className="w-4 h-4" /> Installer</>}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ── ÉTAPE 6 : Succès ──────────────────────────────────────── */}
          {step === 6 && (
            <div className="p-8">
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-2xl mb-4">
                  <CheckCircle className="w-9 h-9 text-green-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">Installation réussie !</h2>
                <p className="text-gray-500 text-sm mt-1">OptiBoard est configuré et prêt à l'emploi.</p>
              </div>

              {/* Premier client cree */}
              {result?.dwh && result.dwh.dwh_inserted && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4 text-sm mb-4">
                  <div className="flex items-center gap-2 text-blue-700 font-medium mb-2">
                    <Building2 className="w-4 h-4" /> Client créé
                  </div>
                  <div className="grid grid-cols-2 gap-y-1 text-xs">
                    <span className="text-gray-500">Code</span><span className="font-mono font-medium text-gray-800">{result.dwh.code}</span>
                    <span className="text-gray-500">Nom</span><span className="font-medium text-gray-800">{result.dwh.nom}</span>
                    <span className="text-gray-500">Base</span><span className="font-mono font-medium text-gray-800">{result.dwh.db_name}</span>
                  </div>
                </div>
              )}

              {/* Admin client cree */}
              {result?.dwh?.admin_client_created && (
                <div className="bg-purple-50 border border-purple-200 rounded-xl px-5 py-4 text-sm mb-4">
                  <div className="flex items-center gap-2 text-purple-700 font-medium mb-2">
                    <UserCog className="w-4 h-4" /> Admin client créé
                  </div>
                  <div className="grid grid-cols-2 gap-y-1 text-xs">
                    <span className="text-gray-500">Login</span>
                    <span className="font-mono font-medium text-gray-800 flex items-center">
                      {result.dwh.admin_client_username}
                      <CopyButton text={result.dwh.admin_client_username} />
                    </span>
                  </div>
                </div>
              )}

              {/* Source Sage */}
              {result?.dwh?.sage_source_inserted && (
                <div className="bg-orange-50 border border-orange-200 rounded-xl px-5 py-4 text-sm mb-4">
                  <div className="flex items-center gap-2 text-orange-700 font-medium mb-2">
                    <Briefcase className="w-4 h-4" /> Source Sage liée
                  </div>
                  <div className="grid grid-cols-2 gap-y-1 text-xs">
                    <span className="text-gray-500">Code société</span>
                    <span className="font-mono font-medium text-gray-800">{result.dwh.sage_societe_code}</span>
                  </div>
                </div>
              )}

              {/* Credentials defaut */}
              <div className="bg-gray-900 rounded-xl p-5 mb-6 text-sm">
                <p className="text-gray-400 text-xs font-medium mb-3 uppercase tracking-wide">Identifiants par défaut</p>
                <div className="space-y-3">
                  {[
                    { role: 'Superadmin', user: 'superadmin', pwd: 'admin' },
                    { role: 'Administrateur', user: 'admin', pwd: 'admin' },
                  ].map(({ role, user, pwd }) => (
                    <div key={user} className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2.5">
                      <div>
                        <span className="text-gray-400 text-xs">{role}</span>
                        <div className="flex items-center gap-1 text-white font-mono mt-0.5">
                          {user}<CopyButton text={user} />
                          <span className="text-gray-500 mx-1">/</span>
                          {pwd}<CopyButton text={pwd} />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="text-amber-400 text-xs mt-3 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Changez ces mots de passe après la première connexion
                </p>
              </div>

              <div className="flex items-center justify-center gap-2 text-gray-400 text-sm">
                <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                Redirection vers la connexion...
              </div>
            </div>
          )}
        </div>

        <p className="text-center text-blue-300/60 text-xs mt-6">
          OptiBoard · KaSoft Maroc · Configuration initiale
        </p>
      </div>
    </div>
  )
}
