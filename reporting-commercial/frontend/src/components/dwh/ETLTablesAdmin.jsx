/**
 * ETLTablesAdmin — Vue Centrale
 * ==============================
 * Accessible uniquement au superadmin (central KASOFT).
 * Permet de :
 *   - Créer / modifier / supprimer des tables ETL
 *   - Publier vers tous les clients ou ciblés
 *   - Valider ou rejeter les propositions des clients
 */
import { useState, useEffect, useMemo } from 'react'
import {
  Database, Plus, RefreshCw, Send, CheckCircle, XCircle,
  Clock, Edit2, Trash2, ChevronDown, ChevronUp, AlertTriangle, Users, Search, X, Info, Maximize2, Minimize2
} from 'lucide-react'
import api from '../../services/api'

const STATUT_BADGE = {
  en_attente: { color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400', icon: Clock,       label: 'En attente' },
  validee:    { color: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400',     icon: CheckCircle, label: 'Validée'    },
  rejetee:    { color: 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400',             icon: XCircle,     label: 'Rejetée'    },
}

const EMPTY_FORM = {
  code: '', table_name: '', target_table: '', source_query: '',
  primary_key_columns: '', sync_type: 'incremental',
  timestamp_column: 'cbModification', interval_minutes: 5,
  priority: 'normal', delete_detection: false, description: ''
}

export default function ETLTablesAdmin() {
  const [tables, setTables]       = useState([])
  const [proposals, setProposals] = useState([])
  const [loading, setLoading]     = useState(true)
  const [activeTab, setActiveTab]   = useState('tables')
  const [searchTerm, setSearchTerm] = useState('')
  const [publishing, setPublishing] = useState(false)
  const [showForm, setShowForm]   = useState(false)
  const [editingCode, setEditingCode] = useState(null)
  const [sqlFullscreen, setSqlFullscreen] = useState(false)
  const [form, setForm]           = useState(EMPTY_FORM)
  const [saving, setSaving]       = useState(false)
  const [validating, setValidating] = useState(null)
  const [error, setError]         = useState(null)
  const [success, setSuccess]     = useState(null)
  const [expandedProposal, setExpandedProposal] = useState(null)
  const [selected, setSelected]   = useState(new Set())   // codes sélectionnés

  const load = async () => {
    setLoading(true); setError(null)
    try {
      const [tablesRes, propsRes] = await Promise.all([
        api.get('/etl-tables/central'),
        api.get('/etl-tables/proposals/central').catch(() => ({ data: { data: [] } }))
      ])
      setTables(tablesRes.data?.data || [])
      setProposals(propsRes.data?.data || [])
    } catch { setError('Erreur de chargement') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handlePublish = async (codes = null) => {
    setPublishing(true); setError(null); setSuccess(null)
    try {
      const body = codes ? { codes } : {}
      const res = await api.post('/etl-tables/central/publish', body)
      const r = res.data?.results || {}
      const label = codes ? `${codes.length} table(s) sélectionnée(s)` : 'toutes les tables'
      setSuccess(`Publication terminée (${label}) — ${r.published || 0} nouvelles, ${r.updated || 0} mises à jour, ${r.failed || 0} erreurs`)
      if (codes) setSelected(new Set())
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur publication')
    } finally { setPublishing(false) }
  }

  const toggleSelect = (code) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(code) ? next.delete(code) : next.add(code)
      return next
    })
  }

  const toggleSelectAll = () => {
    setSelected(prev =>
      prev.size === tables.length ? new Set() : new Set(tables.map(t => t.code))
    )
  }

  // Vérifie si un nom de colonne (avec ou sans crochets) apparaît dans la requête SQL
  const colInQuery = (colName, query) => {
    if (!colName || !query) return true  // pas de requête = pas de validation
    const stripped = colName.replace(/^\[|\]$/g, '').trim().toLowerCase()
    return stripped ? query.toLowerCase().includes(stripped) : true
  }

  const sqlWarnings = useMemo(() => {
    if (!form.source_query) return []
    const warnings = []
    const pks = form.primary_key_columns
      ? form.primary_key_columns.split(',').map(s => s.trim()).filter(Boolean)
      : []
    pks.forEach(pk => {
      if (!colInQuery(pk, form.source_query))
        warnings.push(`Clé primaire "${pk}" absente de la requête SQL`)
    })
    if (form.timestamp_column && !colInQuery(form.timestamp_column, form.source_query))
      warnings.push(`Colonne timestamp "${form.timestamp_column}" absente de la requête SQL`)
    return warnings
  }, [form.primary_key_columns, form.timestamp_column, form.source_query])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true); setError(null)
    try {
      const payload = {
        ...form,
        primary_key_columns: form.primary_key_columns
          ? form.primary_key_columns.split(',').map(s => s.trim()).filter(Boolean)
          : [],
        interval_minutes: Number(form.interval_minutes),
      }
      if (editingCode) {
        await api.put(`/etl-tables/central/${editingCode}`, payload)
        setSuccess(`Table '${editingCode}' mise à jour`)
      } else {
        await api.post('/etl-tables/central', payload)
        setSuccess(`Table '${form.code}' créée`)
      }
      setShowForm(false); setEditingCode(null); setForm(EMPTY_FORM)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur sauvegarde')
    } finally { setSaving(false) }
  }

  // Nettoie un nom de colonne PK : supprime crochets SQL et guillemets
  // Ex: "[N° interne]" → "N° interne"  |  "cbMarq" → "cbMarq"
  const cleanPkName = (pk) => pk.trim().replace(/^\[/, '').replace(/\]$/, '').replace(/^"/, '').replace(/"$/, '').replace(/^\[/, '').replace(/\]$/, '').trim()

  // Convertit primary_key_columns (JSON array ou string) en chaine CSV lisible
  const parsePkColumns = (raw) => {
    if (!raw) return ''
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed.map(cleanPkName).join(', ')
    } catch {}
    // Déjà une string CSV simple
    return String(raw).split(',').map(cleanPkName).join(', ')
  }

  const handleEdit = (table) => {
    setForm({
      code: table.code, table_name: table.table_name, target_table: table.target_table,
      source_query: table.source_query || '', description: table.description || '',
      primary_key_columns: parsePkColumns(table.primary_key_columns),
      sync_type: table.sync_type || 'incremental',
      timestamp_column: table.timestamp_column || 'cbModification',
      interval_minutes: table.interval_minutes || 5,
      priority: table.priority || 'normal',
      delete_detection: !!table.delete_detection,
    })
    setEditingCode(table.code)
    setShowForm(true)
  }

  const handleDelete = async (code) => {
    if (!window.confirm(`Supprimer la table '${code}' ?`)) return
    try {
      await api.delete(`/etl-tables/central/${code}`)
      setSuccess(`Table '${code}' supprimée`)
      load()
    } catch (e) { setError(e.response?.data?.detail || 'Erreur suppression') }
  }

  const handleValidate = async (proposal, statut) => {
    const commentaire = statut === 'rejetee'
      ? window.prompt('Motif du rejet (optionnel) :') ?? ''
      : ''
    setValidating(proposal.id)
    try {
      await api.post(`/etl-tables/proposals/central/${proposal.id}/validate`, {
        statut,
        commentaire,
        publier_si_valide: statut === 'validee'
      })
      setSuccess(statut === 'validee' ? 'Proposition validée et table publiée' : 'Proposition rejetée')
      load()
    } catch (e) { setError(e.response?.data?.detail || 'Erreur validation') }
    finally { setValidating(null) }
  }

  const pendingCount = proposals.filter(p => p.statut === 'en_attente').length

  const filteredTables = useMemo(() => {
    if (!searchTerm.trim()) return tables
    const q = searchTerm.toLowerCase()
    return tables.filter(t =>
      t.code?.toLowerCase().includes(q) ||
      t.table_name?.toLowerCase().includes(q) ||
      t.target_table?.toLowerCase().includes(q) ||
      t.description?.toLowerCase().includes(q)
    )
  }, [tables, searchTerm])

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white">Gestion Tables ETL</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Créez et publiez les tables ETL vers les clients</p>
        </div>
        <div className="flex items-center gap-2">
          {selected.size > 0 ? (
            <button onClick={() => handlePublish([...selected])} disabled={publishing}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors">
              <Send className="w-4 h-4" />
              {publishing ? 'Publication...' : `Publier sélection (${selected.size})`}
            </button>
          ) : (
            <button onClick={() => handlePublish()} disabled={publishing || loading}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors">
              <Send className="w-4 h-4" />
              {publishing ? 'Publication...' : 'Publier tout'}
            </button>
          )}
          <button onClick={() => { setShowForm(true); setEditingCode(null); setForm(EMPTY_FORM) }}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors">
            <Plus className="w-4 h-4" /> Nouvelle table
          </button>
          <button onClick={load} className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 rounded-lg text-sm text-red-700 dark:text-red-400">
          <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">✕</button>
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 rounded-lg text-sm text-green-700 dark:text-green-400">
          <CheckCircle className="w-4 h-4 shrink-0" /> {success}
          <button onClick={() => setSuccess(null)} className="ml-auto text-green-400 hover:text-green-600">✕</button>
        </div>
      )}

      {/* Formulaire création/édition — Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => { setShowForm(false); setEditingCode(null) }} />
          <form onSubmit={handleSave}
            className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-6xl mx-4 flex flex-col"
            style={{ height: '90vh' }}>

            {/* ── HEADER (fixe) ── */}
            <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h4 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Database className="w-4 h-4 text-blue-500" />
                {editingCode ? `Modifier '${editingCode}'` : 'Nouvelle table ETL'}
              </h4>
              <button type="button" onClick={() => { setShowForm(false); setEditingCode(null) }}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* ── BODY ── */}
            <div style={{ display: 'flex', overflow: 'hidden', flex: 1 }}>

              {/* Panneau gauche : champs */}
              <div className="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 p-5 overflow-y-auto space-y-3">
                {!editingCode && (
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Code unique *</label>
                    <input value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                      placeholder="ex: SAGE_ARTICLES" required
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none" />
                  </div>
                )}
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Table source (Sage) *</label>
                  <input value={form.table_name} onChange={e => setForm(f => ({ ...f, table_name: e.target.value }))}
                    placeholder="ex: F_ARTICLE" required
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Table cible (DWH) *</label>
                  <input value={form.target_table} onChange={e => setForm(f => ({ ...f, target_table: e.target.value }))}
                    placeholder="ex: Articles" required
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Clés primaires (virgule)</label>
                  <input value={form.primary_key_columns} onChange={e => setForm(f => ({ ...f, primary_key_columns: e.target.value }))}
                    placeholder="cbMarq, cbNum"
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Colonne timestamp</label>
                  <input value={form.timestamp_column} onChange={e => setForm(f => ({ ...f, timestamp_column: e.target.value }))}
                    placeholder="cbModification"
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Type sync</label>
                  <select value={form.sync_type} onChange={e => setForm(f => ({ ...f, sync_type: e.target.value }))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none">
                    <option value="incremental">Incremental</option>
                    <option value="full">Full</option>
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Intervalle (min)</label>
                    <input type="number" min="1" value={form.interval_minutes} onChange={e => setForm(f => ({ ...f, interval_minutes: e.target.value }))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Priorité</label>
                    <select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none">
                      <option value="high">Haute</option>
                      <option value="normal">Normale</option>
                      <option value="low">Basse</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                  <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                    placeholder="Description de la table"
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
              </div>

              {/* Panneau droit : SQL */}
              <div style={{ flex: 1, minWidth: 0, padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">Requête SQL source</label>
                  <button type="button" onClick={() => setSqlFullscreen(true)}
                    className="flex items-center gap-1 px-2 py-1 text-xs text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors">
                    <Maximize2 className="w-3.5 h-3.5" />
                    Plein écran
                  </button>
                </div>
                <textarea value={form.source_query} onChange={e => setForm(f => ({ ...f, source_query: e.target.value }))}
                  placeholder="SELECT * FROM F_ARTICLE WHERE ..."
                  style={{ width: '100%', height: 'calc(90vh - 175px)', resize: 'none', boxSizing: 'border-box' }}
                  className={`textarea-expand px-4 py-3 text-sm font-mono border rounded-xl bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 outline-none ${
                    sqlWarnings.length > 0
                      ? 'border-amber-400 dark:border-amber-500 focus:ring-amber-400'
                      : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500'
                  }`} />
              </div>

              {/* Overlay SQL plein écran */}
              {sqlFullscreen && (
                <div style={{ position: 'fixed', inset: 0, zIndex: 100, display: 'flex', flexDirection: 'column', background: 'var(--color-bg, #fff)' }}
                  className="bg-white dark:bg-gray-900">
                  <div className="flex-shrink-0 flex items-center justify-between px-6 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                    <span className="text-sm font-semibold text-gray-800 dark:text-white flex items-center gap-2">
                      <Database className="w-4 h-4 text-blue-500" />
                      Requête SQL — {editingCode || 'Nouvelle table'}
                    </span>
                    <button type="button" onClick={() => setSqlFullscreen(false)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                      <Minimize2 className="w-4 h-4" />
                      Réduire
                    </button>
                  </div>
                  <textarea value={form.source_query} onChange={e => setForm(f => ({ ...f, source_query: e.target.value }))}
                    placeholder="SELECT * FROM F_ARTICLE WHERE ..."
                    autoFocus
                    style={{ flex: 1, width: '100%', resize: 'none', boxSizing: 'border-box', padding: '1.5rem', fontSize: '0.875rem', fontFamily: 'monospace', outline: 'none', border: 'none' }}
                    className="textarea-expand bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white" />
                </div>
              )}
            </div>

            {/* ── FOOTER (fixe) ── */}
            <div className="flex-shrink-0 px-6 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between gap-3">
              <div className="flex-1 space-y-1">
                {sqlWarnings.length > 0 && sqlWarnings.map((w, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded px-2 py-1">
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />{w}
                  </div>
                ))}
                {form.source_query && sqlWarnings.length === 0 && (form.primary_key_columns || form.timestamp_column) && (
                  <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" />Clés primaires et colonne timestamp détectées dans la requête.
                  </p>
                )}
              </div>
              <div className="flex gap-3 flex-shrink-0">
                <button type="button" onClick={() => { setShowForm(false); setEditingCode(null) }}
                  className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg">
                  Annuler
                </button>
                <button type="submit" disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg">
                  {saving ? 'Sauvegarde...' : editingCode ? 'Mettre à jour' : 'Créer'}
                </button>
              </div>
            </div>

          </form>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700">
        {[
          { id: 'tables',    label: searchTerm ? `Tables (${filteredTables.length}/${tables.length})` : `Tables (${tables.length})` },
          { id: 'proposals', label: `Propositions${pendingCount > 0 ? ` (${pendingCount} en attente)` : ` (${proposals.length})`}`, alert: pendingCount > 0 },
        ].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors relative ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}>
            {tab.label}
            {tab.alert && <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full" />}
          </button>
        ))}
      </div>

      {/* Tables ETL */}
      {activeTab === 'tables' && (
        loading ? (
          <div className="flex items-center justify-center py-16 text-gray-500">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement...
          </div>
        ) : tables.length === 0 ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <Database className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">Aucune table configurée</p>
            <button onClick={() => setShowForm(true)} className="mt-2 text-sm text-blue-600 hover:underline">Créer la première table</button>
          </div>
        ) : (
          <div className="space-y-2">

            {/* Barre de recherche */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="Rechercher par code, table source, table cible..."
                className="w-full pl-10 pr-8 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
              />
              {searchTerm && (
                <button onClick={() => setSearchTerm('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Barre sélection tout */}
            <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg">
              <input
                type="checkbox"
                checked={selected.size === tables.length && tables.length > 0}
                ref={el => { if (el) el.indeterminate = selected.size > 0 && selected.size < tables.length }}
                onChange={toggleSelectAll}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 cursor-pointer"
              />
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {selected.size > 0
                  ? `${selected.size} / ${tables.length} table(s) sélectionnée(s)`
                  : searchTerm
                    ? `${filteredTables.length} / ${tables.length} tables trouvées`
                    : 'Sélectionner toutes les tables'}
              </span>
              {selected.size > 0 && (
                <button onClick={() => setSelected(new Set())} className="ml-auto text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                  Tout désélectionner
                </button>
              )}
            </div>

            {/* Aucun résultat */}
            {filteredTables.length === 0 && searchTerm && (
              <div className="text-center py-10 text-gray-400 dark:text-gray-500">
                <Search className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">Aucune table ne correspond à <strong>"{searchTerm}"</strong></p>
              </div>
            )}

            {filteredTables.map(table => (
              <div key={table.code}
                onClick={() => toggleSelect(table.code)}
                className={`flex items-center justify-between p-4 bg-white dark:bg-gray-800 border rounded-lg cursor-pointer transition-colors ${
                  selected.has(table.code)
                    ? 'border-blue-400 dark:border-blue-500 bg-blue-50/30 dark:bg-blue-900/10'
                    : 'border-gray-200 dark:border-gray-700 hover:border-blue-300'
                }`}>
                <div className="flex items-center gap-3 min-w-0">
                  <input
                    type="checkbox"
                    checked={selected.has(table.code)}
                    onChange={() => toggleSelect(table.code)}
                    onClick={e => e.stopPropagation()}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 cursor-pointer shrink-0"
                  />
                  <Database className={`w-5 h-5 shrink-0 ${table.actif ? 'text-blue-500' : 'text-gray-400'}`} />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono font-medium text-gray-900 dark:text-white">{table.code}</span>
                      <span className="text-xs text-gray-400">{table.table_name} → {table.target_table}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-gray-500 dark:text-gray-400">{table.sync_type} • {table.interval_minutes}min • {table.priority}</span>
                      {table.description && <span className="text-xs text-gray-400">• {table.description}</span>}
                      <span className="text-xs text-gray-400">v{table.version}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4 shrink-0" onClick={e => e.stopPropagation()}>
                  <button onClick={() => handleEdit(table)} className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors">
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleDelete(table.code)} className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* Propositions clients */}
      {activeTab === 'proposals' && (
        proposals.length === 0 ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <Users className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">Aucune proposition reçue des clients</p>
          </div>
        ) : (
          <div className="space-y-3">
            {proposals.map(prop => {
              const badge = STATUT_BADGE[prop.statut] || STATUT_BADGE.en_attente
              const Icon = badge.icon
              const isExpanded = expandedProposal === prop.id
              return (
                <div key={prop.id} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50"
                    onClick={() => setExpandedProposal(isExpanded ? null : prop.id)}>
                    <div className="flex items-center gap-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full font-medium ${badge.color}`}>
                        <Icon className="w-3 h-3" /> {badge.label}
                      </span>
                      <span className="text-sm font-mono font-medium text-gray-900 dark:text-white">{prop.table_name}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                        {prop.dwh_code}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-400">
                        {prop.date_creation ? new Date(prop.date_creation).toLocaleDateString('fr-FR') : ''}
                      </span>
                      {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700 pt-3 space-y-3">
                      {prop.description && <p className="text-sm text-gray-600 dark:text-gray-400">{prop.description}</p>}
                      {prop.justification && (
                        <div className="p-2 bg-amber-50 dark:bg-amber-900/10 rounded text-xs text-amber-800 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
                          <strong>Justification :</strong> {prop.justification}
                        </div>
                      )}
                      {prop.source_query && (
                        <pre className="p-2 bg-gray-50 dark:bg-gray-900 rounded text-xs text-gray-700 dark:text-gray-400 overflow-x-auto border border-gray-200 dark:border-gray-700">
                          {prop.source_query}
                        </pre>
                      )}
                      {prop.statut === 'en_attente' && (
                        <div className="flex gap-2 pt-1">
                          <button
                            onClick={() => handleValidate(prop, 'validee')}
                            disabled={validating === prop.id}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded-lg transition-colors">
                            <CheckCircle className="w-4 h-4" /> Valider & Publier
                          </button>
                          <button
                            onClick={() => handleValidate(prop, 'rejetee')}
                            disabled={validating === prop.id}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-lg transition-colors">
                            <XCircle className="w-4 h-4" /> Rejeter
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )
      )}
    </div>
  )
}
