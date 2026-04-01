import { useState, useEffect } from 'react'
import { GitBranch, Plus, Trash2, Edit, ToggleLeft, ToggleRight, ChevronRight, X, Save } from 'lucide-react'
import api from '../services/api'

const SOURCE_TYPES = [
  { value: 'gridview', label: 'GridView (tableau)' },
  { value: 'dashboard', label: 'Dashboard' },
  { value: 'pivot', label: 'Pivot V2' },
]

const emptyRule = {
  nom: '',
  source_type: 'gridview',
  source_id: '',
  source_column: '',
  target_type: 'gridview',
  target_id: '',
  target_filter_field: '',
  label: '',
  is_active: true,
}

export default function DrillThroughPage() {
  const [rules, setRules] = useState([])
  const [availableReports, setAvailableReports] = useState({ gridview: [], dashboard: [], pivot: [] })
  const [sourceColumns, setSourceColumns] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(emptyRule)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadAll()
  }, [])

  // Charger les colonnes quand la source GridView change
  useEffect(() => {
    if (form.source_type === 'gridview' && form.source_id) {
      api.get(`/drillthrough/columns/${form.source_id}`)
        .then(res => setSourceColumns(res.data.data || []))
        .catch(() => setSourceColumns([]))
    } else {
      setSourceColumns([])
    }
  }, [form.source_type, form.source_id])

  const loadAll = async () => {
    setLoading(true)
    try {
      const [rulesRes, reportsRes] = await Promise.all([
        api.get('/drillthrough/rules'),
        api.get('/drillthrough/available-reports'),
      ])
      setRules(rulesRes.data.data || [])
      setAvailableReports(reportsRes.data.data || { gridview: [], dashboard: [], pivot: [] })
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const openCreate = () => {
    setForm(emptyRule)
    setEditingId(null)
    setShowForm(true)
  }

  const openEdit = (rule) => {
    setForm({
      nom: rule.nom,
      source_type: rule.source_type,
      source_id: rule.source_id,
      source_column: rule.source_column,
      target_type: rule.target_type,
      target_id: rule.target_id,
      target_filter_field: rule.target_filter_field,
      label: rule.label || '',
      is_active: rule.is_active,
    })
    setEditingId(rule.id)
    setShowForm(true)
  }

  const closeForm = () => {
    setShowForm(false)
    setEditingId(null)
    setForm(emptyRule)
    setSourceColumns([])
  }

  const handleSave = async () => {
    if (!form.nom || !form.source_id || !form.source_column || !form.target_id || !form.target_filter_field) {
      alert('Veuillez remplir tous les champs obligatoires.')
      return
    }
    setSaving(true)
    try {
      const payload = { ...form, source_id: Number(form.source_id), target_id: Number(form.target_id) }
      if (editingId) {
        await api.put(`/drillthrough/rules/${editingId}`, payload)
      } else {
        await api.post('/drillthrough/rules', payload)
      }
      await loadAll()
      closeForm()
    } catch (e) {
      console.error(e)
      alert('Erreur lors de la sauvegarde.')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Supprimer cette règle drill-through ?')) return
    await api.delete(`/drillthrough/rules/${id}`)
    setRules(prev => prev.filter(r => r.id !== id))
  }

  const handleToggle = async (id) => {
    await api.post(`/drillthrough/rules/${id}/toggle`)
    setRules(prev => prev.map(r => r.id === id ? { ...r, is_active: !r.is_active } : r))
  }

  const sourceReports = availableReports[form.source_type] || []
  const targetReports = availableReports[form.target_type] || []

  return (
    <div className="p-4 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <GitBranch className="w-6 h-6 text-primary-500" />
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Drill-through inter-rapports</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Configurez des liens de navigation entre rapports</p>
          </div>
        </div>
        <button onClick={openCreate} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Nouvelle règle
        </button>
      </div>

      {/* Rules list */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Chargement...</div>
      ) : rules.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <GitBranch className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="font-medium">Aucune règle drill-through configurée</p>
          <p className="text-sm mt-1">Créez une règle pour permettre la navigation entre rapports.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map(rule => (
            <div key={rule.id} className={`bg-white dark:bg-gray-800 rounded-xl border shadow-sm p-4 flex items-center gap-4 ${rule.is_active ? 'border-gray-200 dark:border-gray-700' : 'border-gray-100 dark:border-gray-800 opacity-60'}`}>
              {/* Source → Cible */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-gray-900 dark:text-white">{rule.nom}</span>
                  {!rule.is_active && <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-400">Inactif</span>}
                </div>
                <div className="flex items-center gap-1.5 mt-1 text-xs text-gray-500 flex-wrap">
                  <span className="px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-medium">{rule.source_name}</span>
                  <span className="text-gray-400">col: <b>{rule.source_column}</b></span>
                  <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
                  <span className="px-1.5 py-0.5 rounded bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 font-medium">{rule.target_name}</span>
                  <span className="text-gray-400">filtre: <b>{rule.target_filter_field}</b></span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <button
                  onClick={() => handleToggle(rule.id)}
                  className={`p-1.5 rounded-lg transition-colors ${rule.is_active ? 'text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20' : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
                  title={rule.is_active ? 'Désactiver' : 'Activer'}
                >
                  {rule.is_active ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
                </button>
                <button onClick={() => openEdit(rule)} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" title="Modifier">
                  <Edit className="w-4 h-4" />
                </button>
                <button onClick={() => handleDelete(rule.id)} className="p-1.5 rounded-lg text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors" title="Supprimer">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={closeForm} />
          <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl w-[600px] max-w-[95vw] max-h-[90vh] overflow-auto">
            <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {editingId ? 'Modifier la règle' : 'Nouvelle règle drill-through'}
              </h2>
              <button onClick={closeForm} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {/* Nom */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  value={form.nom}
                  onChange={e => setForm(f => ({ ...f, nom: e.target.value }))}
                  placeholder="Ex: Clients → Détail commandes"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-primary-500 text-sm"
                />
              </div>

              {/* Source */}
              <div className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-lg space-y-3 border border-blue-100 dark:border-blue-800/30">
                <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-300">Source (rapport de départ)</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Type de rapport</label>
                    <select
                      value={form.source_type}
                      onChange={e => setForm(f => ({ ...f, source_type: e.target.value, source_id: '', source_column: '' }))}
                      className="w-full px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white text-sm"
                    >
                      {SOURCE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Rapport <span className="text-red-500">*</span></label>
                    <select
                      value={form.source_id}
                      onChange={e => setForm(f => ({ ...f, source_id: e.target.value, source_column: '' }))}
                      className="w-full px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white text-sm"
                    >
                      <option value="">-- Sélectionner --</option>
                      {sourceReports.map(r => <option key={r.id} value={r.id}>{r.nom}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                    Colonne source (champ cliquable) <span className="text-red-500">*</span>
                  </label>
                  {form.source_type === 'gridview' && sourceColumns.length > 0 ? (
                    <select
                      value={form.source_column}
                      onChange={e => setForm(f => ({ ...f, source_column: e.target.value }))}
                      className="w-full px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white text-sm"
                    >
                      <option value="">-- Sélectionner --</option>
                      {sourceColumns.map(c => <option key={c.field} value={c.field}>{c.header || c.field}</option>)}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={form.source_column}
                      onChange={e => setForm(f => ({ ...f, source_column: e.target.value }))}
                      placeholder="Ex: Client, Mois, Categorie..."
                      className="w-full px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white text-sm"
                    />
                  )}
                </div>
              </div>

              {/* Target */}
              <div className="p-4 bg-green-50 dark:bg-green-900/10 rounded-lg space-y-3 border border-green-100 dark:border-green-800/30">
                <h3 className="text-sm font-semibold text-green-700 dark:text-green-300">Cible (rapport de destination)</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Type de rapport</label>
                    <select
                      value={form.target_type}
                      onChange={e => setForm(f => ({ ...f, target_type: e.target.value, target_id: '' }))}
                      className="w-full px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white text-sm"
                    >
                      {SOURCE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Rapport <span className="text-red-500">*</span></label>
                    <select
                      value={form.target_id}
                      onChange={e => setForm(f => ({ ...f, target_id: e.target.value }))}
                      className="w-full px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white text-sm"
                    >
                      <option value="">-- Sélectionner --</option>
                      {targetReports.map(r => <option key={r.id} value={r.id}>{r.nom}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                    Champ de filtre dans la cible <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={form.target_filter_field}
                    onChange={e => setForm(f => ({ ...f, target_filter_field: e.target.value }))}
                    placeholder="Ex: CLIENT, CodeClient, NomClient..."
                    className="w-full px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white text-sm"
                  />
                  <p className="text-xs text-gray-400 mt-1">Nom exact du champ dans le rapport cible sur lequel filtrer la valeur cliquée</p>
                </div>
              </div>

              {/* Libellé */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Libellé (menu contextuel)</label>
                <input
                  type="text"
                  value={form.label}
                  onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
                  placeholder="Ex: Voir les commandes de ce client"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-primary-500 text-sm"
                />
              </div>

              {/* Active */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                  className="rounded border-gray-300 w-4 h-4"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Règle active</span>
              </label>
            </div>

            <div className="flex justify-end gap-2 p-5 border-t border-gray-200 dark:border-gray-700">
              <button onClick={closeForm} className="btn-secondary">Annuler</button>
              <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
                <Save className="w-4 h-4" />
                {saving ? 'Sauvegarde...' : 'Sauvegarder'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
