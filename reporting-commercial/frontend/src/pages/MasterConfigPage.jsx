import { useState, useEffect } from 'react'
import {
  Globe, Key, Save, Wifi, CheckCircle, XCircle, Loader2,
  AlertCircle, Server, Eye, EyeOff, Clock
} from 'lucide-react'
import api, { extractErrorMessage } from '../services/api'

export default function MasterConfigPage() {
  const [loading,    setLoading]    = useState(true)
  const [saving,     setSaving]     = useState(false)
  const [testing,    setTesting]    = useState(false)
  const [showKey,    setShowKey]    = useState(false)
  const [savedMsg,   setSavedMsg]   = useState(null)
  const [testResult, setTestResult] = useState(null)

  const [cfg, setCfg] = useState({
    MASTER_API_URL: '',
    MASTER_API_KEY: '',
    MASTER_TIMEOUT: 30,
  })
  const [enabled, setEnabled] = useState(false)

  // ── Charger la config courante ────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/updates/master/config')
        setCfg({
          MASTER_API_URL: res.data.MASTER_API_URL || '',
          MASTER_API_KEY: res.data.MASTER_API_KEY || '',
          MASTER_TIMEOUT: res.data.MASTER_TIMEOUT || 30,
        })
        setEnabled(!!res.data.enabled)
      } catch (err) {
        console.error('Erreur chargement config master', err)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const set = (k, v) => {
    setCfg(p => ({ ...p, [k]: v }))
    setSavedMsg(null)
  }

  // ── Sauvegarder ──────────────────────────────────────────────────────
  const handleSave = async () => {
    setSaving(true)
    setSavedMsg(null)
    try {
      const res = await api.post('/updates/master/config', cfg)
      setEnabled(!!res.data.enabled)
      setSavedMsg({ success: true, msg: 'Configuration sauvegardée' })
      setTimeout(() => setSavedMsg(null), 4000)
    } catch (err) {
      setSavedMsg({ success: false, msg: extractErrorMessage(err, 'Erreur de sauvegarde') })
    } finally {
      setSaving(false)
    }
  }

  // ── Tester la connexion ──────────────────────────────────────────────
  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await api.post('/updates/master/test', {
        url:     cfg.MASTER_API_URL,
        api_key: cfg.MASTER_API_KEY,
        timeout: 15,
      })
      setTestResult(res.data)
    } catch (err) {
      setTestResult({ success: false, error: extractErrorMessage(err, 'Erreur de test') })
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Globe className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Serveur maître
          </h1>
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${
            enabled
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
          }`}>
            {enabled ? '● Activé' : '○ Désactivé (mode local)'}
          </span>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Configurez la connexion au serveur central KASOFT pour tirer le catalogue
          maître (menus, dashboards, gridviews, pivots) via HTTP. Si l'URL est vide,
          le bouton "Récupérer base maître" utilisera la base centrale locale.
        </p>
      </div>

      {/* Form */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 space-y-5">

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
            <Server className="w-4 h-4 text-gray-400" />
            URL du serveur maître
          </label>
          <input
            type="url"
            value={cfg.MASTER_API_URL}
            onChange={e => set('MASTER_API_URL', e.target.value)}
            placeholder="https://central.kasoft.ma"
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
          <p className="mt-1 text-xs text-gray-400">
            Sans <code>/api</code> à la fin. Laissez vide pour désactiver le mode distant.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
            <Key className="w-4 h-4 text-gray-400" />
            Clé API maître
          </label>
          <div className="relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={cfg.MASTER_API_KEY}
              onChange={e => set('MASTER_API_KEY', e.target.value)}
              placeholder="Clé partagée serveur central <-> client"
              className="w-full px-3 py-2.5 pr-10 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono"
            />
            <button type="button"
              onClick={() => setShowKey(v => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-400">
            Doit correspondre à <code>MASTER_API_KEY</code> dans le <code>.env</code> du serveur central.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-gray-400" />
            Timeout HTTP (secondes)
          </label>
          <input
            type="number"
            min="5"
            max="120"
            value={cfg.MASTER_TIMEOUT}
            onChange={e => set('MASTER_TIMEOUT', parseInt(e.target.value || '30', 10))}
            className="w-32 px-3 py-2.5 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>

        {/* Test result */}
        {testResult && (
          <div className={`p-3 rounded-xl border text-sm
            ${testResult.success ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
                                 : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'}`}>
            <div className="flex items-start gap-2">
              {testResult.success
                ? <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                : <XCircle    className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />}
              <div className="flex-1">
                {testResult.success ? (
                  <>
                    <p className="font-medium text-green-700 dark:text-green-300">
                      Connexion réussie — version {testResult.version}
                    </p>
                    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-600 dark:text-gray-300">
                      {Object.entries(testResult.counts || {}).map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="text-gray-500">{k}</span>
                          <span className="font-mono font-medium">{v}</span>
                        </div>
                      ))}
                    </div>
                    <p className="mt-2 text-xs text-green-700 dark:text-green-300">
                      Total exposé : <strong>{testResult.total}</strong> élément(s)
                    </p>
                  </>
                ) : (
                  <p className="font-medium text-red-700 dark:text-red-300">{testResult.error}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Saved msg */}
        {savedMsg && (
          <div className={`p-3 rounded-xl text-sm flex items-center gap-2
            ${savedMsg.success ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                               : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'}`}>
            {savedMsg.success ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            {savedMsg.msg}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-between pt-2">
          <button
            onClick={handleTest}
            disabled={testing || !cfg.MASTER_API_URL}
            className="flex items-center gap-2 px-4 py-2.5 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 text-gray-700 dark:text-gray-200 font-medium rounded-lg transition-colors text-sm"
          >
            {testing
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Test en cours...</>
              : <><Wifi className="w-4 h-4" /> Tester la connexion</>}
          </button>

          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium rounded-lg transition-colors text-sm"
          >
            {saving
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Sauvegarde...</>
              : <><Save className="w-4 h-4" /> Sauvegarder</>}
          </button>
        </div>
      </div>

      {/* Help */}
      <div className="mt-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-xl p-4 text-xs text-blue-700 dark:text-blue-300">
        <p className="font-semibold mb-1.5">Comment ça marche</p>
        <ul className="space-y-1 list-disc list-inside">
          <li>Le serveur central expose <code>/api/master/menus</code>, <code>/dashboards</code>, <code>/gridviews</code>, <code>/pivots</code>, <code>/datasources</code></li>
          <li>L'auth se fait via le header <code>X-Master-Api-Key</code></li>
          <li>Le bouton "Récupérer base maître" appelle <code>POST /api/updates/pull/builder</code> qui tire depuis cette URL</li>
          <li>Sans configuration, le système utilise la base centrale locale (<code>OptiBoard_SaaS</code>)</li>
        </ul>
      </div>
    </div>
  )
}
