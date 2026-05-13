import { useState, useEffect } from 'react'
import {
  MessageCircle, Key, Save, Phone, CheckCircle, XCircle,
  Loader2, AlertCircle, Eye, EyeOff, Send, Users, Clock,
  History, Plus, Trash2, ToggleLeft, ToggleRight, Globe,
  Shield
} from 'lucide-react'
import api, { extractErrorMessage } from '../services/api'

export default function WhatsAppConfigPage() {
  const [tab, setTab] = useState('config')

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 bg-green-100 dark:bg-green-900/30 rounded-xl">
            <MessageCircle className="w-7 h-7 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              WhatsApp Business
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Chatbot WhatsApp via Meta Cloud API
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
        {[
          { id: 'config', label: 'Configuration', icon: Key },
          { id: 'mappings', label: 'Utilisateurs', icon: Users },
          { id: 'history', label: 'Historique', icon: History },
          { id: 'send', label: 'Envoi Manuel', icon: Send },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t.id
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'config' && <ConfigTab />}
      {tab === 'mappings' && <MappingsTab />}
      {tab === 'history' && <HistoryTab />}
      {tab === 'send' && <SendTab />}
    </div>
  )
}


// ─── Config Tab ──────────────────────────────────────────────────────────────

function ConfigTab() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [savedMsg, setSavedMsg] = useState(null)
  const [testResult, setTestResult] = useState(null)
  const [showApiKey, setShowApiKey] = useState(false)
  const [showToken, setShowToken] = useState(false)
  const [showSecret, setShowSecret] = useState(false)

  const [cfg, setCfg] = useState({
    provider: '360dialog',
    // 360dialog
    api_key_360dialog: '',
    // Meta direct
    phone_number_id: '',
    access_token: '',
    api_version: 'v21.0',
    // commun
    verify_token: '',
    app_secret: '',
    bot_enabled: false,
  })

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/whatsapp/config')
        if (res.data.success) setCfg(res.data.data)
      } catch (err) {
        console.error('WhatsApp config load error:', err)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const set = (k, v) => {
    setCfg(p => ({ ...p, [k]: v }))
    setSavedMsg(null)
  }

  const handleSave = async () => {
    setSaving(true)
    setSavedMsg(null)
    try {
      await api.post('/whatsapp/config', cfg)
      setSavedMsg({ success: true, msg: 'Configuration WhatsApp sauvegardée' })
      setTimeout(() => setSavedMsg(null), 4000)
    } catch (err) {
      setSavedMsg({ success: false, msg: extractErrorMessage(err, 'Erreur de sauvegarde') })
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await api.post('/whatsapp/test')
      setTestResult(res.data)
    } catch (err) {
      setTestResult({ success: false, error: extractErrorMessage(err, 'Échec du test') })
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-green-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Status Card */}
      <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${
        cfg.bot_enabled
          ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
          : 'bg-gray-50 border-gray-200 dark:bg-gray-800 dark:border-gray-700'
      }`}>
        {cfg.bot_enabled
          ? <ToggleRight className="w-6 h-6 text-green-600 dark:text-green-400" />
          : <ToggleLeft className="w-6 h-6 text-gray-400" />}
        <div>
          <span className={`font-medium text-sm ${cfg.bot_enabled ? 'text-green-700 dark:text-green-300' : 'text-gray-600 dark:text-gray-400'}`}>
            {cfg.bot_enabled ? 'Chatbot activé' : 'Chatbot désactivé'}
          </span>
          <p className="text-xs text-gray-500 dark:text-gray-500">
            Webhook : <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">{window.location.origin}/api/whatsapp/webhook</code>
          </p>
        </div>
        <button
          onClick={() => set('bot_enabled', !cfg.bot_enabled)}
          className={`ml-auto px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            cfg.bot_enabled
              ? 'bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400'
              : 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400'
          }`}
        >
          {cfg.bot_enabled ? 'Désactiver' : 'Activer'}
        </button>
      </div>

      {/* Form */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 space-y-5">

        {/* Provider selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Provider</label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { id: '360dialog', label: '360dialog', badge: 'Recommandé', desc: 'BSP officiel — 1 seule clé API' },
              { id: 'meta', label: 'Meta Cloud API', badge: 'Direct', desc: 'Phone ID + Access Token' },
            ].map(p => (
              <button key={p.id} onClick={() => set('provider', p.id)}
                className={`p-3 rounded-xl border-2 text-left transition-all ${
                  cfg.provider === p.id
                    ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                }`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm text-gray-900 dark:text-white">{p.label}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                    p.id === '360dialog' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400'
                  }`}>{p.badge}</span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">{p.desc}</p>
              </button>
            ))}
          </div>
        </div>

        <hr className="border-gray-100 dark:border-gray-700" />

        {/* ── 360dialog fields ── */}
        {cfg.provider === '360dialog' && (<>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              <div className="flex items-center gap-1.5"><Key className="w-4 h-4 text-gray-400" />API Key 360dialog</div>
            </label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={cfg.api_key_360dialog}
                onChange={e => set('api_key_360dialog', e.target.value)}
                placeholder="Clé API depuis app.360dialog.com → Accounts → API Key"
                className="w-full px-3 py-2.5 pr-10 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none font-mono"
              />
              <button type="button" onClick={() => setShowApiKey(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              360dialog Hub → <strong>Accounts</strong> → votre numéro → <strong>API Key</strong>
            </p>
          </div>
        </>)}

        {/* ── Meta direct fields ── */}
        {cfg.provider === 'meta' && (<>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              <div className="flex items-center gap-1.5"><Phone className="w-4 h-4 text-gray-400" />Phone Number ID</div>
            </label>
            <input type="text" value={cfg.phone_number_id}
              onChange={e => set('phone_number_id', e.target.value)}
              placeholder="Ex: 123456789012345"
              className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none font-mono"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              <div className="flex items-center gap-1.5"><Key className="w-4 h-4 text-gray-400" />Access Token</div>
            </label>
            <div className="relative">
              <input type={showToken ? 'text' : 'password'} value={cfg.access_token}
                onChange={e => set('access_token', e.target.value)}
                placeholder="EAAxxxxxxx..."
                className="w-full px-3 py-2.5 pr-10 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none font-mono"
              />
              <button type="button" onClick={() => setShowToken(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              <div className="flex items-center gap-1.5"><Globe className="w-4 h-4 text-gray-400" />Version API Graph</div>
            </label>
            <select value={cfg.api_version} onChange={e => set('api_version', e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none">
              <option value="v21.0">v21.0 (recommandé)</option>
              <option value="v20.0">v20.0</option>
              <option value="v19.0">v19.0</option>
            </select>
          </div>
        </>)}

        {/* Webhook (commun aux deux providers) */}
        <hr className="border-gray-100 dark:border-gray-700" />
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
            <div className="flex items-center gap-1.5"><Shield className="w-4 h-4 text-gray-400" />Verify Token (webhook)</div>
          </label>
          <input type="text" value={cfg.verify_token}
            onChange={e => set('verify_token', e.target.value)}
            placeholder="Mot de passe webhook que vous choisissez librement"
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none"
          />
          <p className="text-xs text-gray-400 mt-1">
            {cfg.provider === '360dialog'
              ? 'À entrer dans 360dialog Hub → Webhooks → Verify Token'
              : 'À entrer dans Meta Developer → Webhooks → Verify Token'}
          </p>
        </div>

        {/* Test Result */}
        {testResult && (
          <div className={`p-3 rounded-xl border text-sm ${
            testResult.success
              ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
              : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
          }`}>
            <div className="flex items-start gap-2">
              {testResult.success
                ? <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                : <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />}
              <div>
                {testResult.success ? (
                  <>
                    <p className="text-green-700 dark:text-green-300 font-medium">Connexion réussie</p>
                    <p className="text-green-600 dark:text-green-400 text-xs mt-1">
                      Numéro : {testResult.phone_number} — Nom : {testResult.verified_name} — Qualité : {testResult.quality_rating}
                    </p>
                  </>
                ) : (
                  <p className="text-red-700 dark:text-red-300">{testResult.error}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Saved Message */}
        {savedMsg && (
          <div className={`p-3 rounded-xl text-sm flex items-center gap-2 ${
            savedMsg.success
              ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
              : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
          }`}>
            {savedMsg.success ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            {savedMsg.msg}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-between pt-2">
          <button onClick={handleTest}
            disabled={testing || (cfg.provider === '360dialog' ? !cfg.api_key_360dialog : !cfg.phone_number_id)}
            className="flex items-center gap-2 px-4 py-2.5 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 text-gray-700 dark:text-gray-200 font-medium rounded-lg transition-colors text-sm">
            {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Phone className="w-4 h-4" />}
            {testing ? 'Test en cours...' : 'Tester la connexion'}
          </button>
          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white font-medium rounded-lg transition-colors text-sm">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Sauvegarde...' : 'Sauvegarder'}
          </button>
        </div>
      </div>

      {/* Setup Guide */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-3">Guide de configuration</h3>
        <ol className="text-xs text-blue-700 dark:text-blue-400 space-y-2 list-decimal list-inside">
          <li>Créer un compte <strong>Meta Business</strong> sur business.facebook.com</li>
          <li>Créer une <strong>App Meta Developer</strong> (type Business) sur developers.facebook.com</li>
          <li>Ajouter le produit <strong>WhatsApp</strong> à l'app</li>
          <li>Copier le <strong>Phone Number ID</strong> et le <strong>Access Token</strong> permanent</li>
          <li>Configurer le <strong>Webhook</strong> avec l'URL ci-dessus et le Verify Token choisi</li>
          <li>S'abonner aux événements <strong>messages</strong> dans le webhook</li>
        </ol>
      </div>
    </div>
  )
}


// ─── Mappings Tab ────────────────────────────────────────────────────────────

function MappingsTab() {
  const [mappings, setMappings] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ phone_number: '', dwh_code: '', label: '' })
  const [saving, setSaving] = useState(false)

  const loadMappings = async () => {
    try {
      const res = await api.get('/whatsapp/mappings')
      if (res.data.success) setMappings(res.data.data || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadMappings() }, [])

  const handleAdd = async () => {
    if (!form.phone_number || !form.dwh_code) return
    setSaving(true)
    try {
      await api.post('/whatsapp/mappings', form)
      setForm({ phone_number: '', dwh_code: '', label: '' })
      await loadMappings()
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (phone) => {
    try {
      await api.delete(`/whatsapp/mappings/${encodeURIComponent(phone)}`)
      await loadMappings()
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-green-500" /></div>
  }

  return (
    <div className="space-y-6">
      {/* Add form */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Associer un numéro WhatsApp</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input
            type="text" placeholder="Numéro (ex: 212612345678)"
            value={form.phone_number} onChange={e => setForm(p => ({...p, phone_number: e.target.value}))}
            className="px-3 py-2.5 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none"
          />
          <input
            type="text" placeholder="Code DWH (ex: SG)"
            value={form.dwh_code} onChange={e => setForm(p => ({...p, dwh_code: e.target.value.toUpperCase()}))}
            className="px-3 py-2.5 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none"
          />
          <input
            type="text" placeholder="Nom (optionnel)"
            value={form.label} onChange={e => setForm(p => ({...p, label: e.target.value}))}
            className="px-3 py-2.5 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none"
          />
          <button onClick={handleAdd} disabled={saving || !form.phone_number || !form.dwh_code}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-medium rounded-lg text-sm transition-colors">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Ajouter
          </button>
        </div>
      </div>

      {/* List */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Numéro</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">DWH</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Nom</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Date</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {mappings.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Aucun mapping configuré</td></tr>
            ) : mappings.map((m, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-4 py-3 font-mono text-gray-900 dark:text-white">{m.phone_number}</td>
                <td className="px-4 py-3"><span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-xs font-medium">{m.dwh_code}</span></td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{m.label || '—'}</td>
                <td className="px-4 py-3 text-gray-500 dark:text-gray-500 text-xs">{m.created_at ? new Date(m.created_at).toLocaleDateString('fr') : ''}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => handleDelete(m.phone_number)}
                    className="text-red-400 hover:text-red-600 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}


// ─── History Tab ─────────────────────────────────────────────────────────────

function HistoryTab() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/whatsapp/history?limit=100')
        if (res.data.success) setMessages(res.data.data || [])
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-green-500" /></div>
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="max-h-[600px] overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700">
        {messages.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-400">Aucun message</div>
        ) : messages.map((m, i) => (
          <div key={i} className={`px-4 py-3 flex items-start gap-3 ${
            m.direction === 'in' ? 'bg-white dark:bg-gray-800' : 'bg-green-50/50 dark:bg-green-900/10'
          }`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
              m.direction === 'in'
                ? 'bg-blue-100 dark:bg-blue-900/30'
                : 'bg-green-100 dark:bg-green-900/30'
            }`}>
              {m.direction === 'in'
                ? <Phone className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                : <Send className="w-4 h-4 text-green-600 dark:text-green-400" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  {m.contact_name || m.phone_number}
                </span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                  m.direction === 'in'
                    ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                    : 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400'
                }`}>
                  {m.direction === 'in' ? 'Reçu' : 'Envoyé'}
                </span>
                {m.dwh_code && (
                  <span className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-500 rounded">{m.dwh_code}</span>
                )}
                <span className="text-xs text-gray-400 ml-auto">{m.created_at ? new Date(m.created_at).toLocaleString('fr') : ''}</span>
              </div>
              <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words">{m.body}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}


// ─── Send Tab ────────────────────────────────────────────────────────────────

function SendTab() {
  const [to, setTo] = useState('')
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState(null)

  const handleSend = async () => {
    if (!to || !message) return
    setSending(true)
    setResult(null)
    try {
      const res = await api.post('/whatsapp/send', { to, message })
      setResult(res.data)
      if (res.data.success) setMessage('')
    } catch (err) {
      setResult({ success: false, error: extractErrorMessage(err, 'Erreur d\'envoi') })
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 space-y-5">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Envoi manuel de message</h3>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Numéro destinataire</label>
        <input
          type="text" placeholder="212612345678 (sans + ni espaces)"
          value={to} onChange={e => setTo(e.target.value)}
          className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none font-mono"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Message</label>
        <textarea
          rows={5} placeholder="Tapez votre message..."
          value={message} onChange={e => setMessage(e.target.value)}
          className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-600 dark:bg-gray-900 dark:text-white rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none resize-none"
        />
        <p className="text-xs text-gray-400 mt-1">Utilisez *gras* et _italique_ pour le formatage WhatsApp</p>
      </div>

      {result && (
        <div className={`p-3 rounded-xl text-sm flex items-center gap-2 ${
          result.success
            ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
            : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
        }`}>
          {result.success ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {result.success ? `Message envoyé (ID: ${result.message_id})` : result.error}
        </div>
      )}

      <button onClick={handleSend} disabled={sending || !to || !message}
        className="flex items-center gap-2 px-5 py-2.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-medium rounded-lg transition-colors text-sm">
        {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        {sending ? 'Envoi en cours...' : 'Envoyer'}
      </button>
    </div>
  )
}
