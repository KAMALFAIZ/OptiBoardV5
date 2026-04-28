/**
 * ETLClientTablesConfig — Architecture double onglet
 * ====================================================
 * Onglet 1 "Tables KASOFT" : tables publiees par le central (lecture seule + toggle)
 * Onglet 2 "Mes Tables"    : tables personnalisees du client (CRUD + publication agent)
 */
import { useState, useEffect } from 'react'
import {
  Database, Plus, RefreshCw, Send, CheckCircle, XCircle,
  Edit2, Trash2, Lock, Eye, Download
} from 'lucide-react'
import {
  getPublishedETLTables,
  toggleETLTable,
  getClientCustomETLTables,
  createClientCustomETLTable,
  updateClientCustomETLTable,
  deleteClientCustomETLTable,
  publishClientCustomETLTables,
} from '../../services/etlApi'

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

const SYNC_TYPE_BADGE = {
  incremental: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  full:        'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
}

const EMPTY_FORM = {
  code: '',
  table_name: '',
  target_table: '',
  source_query: '',
  sync_type: 'incremental',
  primary_key_columns: '',
  interval_minutes: 5,
  description: '',
}

// ---------------------------------------------------------------------------
// Composant principal
// ---------------------------------------------------------------------------

export default function ETLClientTablesConfig({ agents = [], onSyncFromOptiBoard }) {
  const [activeTab, setActiveTab]       = useState('kasoft')

  // --- onglet KASOFT ---
  const [kasoftTables, setKasoftTables] = useState([])
  const [kasoftLoading, setKasoftLoading] = useState(true)
  const [toggling, setToggling]         = useState(null)

  // --- onglet MES TABLES ---
  const [customTables, setCustomTables] = useState([])
  const [customLoading, setCustomLoading] = useState(true)
  const [showForm, setShowForm]         = useState(false)
  const [editingCode, setEditingCode]   = useState(null)   // null = nouvelle table
  const [form, setForm]                 = useState(EMPTY_FORM)
  const [saving, setSaving]             = useState(false)
  const [publishing, setPublishing]     = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(null) // code a confirmer

  // --- messages globaux ---
  const [error, setError]   = useState(null)
  const [success, setSuccess] = useState(null)
  const [syncing, setSyncing] = useState(false)

  // ---------------------------------------------------------------------------
  // Chargements
  // ---------------------------------------------------------------------------

  const loadKasoftTables = async () => {
    setKasoftLoading(true)
    try {
      const res = await getPublishedETLTables()
      setKasoftTables(res.data?.data || [])
    } catch {
      setError('Impossible de charger les tables KASOFT')
    } finally {
      setKasoftLoading(false)
    }
  }

  const loadCustomTables = async () => {
    setCustomLoading(true)
    try {
      const res = await getClientCustomETLTables()
      setCustomTables(res.data?.data || [])
    } catch {
      setError('Impossible de charger vos tables personnalisees')
    } finally {
      setCustomLoading(false)
    }
  }

  useEffect(() => {
    loadKasoftTables()
    loadCustomTables()
  }, [])

  // Effacer le message de succes apres 4s
  useEffect(() => {
    if (!success) return
    const t = setTimeout(() => setSuccess(null), 4000)
    return () => clearTimeout(t)
  }, [success])

  // ---------------------------------------------------------------------------
  // Onglet KASOFT — toggle
  // ---------------------------------------------------------------------------

  const handleToggle = async (table) => {
    setToggling(table.code)
    setError(null)
    try {
      await toggleETLTable(table.code, !table.is_enabled)
      setKasoftTables(prev =>
        prev.map(t => t.code === table.code ? { ...t, is_enabled: !t.is_enabled } : t)
      )
    } catch {
      setError('Erreur lors de la mise a jour du statut')
    } finally {
      setToggling(null)
    }
  }

  // ---------------------------------------------------------------------------
  // Onglet MES TABLES — formulaire
  // ---------------------------------------------------------------------------

  const openNew = () => {
    setEditingCode(null)
    setForm(EMPTY_FORM)
    setShowForm(true)
    setError(null)
  }

  const openEdit = (table) => {
    setEditingCode(table.code)
    setForm({
      code:                table.code,
      table_name:          table.table_name,
      target_table:        table.target_table,
      source_query:        table.source_query || '',
      sync_type:           table.sync_type || 'incremental',
      primary_key_columns: Array.isArray(table.primary_key_columns)
        ? table.primary_key_columns.join(', ')
        : (() => {
            try { return JSON.parse(table.primary_key_columns || '[]').join(', ') }
            catch { return table.primary_key_columns || '' }
          })(),
      interval_minutes:    table.interval_minutes ?? 5,
      description:         table.description || '',
    })
    setShowForm(true)
    setError(null)
  }

  const cancelForm = () => {
    setShowForm(false)
    setEditingCode(null)
    setForm(EMPTY_FORM)
    setError(null)
  }

  const handleFormChange = (e) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)

    // Convertir primary_key_columns en tableau
    const pkArray = form.primary_key_columns
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)

    const payload = {
      code:                form.code,
      table_name:          form.table_name,
      target_table:        form.target_table,
      source_query:        form.source_query,
      sync_type:           form.sync_type,
      primary_key_columns: pkArray,
      interval_minutes:    parseInt(form.interval_minutes, 10) || 5,
      description:         form.description || null,
    }

    try {
      if (editingCode) {
        await updateClientCustomETLTable(editingCode, payload)
        setSuccess(`Table '${editingCode}' mise a jour`)
      } else {
        await createClientCustomETLTable(payload)
        setSuccess(`Table '${form.code}' creee`)
      }
      cancelForm()
      loadCustomTables()
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erreur lors de la sauvegarde'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (code) => {
    if (deleteConfirm !== code) {
      setDeleteConfirm(code)
      return
    }
    setDeleteConfirm(null)
    setError(null)
    try {
      await deleteClientCustomETLTable(code)
      setSuccess(`Table '${code}' supprimee`)
      setCustomTables(prev => prev.filter(t => t.code !== code))
    } catch {
      setError('Erreur lors de la suppression')
    }
  }

  // ---------------------------------------------------------------------------
  // Publication vers agent
  // ---------------------------------------------------------------------------

  const handlePublish = async () => {
    setPublishing(true)
    setError(null)
    try {
      const res = await publishClientCustomETLTables()
      const r = res.data?.results || {}
      setSuccess(
        `Publication terminee : ${r.published ?? 0} nouvelle(s), ${r.updated ?? 0} mise(s) a jour` +
        (r.failed ? `, ${r.failed} echec(s)` : '')
      )
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erreur lors de la publication'
      setError(msg)
    } finally {
      setPublishing(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Rendu
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-4">

      {/* En-tete */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white">
            Tables ETL
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Tables publiées par OptiBoard + vos tables personnalisées
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Bouton Récupérer depuis OptiBoard */}
          {onSyncFromOptiBoard && agents.length > 0 && (
            <button
              onClick={async () => {
                setSyncing(true)
                setError(null)
                try {
                  await onSyncFromOptiBoard(agents[0])
                  await loadKasoftTables()
                  setSuccess('Tables récupérées depuis OptiBoard avec succès')
                } catch {
                  setError('Erreur lors de la récupération depuis OptiBoard')
                } finally {
                  setSyncing(false)
                }
              }}
              disabled={syncing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors disabled:opacity-50 shadow-sm"
              title="Récupérer les tables ETL publiées depuis le catalogue central OptiBoard"
            >
              <Download className={`w-4 h-4 ${syncing ? 'animate-bounce' : ''}`} />
              {syncing ? 'Récupération...' : 'Récup. OptiBoard'}
            </button>
          )}
          <button
            onClick={() => { loadKasoftTables(); loadCustomTables() }}
            className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Rafraichir"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Bannieres */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-400">
          <XCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-700 dark:text-green-400">
          <CheckCircle className="w-4 h-4 shrink-0" /> {success}
        </div>
      )}

      {/* Onglets */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700">
        {[
          { id: 'kasoft', label: `Tables KASOFT (${kasoftTables.length})` },
          { id: 'custom', label: `Mes Tables (${customTables.length})` },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setShowForm(false); setDeleteConfirm(null) }}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-primary-600 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* ONGLET 1 — Tables KASOFT                                            */}
      {/* ------------------------------------------------------------------ */}

      {activeTab === 'kasoft' && (
        <>
          <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg text-xs text-blue-700 dark:text-blue-400">
            <Lock className="w-4 h-4 shrink-0 mt-0.5" />
            <span>
              Tables definies par l'administrateur KASOFT — <strong>lecture seule</strong>.
              Vous pouvez uniquement les <strong>activer ou desactiver</strong>.
            </span>
          </div>

          {kasoftLoading ? (
            <div className="flex items-center justify-center py-16 text-gray-500">
              <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement...
            </div>
          ) : kasoftTables.length === 0 ? (
            <div className="text-center py-14 text-gray-500 dark:text-gray-400">
              <Database className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm">Aucune table publiee par l'administrateur KASOFT</p>
            </div>
          ) : (
            <div className="space-y-2">
              {kasoftTables.map(table => (
                <div
                  key={table.code}
                  className={`flex items-center justify-between p-4 rounded-lg border transition-colors ${
                    table.is_enabled
                      ? 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'
                      : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700 opacity-60'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Lock className="w-4 h-4 shrink-0 text-gray-400" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {table.table_name}
                        </span>
                        <span className="text-xs text-gray-400">→</span>
                        <span className="text-xs font-mono text-gray-600 dark:text-gray-400 truncate">
                          {table.target_table}
                        </span>
                        <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                          SYNC_TYPE_BADGE[table.sync_type] || SYNC_TYPE_BADGE.incremental
                        }`}>
                          {table.sync_type}
                        </span>
                      </div>
                      {table.description && (
                        <p className="text-xs text-gray-400 mt-0.5 truncate max-w-xs">
                          {table.description}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Toggle activer/desactiver */}
                  <button
                    onClick={() => handleToggle(table)}
                    disabled={toggling === table.code}
                    title={table.is_enabled ? 'Desactiver' : 'Activer'}
                    className={`ml-4 shrink-0 inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-full border transition-colors disabled:opacity-50 ${
                      table.is_enabled
                        ? 'bg-green-50 text-green-700 border-green-300 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400 dark:border-green-700'
                        : 'bg-gray-100 text-gray-500 border-gray-300 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:border-gray-600'
                    }`}
                  >
                    {table.is_enabled
                      ? <><CheckCircle className="w-3.5 h-3.5" /> Actif</>
                      : <><XCircle className="w-3.5 h-3.5" /> Inactif</>
                    }
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* ONGLET 2 — Mes Tables                                               */}
      {/* ------------------------------------------------------------------ */}

      {activeTab === 'custom' && (
        <>
          {/* Barre d'actions */}
          {!showForm && (
            <div className="flex items-center justify-between gap-3">
              <button
                onClick={handlePublish}
                disabled={publishing || customTables.length === 0}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
              >
                {publishing
                  ? <RefreshCw className="w-4 h-4 animate-spin" />
                  : <Send className="w-4 h-4" />
                }
                Publier vers agent
              </button>

              <button
                onClick={openNew}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                Nouvelle table
              </button>
            </div>
          )}

          {/* Formulaire inline (creation / edition) */}
          {showForm && (
            <form
              onSubmit={handleSave}
              className="p-4 bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700 rounded-xl space-y-4"
            >
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                {editingCode ? `Modifier — ${editingCode}` : 'Nouvelle table ETL'}
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Code */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Code <span className="text-red-500">*</span>
                  </label>
                  <input
                    name="code"
                    value={form.code}
                    onChange={handleFormChange}
                    disabled={!!editingCode}
                    required
                    placeholder="ex: MY_TABLE"
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                {/* Table source */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Nom de la table source <span className="text-red-500">*</span>
                  </label>
                  <input
                    name="table_name"
                    value={form.table_name}
                    onChange={handleFormChange}
                    required
                    placeholder="ex: F_ARTICLE"
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                {/* Table cible */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Table cible (DWH) <span className="text-red-500">*</span>
                  </label>
                  <input
                    name="target_table"
                    value={form.target_table}
                    onChange={handleFormChange}
                    required
                    placeholder="ex: DWH_ARTICLES"
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                {/* Sync type */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Type de synchronisation
                  </label>
                  <select
                    name="sync_type"
                    value={form.sync_type}
                    onChange={handleFormChange}
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="incremental">Incremental</option>
                    <option value="full">Full</option>
                  </select>
                </div>

                {/* Cles primaires */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Colonnes cle primaire <span className="text-red-500">*</span>
                    <span className="font-normal text-gray-400 ml-1">(separees par virgule)</span>
                  </label>
                  <input
                    name="primary_key_columns"
                    value={form.primary_key_columns}
                    onChange={handleFormChange}
                    required
                    placeholder="ex: cbRef, cbRevision"
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                {/* Intervalle */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Intervalle (minutes)
                  </label>
                  <input
                    name="interval_minutes"
                    type="number"
                    min="1"
                    max="1440"
                    value={form.interval_minutes}
                    onChange={handleFormChange}
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Requete source */}
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Requete source (SQL) <span className="text-red-500">*</span>
                </label>
                <textarea
                  name="source_query"
                  value={form.source_query}
                  onChange={handleFormChange}
                  required
                  rows={5}
                  placeholder="SELECT * FROM F_ARTICLE WHERE cbModification > ?"
                  className="w-full px-3 py-2 text-sm font-mono border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <input
                  name="description"
                  value={form.description}
                  onChange={handleFormChange}
                  placeholder="Description optionnelle de la table"
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              {/* Boutons du formulaire */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={cancelForm}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 rounded-lg transition-colors"
                >
                  {saving && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  {editingCode ? 'Enregistrer' : 'Creer'}
                </button>
              </div>
            </form>
          )}

          {/* Liste des tables personnalisees */}
          {!showForm && (
            <>
              {customLoading ? (
                <div className="flex items-center justify-center py-16 text-gray-500">
                  <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement...
                </div>
              ) : customTables.length === 0 ? (
                <div className="text-center py-14 text-gray-500 dark:text-gray-400">
                  <Database className="w-10 h-10 mx-auto mb-3 opacity-40" />
                  <p className="text-sm">Aucune table personnalisee</p>
                  <button
                    onClick={openNew}
                    className="mt-3 text-sm text-primary-600 hover:text-primary-700 underline"
                  >
                    Creer une premiere table
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {customTables.map(table => (
                    <div
                      key={table.code}
                      className="flex items-center justify-between p-4 rounded-lg border bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <Database className="w-5 h-5 shrink-0 text-primary-500" />
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-mono text-gray-400">{table.code}</span>
                            <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                              {table.table_name}
                            </span>
                            <span className="text-xs text-gray-400">→</span>
                            <span className="text-xs font-mono text-gray-600 dark:text-gray-400 truncate">
                              {table.target_table}
                            </span>
                            <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                              SYNC_TYPE_BADGE[table.sync_type] || SYNC_TYPE_BADGE.incremental
                            }`}>
                              {table.sync_type}
                            </span>
                          </div>
                          {table.description && (
                            <p className="text-xs text-gray-400 mt-0.5 truncate max-w-xs">
                              {table.description}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-1 ml-4 shrink-0">
                        {/* Apercu rapide (query) */}
                        {table.source_query && (
                          <button
                            title={table.source_query}
                            className="p-1.5 text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 rounded transition-colors"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        )}

                        {/* Editer */}
                        <button
                          onClick={() => openEdit(table)}
                          title="Modifier"
                          className="p-1.5 text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 rounded transition-colors"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>

                        {/* Supprimer (double-clic pour confirmer) */}
                        <button
                          onClick={() => handleDelete(table.code)}
                          title={deleteConfirm === table.code ? 'Cliquer pour confirmer' : 'Supprimer'}
                          className={`p-1.5 rounded transition-colors ${
                            deleteConfirm === table.code
                              ? 'text-red-600 bg-red-50 dark:bg-red-900/20 animate-pulse'
                              : 'text-gray-400 hover:text-red-500 dark:hover:text-red-400'
                          }`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
