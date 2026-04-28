import { useState, useEffect, useCallback } from 'react'
import {
  Database, Key, Bot, Settings as SettingsIcon, Mail,
  Eye, EyeOff, Save, RefreshCw, CheckCircle2,
  XCircle, AlertTriangle, Loader2, RotateCcw,
  Wifi, WifiOff, ChevronDown, ChevronRight
} from 'lucide-react'
import api from '../services/api'

// ─── Icône par section ───────────────────────────────────────────────────────
const ICONS = {
  database: Database,
  key:      Key,
  bot:      Bot,
  settings: SettingsIcon,
  mail:     Mail,
}

// ─── Composant champ individuel ──────────────────────────────────────────────
function EnvField({ field, value, sensitiveKeys, onChange }) {
  const [showSecret, setShowSecret] = useState(false)
  const isSensitive = sensitiveKeys.includes(field.key)
  const isPassword   = field.type === 'password'

  if (field.type === 'boolean') {
    const checked = String(value).toLowerCase() === 'true'
    return (
      <div className="flex items-center justify-between py-2">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {field.label}
        </label>
        <button
          type="button"
          onClick={() => onChange(field.key, String(!checked))}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors
            ${checked ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'}`}
        >
          <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform
            ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
        </button>
      </div>
    )
  }

  if (field.type === 'select') {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {field.label}
        </label>
        <select
          value={value || ''}
          onChange={e => onChange(field.key, e.target.value)}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                     px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          {(field.options || []).map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </div>
    )
  }

  if (field.type === 'number') {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {field.label}
        </label>
        <input
          type="number"
          value={value || ''}
          min={field.min}
          max={field.max}
          step={field.step || 1}
          onChange={e => onChange(field.key, e.target.value)}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                     px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>
    )
  }

  // text / password
  const inputType = isPassword
    ? (showSecret ? 'text' : 'password')
    : 'text'

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {field.label}
        {isSensitive && (
          <span className="ml-2 text-xs text-amber-500 font-normal">● chiffré</span>
        )}
      </label>
      <div className="relative">
        <input
          type={inputType}
          value={value || ''}
          placeholder={field.placeholder || ''}
          onChange={e => onChange(field.key, e.target.value)}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                     px-3 py-2 pr-10 text-sm font-mono
                     focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowSecret(s => !s)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Composant section ───────────────────────────────────────────────────────
function EnvSection({ section, values, sensitiveKeys, onSave, onChange }) {
  const [open, setOpen]       = useState(true)
  const [saving, setSaving]   = useState(false)
  const [result, setResult]   = useState(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  const Icon = ICONS[section.icon] || SettingsIcon

  const handleSave = async () => {
    setSaving(true)
    setResult(null)
    const updates = {}
    section.fields.forEach(f => {
      if (values[f.key] !== undefined) updates[f.key] = values[f.key]
    })
    try {
      const res = await api.put('/env/config', { updates })
      setResult({ ok: true, msg: res.data.message })
    } catch (e) {
      setResult({ ok: false, msg: e.response?.data?.detail || e.message })
    } finally {
      setSaving(false)
      setTimeout(() => setResult(null), 4000)
    }
  }

  const handleTestDB = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await api.post('/env/test-db', {
        server:   values.DB_SERVER || '',
        database: values.DB_NAME   || '',
        username: values.DB_USER   || '',
        password: values.DB_PASSWORD || '',
        driver:   values.DB_DRIVER || '{ODBC Driver 17 for SQL Server}',
      })
      setTestResult(res.data)
    } catch (e) {
      setTestResult({ success: false, message: e.message })
    } finally {
      setTesting(false)
    }
  }

  const handleTestLicense = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await api.post('/env/test-license-server', {
        url: values.LICENSE_SERVER_URL || '',
      })
      setTestResult(res.data)
    } catch (e) {
      setTestResult({ success: false, message: e.message })
    } finally {
      setTesting(false)
    }
  }

  const [smtpTestEmail, setSmtpTestEmail] = useState('')

  const handleTestSMTP = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      // Le backend lit les credentials depuis .env directement
      const res = await api.post('/env/test-smtp', { test_to: smtpTestEmail.trim() })
      setTestResult(res.data)
    } catch (e) {
      setTestResult({ success: false, message: e.response?.data?.detail || e.message })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <button
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <div className="w-8 h-8 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
          <Icon className="w-4 h-4 text-primary-600 dark:text-primary-400" />
        </div>
        <span className="font-semibold text-gray-900 dark:text-white flex-1">{section.label}</span>
        {open ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-gray-100 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {section.fields.map(field => (
              <EnvField
                key={field.key}
                field={field}
                value={values[field.key] ?? ''}
                sensitiveKeys={sensitiveKeys}
                onChange={onChange}
              />
            ))}
          </div>

          {/* Boutons d'action */}
          <div className="flex flex-wrap items-center gap-2 mt-5">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700
                         disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Enregistrer
            </button>

            {section.id === 'database' && (
              <button
                onClick={handleTestDB}
                disabled={testing}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                           disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wifi className="w-4 h-4" />}
                Tester la connexion
              </button>
            )}

            {section.id === 'license' && (
              <button
                onClick={handleTestLicense}
                disabled={testing}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                           disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wifi className="w-4 h-4" />}
                Tester le serveur
              </button>
            )}

            {section.id === 'smtp' && (
              <>
                <input
                  type="email"
                  value={smtpTestEmail}
                  onChange={e => setSmtpTestEmail(e.target.value)}
                  placeholder="Email de destination (test)"
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm
                             bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                             focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
                />
                <button
                  onClick={handleTestSMTP}
                  disabled={testing}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                             disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
                  Tester l'envoi
                </button>
              </>
            )}

            {/* Résultat sauvegarde */}
            {result && (
              <div className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg
                ${result.ok
                  ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                  : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'}`}>
                {result.ok
                  ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  : <XCircle className="w-4 h-4 flex-shrink-0" />}
                {result.msg}
              </div>
            )}

            {/* Résultat test */}
            {testResult && (
              <div className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg
                ${testResult.success
                  ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                  : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'}`}>
                {testResult.success
                  ? <Wifi className="w-4 h-4 flex-shrink-0" />
                  : <WifiOff className="w-4 h-4 flex-shrink-0" />}
                {testResult.message}
                {testResult.version && <span className="ml-1 text-xs opacity-70">({testResult.version.slice(0, 40)}...)</span>}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Page principale ─────────────────────────────────────────────────────────
export default function EnvManagerPage() {
  const [schema,       setSchema]       = useState([])
  const [values,       setValues]       = useState({})
  const [sensitiveKeys, setSensitiveKeys] = useState([])
  const [loading,      setLoading]      = useState(true)
  const [loadError,    setLoadError]    = useState(null)
  const [restarting,   setRestarting]   = useState(false)
  const [restartMsg,   setRestartMsg]   = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [schemaRes, configRes] = await Promise.all([
        api.get('/env/schema'),
        api.get('/env/config'),
      ])
      setSchema(schemaRes.data.schema || [])
      setValues(configRes.data.values || {})
      setSensitiveKeys(configRes.data.sensitive_keys || [])
    } catch (e) {
      const status = e.response?.status
      if (status === 404) {
        setLoadError('route_not_found')
      } else {
        setLoadError(e.message || 'Erreur inconnue')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleChange = (key, value) => {
    setValues(prev => ({ ...prev, [key]: value }))
  }

  const handleRestart = async () => {
    if (!confirm('Redémarrer le backend ? L\'application sera indisponible ~5 secondes.')) return
    setRestarting(true)
    setRestartMsg(null)
    try {
      await api.post('/env/restart')
      setRestartMsg({ ok: true, text: 'Redémarrage lancé. Reconnexion dans 6 secondes...' })
      setTimeout(() => window.location.reload(), 6000)
    } catch {
      setRestartMsg({ ok: true, text: 'Redémarrage lancé...' })
      setTimeout(() => window.location.reload(), 6000)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12">
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-xl p-6 text-center">
          <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto mb-3" />
          <h2 className="text-lg font-semibold text-amber-800 dark:text-amber-300 mb-2">
            Backend non mis à jour
          </h2>
          <p className="text-sm text-amber-700 dark:text-amber-400 mb-4">
            {loadError === 'route_not_found'
              ? 'La route /api/env/schema est introuvable — le backend tourne encore sur une ancienne version.'
              : `Erreur : ${loadError}`}
          </p>
          <div className="bg-white dark:bg-gray-900 rounded-lg p-4 text-left text-sm font-mono text-gray-700 dark:text-gray-300 mb-5 border border-amber-200 dark:border-amber-700">
            <p className="text-gray-500 dark:text-gray-500 mb-1"># Redémarrer le backend manuellement :</p>
            <p>cd D:\FinAnnee\reporting-commercial\backend</p>
            <p>python run.py</p>
          </div>
          <button
            onClick={load}
            className="flex items-center gap-2 mx-auto px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Réessayer
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Configuration serveur
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Gestion du fichier <code className="text-primary-600 dark:text-primary-400">.env</code> — les modifications nécessitent un redémarrage
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 dark:text-gray-400
                       hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Actualiser
          </button>
          <button
            onClick={handleRestart}
            disabled={restarting}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium
                       bg-orange-500 hover:bg-orange-600 disabled:opacity-50
                       text-white rounded-lg transition-colors"
          >
            {restarting
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <RotateCcw className="w-4 h-4" />}
            Redémarrer le backend
          </button>
        </div>
      </div>

      {/* Bandeau redémarrage */}
      {restartMsg && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-lg mb-5 text-sm font-medium
          ${restartMsg.ok
            ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-700'
            : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-700'}`}>
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {restartMsg.text}
        </div>
      )}

      {/* Avertissement général */}
      <div className="flex items-start gap-3 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-700
                      rounded-xl px-4 py-3 mb-6 text-sm text-amber-700 dark:text-amber-400">
        <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
        <span>
          Les modifications sont écrites immédiatement dans <strong>.env</strong> mais
          ne prennent effet qu'après redémarrage du backend.
          Les valeurs <em>chiffrées</em> (●) ne sont pas affichées en clair — laisser vide pour garder l'existant.
        </span>
      </div>

      {/* Sections */}
      <div className="space-y-4">
        {schema.map(section => (
          <EnvSection
            key={section.id}
            section={section}
            values={values}
            sensitiveKeys={sensitiveKeys}
            onChange={handleChange}
            onSave={() => {}}
          />
        ))}
      </div>
    </div>
  )
}
