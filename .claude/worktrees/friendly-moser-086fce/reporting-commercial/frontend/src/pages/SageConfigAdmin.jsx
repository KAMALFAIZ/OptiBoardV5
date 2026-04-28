import { useState, useEffect, useCallback } from 'react'
import {
  Database, Plus, Edit2, Trash2, RefreshCw, Play, X, Save,
  AlertCircle, CheckCircle, RotateCcw, Info
} from 'lucide-react'
import {
  getSageConfigMappings,
  createSageMapping,
  updateSageMapping,
  deleteSageMapping,
  resetSageMappings,
  invalidateSageCache,
  testSageSql,
  extractErrorMessage,
} from '../services/api'

const EMPTY_FORM = {
  id: null,
  table_name: '',
  sage_sql: '',
  is_stub: false,
  actif: true,
  description: '',
}

export default function SageConfigAdmin() {
  const [mappings, setMappings] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  const [editorOpen, setEditorOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testDb, setTestDb] = useState('bijou')
  const [testSociete, setTestSociete] = useState('bijou')

  const showSuccess = (msg) => {
    setSuccessMsg(msg)
    setTimeout(() => setSuccessMsg(null), 3000)
  }

  const loadMappings = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getSageConfigMappings(true)
      setMappings(res.data.data || [])
    } catch (e) {
      setError(extractErrorMessage(e, 'Erreur chargement mappings'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadMappings() }, [loadMappings])

  const openCreate = () => {
    setForm(EMPTY_FORM)
    setTestResult(null)
    setEditorOpen(true)
  }

  const openEdit = (m) => {
    setForm({
      id: m.id,
      table_name: m.table_name || '',
      sage_sql: m.sage_sql || '',
      is_stub: !!m.is_stub,
      actif: !!m.actif,
      description: m.description || '',
    })
    setTestResult(null)
    setEditorOpen(true)
  }

  const closeEditor = () => {
    setEditorOpen(false)
    setForm(EMPTY_FORM)
    setTestResult(null)
  }

  const handleSave = async () => {
    if (!form.table_name.trim() || !form.sage_sql.trim()) {
      setError('Le nom de table et le SQL Sage sont obligatoires')
      return
    }
    setSaving(true)
    setError(null)
    try {
      if (form.id) {
        await updateSageMapping(form.id, {
          table_name: form.table_name.trim(),
          sage_sql: form.sage_sql,
          is_stub: form.is_stub,
          actif: form.actif,
          description: form.description || null,
        })
        showSuccess('Mapping mis à jour')
      } else {
        await createSageMapping({
          table_name: form.table_name.trim(),
          sage_sql: form.sage_sql,
          is_stub: form.is_stub,
          description: form.description || null,
        })
        showSuccess('Mapping créé')
      }
      closeEditor()
      loadMappings()
    } catch (e) {
      setError(extractErrorMessage(e, 'Erreur sauvegarde'))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (m) => {
    if (!window.confirm(`Supprimer le mapping "${m.table_name}" ?`)) return
    try {
      await deleteSageMapping(m.id)
      showSuccess('Mapping supprimé')
      loadMappings()
    } catch (e) {
      setError(extractErrorMessage(e, 'Erreur suppression'))
    }
  }

  const handleReset = async () => {
    if (!window.confirm('Réinitialiser TOUS les mappings depuis config.py ? Les modifications seront perdues.')) return
    try {
      const res = await resetSageMappings()
      showSuccess(res.data.message || 'Réinitialisation OK')
      loadMappings()
    } catch (e) {
      setError(extractErrorMessage(e, 'Erreur reset'))
    }
  }

  const handleInvalidateCache = async () => {
    try {
      await invalidateSageCache()
      showSuccess('Cache invalidé')
    } catch (e) {
      setError(extractErrorMessage(e, 'Erreur cache'))
    }
  }

  const handleTestSql = async () => {
    if (!form.sage_sql.trim()) {
      setError('SQL vide')
      return
    }
    setTesting(true)
    setTestResult(null)
    try {
      const res = await testSageSql(form.sage_sql, testDb, testSociete)
      setTestResult(res.data)
    } catch (e) {
      setTestResult({ success: false, error: extractErrorMessage(e, 'Erreur test SQL') })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
          <Database className="h-6 w-6 text-orange-600 dark:text-orange-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Mappings Sage Direct
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Gérer les CTEs qui reproduisent les vues DWH depuis Sage
          </p>
        </div>
        <div className="ml-auto flex gap-2">
          <button
            onClick={handleInvalidateCache}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600
                       text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg"
          >
            <RefreshCw className="h-4 w-4" /> Invalider cache
          </button>
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-orange-300 dark:border-orange-700
                       text-orange-700 dark:text-orange-300 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded-lg"
          >
            <RotateCcw className="h-4 w-4" /> Reset config.py
          </button>
          <button
            onClick={openCreate}
            className="flex items-center gap-1.5 px-4 py-2 text-sm bg-orange-500 hover:bg-orange-600
                       text-white font-medium rounded-lg"
          >
            <Plus className="h-4 w-4" /> Nouveau mapping
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200
                        dark:border-red-700 rounded-lg text-red-700 dark:text-red-300 text-sm">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)}><X className="h-4 w-4" /></button>
        </div>
      )}
      {successMsg && (
        <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200
                        dark:border-green-700 rounded-lg text-green-700 dark:text-green-300 text-sm">
          <CheckCircle className="h-4 w-4 flex-shrink-0" />
          {successMsg}
        </div>
      )}

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <RefreshCw className="h-5 w-5 animate-spin mr-2" />
            Chargement...
          </div>
        ) : mappings.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400">
            <Database className="h-12 w-12 mb-3 opacity-40" />
            <p className="text-sm">Aucun mapping défini</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-700/60 text-xs font-semibold
                             text-gray-600 dark:text-gray-300 uppercase tracking-wide">
                <th className="px-4 py-3 text-left">Table DWH</th>
                <th className="px-4 py-3 text-left">Description</th>
                <th className="px-4 py-3 text-center">Actif</th>
                <th className="px-4 py-3 text-center">Stub</th>
                <th className="px-4 py-3 text-left">Mis à jour</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {mappings.map(m => (
                <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/40">
                  <td className="px-4 py-3 font-mono font-medium text-gray-900 dark:text-white">
                    {m.table_name}
                  </td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs max-w-md truncate">
                    {m.description || '-'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {m.actif ? (
                      <span className="inline-block px-2 py-0.5 rounded text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">Oui</span>
                    ) : (
                      <span className="inline-block px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-500">Non</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {m.is_stub ? (
                      <span className="inline-block px-2 py-0.5 rounded text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300">Stub</span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {m.updated_at ? m.updated_at.slice(0, 19).replace('T', ' ') : '-'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => openEdit(m)}
                        className="p-1.5 text-gray-500 hover:text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded"
                        title="Modifier"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(m)}
                        className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                        title="Supprimer"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Editor Modal */}
      {editorOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-5xl max-h-[90vh] flex flex-col">
            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {form.id ? `Modifier mapping #${form.id}` : 'Nouveau mapping'}
              </h2>
              <button onClick={closeEditor} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal body */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1 uppercase">
                    Nom table DWH *
                  </label>
                  <input
                    type="text"
                    value={form.table_name}
                    onChange={e => setForm({ ...form, table_name: e.target.value })}
                    placeholder="ex: Articles, LigneVente..."
                    className="w-full h-9 px-3 rounded-lg border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm font-mono
                               focus:outline-none focus:ring-2 focus:ring-orange-400"
                  />
                </div>
                <div className="flex items-end gap-4">
                  <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                    <input
                      type="checkbox"
                      checked={form.is_stub}
                      onChange={e => setForm({ ...form, is_stub: e.target.checked })}
                      className="h-4 w-4 rounded text-orange-500 focus:ring-orange-400"
                    />
                    Stub (non supporté)
                  </label>
                  {form.id && (
                    <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                      <input
                        type="checkbox"
                        checked={form.actif}
                        onChange={e => setForm({ ...form, actif: e.target.checked })}
                        className="h-4 w-4 rounded text-orange-500 focus:ring-orange-400"
                      />
                      Actif
                    </label>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1 uppercase">
                  Description
                </label>
                <input
                  type="text"
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                  className="w-full h-9 px-3 rounded-lg border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm
                             focus:outline-none focus:ring-2 focus:ring-orange-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1 uppercase">
                  SQL Sage (avec placeholders &#123;db&#125; et &#123;societe&#125;) *
                </label>
                <textarea
                  value={form.sage_sql}
                  onChange={e => setForm({ ...form, sage_sql: e.target.value })}
                  rows={14}
                  spellCheck={false}
                  placeholder="SELECT ... FROM [{db}].[dbo].[F_ARTICLE] ..."
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-xs font-mono
                             focus:outline-none focus:ring-2 focus:ring-orange-400"
                />
                <p className="mt-1 text-xs text-gray-500 flex items-center gap-1">
                  <Info className="h-3 w-3" />
                  Les placeholders &#123;db&#125; et &#123;societe&#125; seront remplacés lors de l'exécution multi-société
                </p>
              </div>

              {/* Test SQL zone */}
              <div className="bg-gray-50 dark:bg-gray-700/30 border border-gray-200 dark:border-gray-600 rounded-lg p-3">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xs font-semibold uppercase text-gray-600 dark:text-gray-400">Test SQL</h3>
                  <input
                    type="text"
                    value={testDb}
                    onChange={e => setTestDb(e.target.value)}
                    placeholder="DB Sage"
                    className="h-7 px-2 text-xs rounded border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <input
                    type="text"
                    value={testSociete}
                    onChange={e => setTestSociete(e.target.value)}
                    placeholder="Code société"
                    className="h-7 px-2 text-xs rounded border border-gray-300 dark:border-gray-600
                               bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <button
                    onClick={handleTestSql}
                    disabled={testing}
                    className="flex items-center gap-1 px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600
                               disabled:opacity-50 text-white rounded"
                  >
                    {testing ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                    Tester (TOP 5)
                  </button>
                </div>

                {testResult && (
                  <div className="mt-2">
                    {testResult.success ? (
                      <div>
                        <p className="text-xs text-green-700 dark:text-green-300 mb-2">
                          ✓ {testResult.nb_rows} ligne(s) · {testResult.columns?.length} colonne(s)
                        </p>
                        {testResult.rows?.length > 0 && (
                          <div className="overflow-x-auto border border-gray-200 dark:border-gray-600 rounded">
                            <table className="text-xs w-full">
                              <thead>
                                <tr className="bg-gray-100 dark:bg-gray-700">
                                  {testResult.columns.map(c => (
                                    <th key={c} className="px-2 py-1 text-left font-semibold text-gray-600 dark:text-gray-300">
                                      {c}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {testResult.rows.map((r, i) => (
                                  <tr key={i} className="border-t border-gray-200 dark:border-gray-700">
                                    {testResult.columns.map(c => (
                                      <td key={c} className="px-2 py-1 text-gray-700 dark:text-gray-300 max-w-xs truncate">
                                        {r[c] ?? '—'}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="p-2 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-xs rounded whitespace-pre-wrap font-mono">
                        {testResult.error}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Modal footer */}
            <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={closeEditor}
                className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                Annuler
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-1.5 px-4 py-2 text-sm bg-orange-500 hover:bg-orange-600
                           disabled:opacity-50 text-white font-medium rounded-lg"
              >
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {form.id ? 'Enregistrer' : 'Créer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
