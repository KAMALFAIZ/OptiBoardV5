import { useState, useEffect, useCallback } from 'react'
import { Brain, CheckCircle, XCircle, Trash2, Plus, Edit3, Save, X, ThumbsUp, ThumbsDown, RefreshCw, ChevronDown, ChevronUp, Search, Sparkles, Key, Eye, EyeOff, Bot, Zap, Settings2 } from 'lucide-react'
import api from '../services/api'

const PROVIDER_MODELS = {
  openai:    ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: ['claude-opus-4-5', 'claude-sonnet-4-5-20250929', 'claude-haiku-4-5'],
  ollama:    ['llama3.2', 'mistral', 'codellama', 'phi3'],
}

const getUserHeader = () => {
  try {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    return user.id ? { 'X-User-Id': String(user.id) } : {}
  } catch { return {} }
}

export default function AIQueryLibraryPage() {
  const [entries, setEntries] = useState([])
  const [stats, setStats] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({ question_text: '', sql_query: '' })
  const [showAddForm, setShowAddForm] = useState(false)
  const [newEntry, setNewEntry] = useState({ question_text: '', sql_query: '', dwh_code: '' })
  const [filterValidated, setFilterValidated] = useState('all') // 'all' | 'validated' | 'pending'
  const [saving, setSaving] = useState(false)
  const [search, setSearch] = useState('')
  const [seeding, setSeeding] = useState(false)

  // ── Config IA ─────────────────────────────────────────────────────────────
  const [showApiConfig, setShowApiConfig] = useState(false)
  const [aiConfig, setAiConfig] = useState({
    AI_PROVIDER: '', AI_MODEL: '', AI_API_KEY: '',
    AI_OLLAMA_URL: 'http://localhost:11434',
    AI_MAX_TOKENS: 4096, AI_TEMPERATURE: 0.2, AI_ENABLED: true,
    AI_RATE_LIMIT_PER_MINUTE: 20,
  })
  const [aiConfigLoaded, setAiConfigLoaded] = useState(false)
  const [aiSaving, setAiSaving] = useState(false)
  const [aiTesting, setAiTesting] = useState(false)
  const [aiTestResult, setAiTestResult] = useState(null)
  const [showKey, setShowKey] = useState(false)
  const [aiSaved, setAiSaved] = useState(false)
  // ─────────────────────────────────────────────────────────────────────────

  const headers = getUserHeader()

  // ── Fonctions config IA ───────────────────────────────────────────────────
  const loadAiConfig = useCallback(async () => {
    if (aiConfigLoaded) return
    try {
      const res = await api.get('/setup/ai-config')
      if (res.data.success) { setAiConfig(res.data.config); setAiConfigLoaded(true) }
    } catch { /* ignore */ }
  }, [aiConfigLoaded])

  const handleAiSave = async () => {
    setAiSaving(true)
    setAiTestResult(null)
    try {
      await api.post('/setup/ai-config', aiConfig)
      setAiSaved(true)
      setTimeout(() => setAiSaved(false), 3000)
    } catch (e) { alert('Erreur: ' + (e.response?.data?.detail || e.message)) }
    finally { setAiSaving(false) }
  }

  const handleAiTest = async () => {
    setAiTesting(true)
    setAiTestResult(null)
    try {
      await api.post('/setup/ai-config', aiConfig)
      const res = await api.post('/ai/test-provider')
      setAiTestResult(res.data)
    } catch (e) {
      setAiTestResult({ success: false, error: e.response?.data?.detail || e.message })
    } finally { setAiTesting(false) }
  }

  const toggleApiConfig = () => {
    if (!showApiConfig) loadAiConfig()
    setShowApiConfig(v => !v)
    setAiTestResult(null)
  }
  // ─────────────────────────────────────────────────────────────────────────

  const handleSeed = async () => {
    if (!confirm('Initialiser la library avec les 15 exemples de référence ?')) return
    setSeeding(true)
    try {
      const res = await api.post('/ai/learning/seed', {}, { headers })
      await load()
      alert(res.data.message || 'Exemples ajoutés avec succès')
    } catch (e) {
      alert('Erreur: ' + (e.response?.data?.detail || e.message))
    } finally {
      setSeeding(false) }
  }

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.get('/ai/learning/library', { headers })
      setEntries(res.data.entries || [])
      setStats(res.data.stats || {})
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleValidate = async (id, validated) => {
    try {
      await api.put(`/ai/learning/library/${id}`, { validated }, { headers })
      setEntries(prev => prev.map(e => e.id === id ? { ...e, is_validated: validated ? 1 : 0 } : e))
    } catch (e) { alert('Erreur: ' + (e.response?.data?.detail || e.message)) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Supprimer cette entrée ?')) return
    try {
      await api.delete(`/ai/learning/library/${id}`, { headers })
      setEntries(prev => prev.filter(e => e.id !== id))
    } catch (e) { alert('Erreur: ' + (e.response?.data?.detail || e.message)) }
  }

  const startEdit = (entry) => {
    setEditingId(entry.id)
    setEditForm({ question_text: entry.question_text, sql_query: entry.sql_query })
    setExpandedId(entry.id)
  }

  const saveEdit = async (id) => {
    setSaving(true)
    try {
      await api.put(`/ai/learning/library/${id}`, editForm, { headers })
      setEntries(prev => prev.map(e => e.id === id ? { ...e, ...editForm } : e))
      setEditingId(null)
    } catch (e) { alert('Erreur: ' + (e.response?.data?.detail || e.message)) }
    finally { setSaving(false) }
  }

  const handleAdd = async () => {
    if (!newEntry.question_text.trim() || !newEntry.sql_query.trim()) {
      alert('Question et SQL requis')
      return
    }
    setSaving(true)
    try {
      await api.post('/ai/learning/library', newEntry, { headers })
      setShowAddForm(false)
      setNewEntry({ question_text: '', sql_query: '', dwh_code: '' })
      await load()
    } catch (e) { alert('Erreur: ' + (e.response?.data?.detail || e.message)) }
    finally { setSaving(false) }
  }

  const filtered = entries.filter(e => {
    if (filterValidated === 'validated' && e.is_validated !== 1) return false
    if (filterValidated === 'pending' && e.is_validated !== 0) return false
    if (search.trim()) {
      const q = search.toLowerCase()
      return e.question_text.toLowerCase().includes(q) || e.sql_query.toLowerCase().includes(q)
    }
    return true
  })

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
            <Brain className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Query Library IA</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Base de connaissance pour l'agent IA</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
            <RefreshCw className="w-4 h-4" /> Actualiser
          </button>
          <button onClick={handleSeed} disabled={seeding} title="Initialiser avec 15 exemples de référence"
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-amber-500 hover:bg-amber-600 text-white rounded-lg disabled:opacity-50 transition-colors">
            <Sparkles className="w-4 h-4" /> {seeding ? 'Ajout...' : 'Init Exemples'}
          </button>
          <button onClick={() => setShowAddForm(true)} className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors">
            <Plus className="w-4 h-4" /> Ajouter
          </button>
        </div>
      </div>

      {/* ── Configuration API IA ───────────────────────────────────────────── */}
      <div className="mb-5 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <button
          onClick={toggleApiConfig}
          className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800/60 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <Key className="w-4 h-4 text-primary-500" />
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Configuration API IA</span>
            {aiConfig.AI_PROVIDER && aiConfigLoaded && (
              <span className="px-2 py-0.5 text-[10px] font-medium bg-primary-100 dark:bg-primary-900/40 text-primary-600 dark:text-primary-400 rounded-full">
                {aiConfig.AI_PROVIDER} · {aiConfig.AI_MODEL || '—'}
              </span>
            )}
            {aiSaved && <span className="text-[11px] text-green-500 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Sauvegardé</span>}
          </div>
          {showApiConfig ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </button>

        {showApiConfig && (
          <div className="p-4 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-700">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              {/* Enable toggle */}
              <div className="md:col-span-2 flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-primary-500" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Module IA activé</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={!!aiConfig.AI_ENABLED}
                    onChange={e => setAiConfig(p => ({ ...p, AI_ENABLED: e.target.checked }))}
                    className="sr-only peer" />
                  <div className="w-10 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-600" />
                </label>
              </div>

              {/* Provider */}
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Fournisseur</label>
                <select value={aiConfig.AI_PROVIDER}
                  onChange={e => {
                    const p = e.target.value
                    setAiConfig(prev => ({ ...prev, AI_PROVIDER: p, AI_MODEL: PROVIDER_MODELS[p]?.[0] || '' }))
                  }}
                  className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500">
                  <option value="">-- Choisir --</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic (Claude)</option>
                  <option value="ollama">Ollama (local)</option>
                </select>
              </div>

              {/* Model */}
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Modèle</label>
                <select value={aiConfig.AI_MODEL}
                  onChange={e => setAiConfig(p => ({ ...p, AI_MODEL: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500">
                  {(PROVIDER_MODELS[aiConfig.AI_PROVIDER] || []).map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              {/* API Key */}
              {aiConfig.AI_PROVIDER && aiConfig.AI_PROVIDER !== 'ollama' && (
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Clé API</label>
                  <div className="relative">
                    <input
                      type={showKey ? 'text' : 'password'}
                      value={aiConfig.AI_API_KEY}
                      onChange={e => setAiConfig(p => ({ ...p, AI_API_KEY: e.target.value }))}
                      placeholder={aiConfig.AI_API_KEY === '***' ? 'Clé déjà configurée (laisser vide pour garder)' : aiConfig.AI_PROVIDER === 'anthropic' ? 'sk-ant-...' : 'sk-...'}
                      className="w-full px-3 py-2 pr-10 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                    />
                    <button onClick={() => setShowKey(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                      {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  <p className="text-[11px] text-gray-400 mt-1">Stockée de manière sécurisée dans le fichier .env</p>
                </div>
              )}

              {/* Ollama URL */}
              {aiConfig.AI_PROVIDER === 'ollama' && (
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">URL Ollama</label>
                  <input type="text" value={aiConfig.AI_OLLAMA_URL}
                    onChange={e => setAiConfig(p => ({ ...p, AI_OLLAMA_URL: e.target.value }))}
                    className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500" />
                </div>
              )}

              {/* Temperature + Tokens */}
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                  Température ({aiConfig.AI_TEMPERATURE})
                </label>
                <input type="range" min="0" max="1" step="0.05"
                  value={aiConfig.AI_TEMPERATURE}
                  onChange={e => setAiConfig(p => ({ ...p, AI_TEMPERATURE: parseFloat(e.target.value) }))}
                  className="w-full accent-primary-600" />
                <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                  <span>Précis (0)</span><span>Créatif (1)</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Max Tokens</label>
                <select value={aiConfig.AI_MAX_TOKENS}
                  onChange={e => setAiConfig(p => ({ ...p, AI_MAX_TOKENS: parseInt(e.target.value) }))}
                  className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500">
                  <option value={1024}>1 024</option>
                  <option value={2048}>2 048</option>
                  <option value={4096}>4 096</option>
                  <option value={8192}>8 192</option>
                </select>
              </div>
            </div>

            {/* Test result */}
            {aiTestResult && (
              <div className={`mt-3 p-2.5 rounded-lg text-xs flex items-start gap-2
                ${aiTestResult.success ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400' : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'}`}>
                {aiTestResult.success
                  ? <><CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" /> Connexion réussie · {aiTestResult.response}</>
                  : <><XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" /> {aiTestResult.error}</>
                }
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 mt-4">
              <button onClick={handleAiSave} disabled={aiSaving}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50 transition-colors">
                <Save className="w-4 h-4" /> {aiSaving ? 'Sauvegarde...' : 'Sauvegarder'}
              </button>
              <button onClick={handleAiTest} disabled={aiTesting || !aiConfig.AI_PROVIDER}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg disabled:opacity-50 transition-colors">
                <Zap className="w-4 h-4" /> {aiTesting ? 'Test...' : 'Tester connexion'}
              </button>
            </div>
          </div>
        )}
      </div>
      {/* ────────────────────────────────────────────────────────────────────── */}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {[
          { label: 'Total', value: stats.total || 0, color: 'gray' },
          { label: 'Validées', value: stats.validated || 0, color: 'green' },
          { label: 'En attente', value: (stats.total || 0) - (stats.validated || 0), color: 'amber' },
          { label: '👍 Positifs', value: stats.total_positive || 0, color: 'blue' },
          { label: '👎 Négatifs', value: stats.total_negative || 0, color: 'red' },
        ].map(s => (
          <div key={s.label} className="bg-white dark:bg-gray-800 rounded-xl p-3 border border-gray-200 dark:border-gray-700 text-center">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{s.value}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Recherche */}
      <div className="relative mb-3">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher une question ou du SQL..."
          className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
        {search && (
          <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Filtres */}
      <div className="flex gap-2 mb-4">
        {[['all', 'Toutes'], ['validated', 'Validées'], ['pending', 'En attente']].map(([val, label]) => (
          <button key={val} onClick={() => setFilterValidated(val)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors
              ${filterValidated === val ? 'bg-primary-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'}`}>
            {label}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-400 dark:text-gray-500 self-center">{filtered.length} entrée{filtered.length > 1 ? 's' : ''}</span>
      </div>

      {/* Formulaire ajout */}
      {showAddForm && (
        <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
          <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-3">Nouvelle entrée</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Question</label>
              <input value={newEntry.question_text} onChange={e => setNewEntry(p => ({ ...p, question_text: e.target.value }))}
                placeholder="Ex: Quel est le CA du mois en cours ?"
                className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Requête SQL</label>
              <textarea value={newEntry.sql_query} onChange={e => setNewEntry(p => ({ ...p, sql_query: e.target.value }))}
                rows={5} placeholder="SELECT ..."
                className="w-full px-3 py-2 text-xs font-mono border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-900 text-green-300 focus:outline-none focus:ring-2 focus:ring-primary-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Code DWH (optionnel)</label>
              <input value={newEntry.dwh_code} onChange={e => setNewEntry(p => ({ ...p, dwh_code: e.target.value }))}
                placeholder="Ex: QSD"
                className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500" />
            </div>
            <div className="flex gap-2">
              <button onClick={handleAdd} disabled={saving} className="px-4 py-2 text-sm font-medium bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50 transition-colors">
                {saving ? 'Ajout...' : 'Ajouter'}
              </button>
              <button onClick={() => setShowAddForm(false)} className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement...
        </div>
      )}

      {/* Liste */}
      {!loading && (
        <div className="space-y-2">
          {filtered.length === 0 && (
            <div className="text-center py-12 text-gray-400 dark:text-gray-500">
              <Brain className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Aucune entrée dans la query library.</p>
              <p className="text-xs mt-1">Les requêtes validées par 👍 apparaîtront ici.</p>
            </div>
          )}
          {filtered.map(entry => (
            <div key={entry.id} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              {/* Header entrée */}
              <div className="flex items-start gap-3 p-4">
                <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${entry.is_validated ? 'bg-green-500' : 'bg-amber-400'}`} />
                <div className="flex-1 min-w-0">
                  {editingId === entry.id ? (
                    <input value={editForm.question_text} onChange={e => setEditForm(p => ({ ...p, question_text: e.target.value }))}
                      className="w-full px-2 py-1 text-sm border border-primary-300 rounded bg-white dark:bg-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
                  ) : (
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{entry.question_text}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-[11px] text-gray-400">
                      {entry.is_validated ? '✅ Validée' : '⏳ En attente'}
                      {entry.dwh_code && ` · DWH: ${entry.dwh_code}`}
                    </span>
                    <span className="text-[11px] text-gray-400 flex items-center gap-1">
                      <ThumbsUp className="w-3 h-3 text-green-400" /> {entry.feedback_positive}
                      <ThumbsDown className="w-3 h-3 text-red-400 ml-1" /> {entry.feedback_negative}
                      · {entry.success_count} utilisation{entry.success_count > 1 ? 's' : ''}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {editingId === entry.id ? (
                    <>
                      <button onClick={() => saveEdit(entry.id)} disabled={saving} title="Sauvegarder"
                        className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors">
                        <Save className="w-4 h-4" />
                      </button>
                      <button onClick={() => setEditingId(null)} title="Annuler"
                        className="p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                        <X className="w-4 h-4" />
                      </button>
                    </>
                  ) : (
                    <>
                      {!entry.is_validated && (
                        <button onClick={() => handleValidate(entry.id, true)} title="Valider"
                          className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors">
                          <CheckCircle className="w-4 h-4" />
                        </button>
                      )}
                      {entry.is_validated === 1 && (
                        <button onClick={() => handleValidate(entry.id, false)} title="Désactiver"
                          className="p-1.5 text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors">
                          <XCircle className="w-4 h-4" />
                        </button>
                      )}
                      <button onClick={() => startEdit(entry)} title="Modifier"
                        className="p-1.5 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors">
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleDelete(entry.id)} title="Supprimer"
                        className="p-1.5 text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <button onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)} title="Voir SQL"
                        className="p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                        {expandedId === entry.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* SQL expandé */}
              {expandedId === entry.id && (
                <div className="border-t border-gray-100 dark:border-gray-700 px-4 pb-4">
                  {editingId === entry.id ? (
                    <textarea value={editForm.sql_query} onChange={e => setEditForm(p => ({ ...p, sql_query: e.target.value }))}
                      rows={8}
                      className="w-full mt-3 px-3 py-2 text-xs font-mono bg-gray-900 text-green-300 border-0 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary-500" />
                  ) : (
                    <pre className="mt-3 p-3 text-xs font-mono bg-gray-50 dark:bg-gray-900 text-gray-700 dark:text-gray-300 rounded-lg overflow-auto max-h-48 whitespace-pre-wrap">
                      {entry.sql_query}
                    </pre>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
