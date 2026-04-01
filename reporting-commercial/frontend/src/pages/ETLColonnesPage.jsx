/**
 * ETLColonnesPage — Gestion des colonnes ETL
 * ============================================
 * Superadmin : gere le catalogue officiel des colonnes par table Sage
 * Client     : choisit quelles colonnes optionnelles inclure (toggle),
 *              ne peut PAS exclure les colonnes obligatoires
 *
 * Routes backend utilisees :
 *   GET  /api/etl-colonnes/central/{table_code}        — catalogue central
 *   POST /api/etl-colonnes/central/{table_code}        — ajouter colonne (superadmin)
 *   PUT  /api/etl-colonnes/central/{table_code}/{id}   — modifier colonne (superadmin)
 *   DELETE /api/etl-colonnes/central/{table_code}/{id} — supprimer (superadmin)
 *   GET  /api/etl-colonnes/client/{table_code}         — vue client (merged)
 *   PATCH /api/etl-colonnes/client/{table_code}/{id}   — client toggle
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Database, Lock, Eye, EyeOff, Plus, Edit2, Trash2,
  RefreshCw, ChevronLeft, Save, X, CheckCircle, AlertCircle
} from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

// ── API ──────────────────────────────────────────────────────
const getETLTables      = ()           => api.get('/etl-tables/client')
const getCentralCols    = (tableCode)  => api.get(`/etl-colonnes/central/${tableCode}`)
const createCentralCol  = (tc, data)   => api.post(`/etl-colonnes/central/${tc}`, data)
const updateCentralCol  = (tc, id, d)  => api.put(`/etl-colonnes/central/${tc}/${id}`, d)
const deleteCentralCol  = (tc, id)     => api.delete(`/etl-colonnes/central/${tc}/${id}`)
const getClientCols     = (tc)         => api.get(`/etl-colonnes/client/${tc}`)
const toggleClientCol   = (tc, id, d)  => api.patch(`/etl-colonnes/client/${tc}/${id}`, d)
const publishCols       = (tc)         => api.post(`/etl-colonnes/publish/${tc}`)

// ── Type badge ───────────────────────────────────────────────
const TYPE_COLORS = {
  VARCHAR:  'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
  NVARCHAR: 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
  INT:      'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400',
  BIGINT:   'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400',
  DECIMAL:  'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400',
  FLOAT:    'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400',
  DATE:     'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
  DATETIME: 'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
  BIT:      'bg-gray-50 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
}
const typeColor = t => TYPE_COLORS[t?.toUpperCase()] || TYPE_COLORS.VARCHAR

const SQL_TYPES = ['VARCHAR','NVARCHAR','INT','BIGINT','DECIMAL','FLOAT','DATE','DATETIME','BIT','TEXT','NTEXT']

// ── EmptyForm ────────────────────────────────────────────────
const EMPTY_FORM = {
  nom_colonne: '', type_donnee: 'VARCHAR', longueur: '',
  description: '', obligatoire: false, visible_client: true, valeur_defaut: ''
}

// ── ColonneForm modal ────────────────────────────────────────
function ColonneFormModal({ initial, onSave, onClose }) {
  const [form, setForm] = useState(initial || EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!form.nom_colonne || !form.type_donnee) return
    setSaving(true)
    try {
      await onSave(form)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-bold text-gray-900 dark:text-white">
            {initial ? 'Modifier la colonne' : 'Ajouter une colonne'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Nom colonne *</label>
            <input
              className="w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
              value={form.nom_colonne}
              onChange={e => setForm(f => ({ ...f, nom_colonne: e.target.value }))}
              placeholder="ex: cbModification"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Type SQL *</label>
              <select
                className="w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                value={form.type_donnee}
                onChange={e => setForm(f => ({ ...f, type_donnee: e.target.value }))}
              >
                {SQL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Longueur</label>
              <input
                type="number"
                className="w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                value={form.longueur}
                onChange={e => setForm(f => ({ ...f, longueur: e.target.value }))}
                placeholder="ex: 200"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Description</label>
            <input
              className="w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Description de la colonne"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Valeur par defaut</label>
            <input
              className="w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
              value={form.valeur_defaut}
              onChange={e => setForm(f => ({ ...f, valeur_defaut: e.target.value }))}
              placeholder="NULL"
            />
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 rounded text-red-600"
                checked={form.obligatoire}
                onChange={e => setForm(f => ({ ...f, obligatoire: e.target.checked }))}
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                <span className="font-medium">Obligatoire</span>
                <span className="text-xs text-gray-400 ml-1">(client ne peut pas exclure)</span>
              </span>
            </label>
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 rounded text-blue-600"
                checked={form.visible_client}
                onChange={e => setForm(f => ({ ...f, visible_client: e.target.checked }))}
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Visible client</span>
            </label>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
            Annuler
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !form.nom_colonne}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors"
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────
export default function ETLColonnesPage() {
  const { user } = useAuth()
  const isSuperAdmin = !user?.dwh_code   // superadmin n'a pas de dwh_code

  const [tables, setTables]         = useState([])
  const [selectedTable, setSelected] = useState(null)
  const [colonnes, setColonnes]     = useState([])
  const [loadingTables, setLoadingT] = useState(true)
  const [loadingCols, setLoadingC]  = useState(false)
  const [showForm, setShowForm]     = useState(false)
  const [editingCol, setEditingCol] = useState(null)
  const [toast, setToast]           = useState(null)

  const showMsg = (msg, type='success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  // Charger la liste des tables ETL
  const loadTables = useCallback(async () => {
    setLoadingT(true)
    try {
      const res = await getETLTables()
      setTables(res.data?.data || res.data || [])
    } catch (e) {
      showMsg('Erreur chargement tables', 'error')
    } finally {
      setLoadingT(false)
    }
  }, [])

  // Charger les colonnes d'une table
  const loadColonnes = useCallback(async (tableCode) => {
    setLoadingC(true)
    try {
      const res = isSuperAdmin
        ? await getCentralCols(tableCode)
        : await getClientCols(tableCode)
      setColonnes(res.data?.data || res.data || [])
    } catch (e) {
      showMsg('Erreur chargement colonnes', 'error')
    } finally {
      setLoadingC(false)
    }
  }, [isSuperAdmin])

  useEffect(() => { loadTables() }, [loadTables])

  const handleSelectTable = (table) => {
    setSelected(table)
    loadColonnes(table.code)
  }

  const handleBack = () => {
    setSelected(null)
    setColonnes([])
  }

  // Superadmin : sauvegarder une colonne (create ou update)
  const handleSaveCol = async (formData) => {
    try {
      if (editingCol) {
        await updateCentralCol(selectedTable.code, editingCol.id, formData)
        showMsg('Colonne mise a jour')
      } else {
        await createCentralCol(selectedTable.code, formData)
        showMsg('Colonne ajoutee')
      }
      setShowForm(false)
      setEditingCol(null)
      loadColonnes(selectedTable.code)
    } catch (e) {
      showMsg(e.response?.data?.detail || 'Erreur', 'error')
    }
  }

  // Superadmin : supprimer une colonne
  const handleDeleteCol = async (col) => {
    if (!window.confirm(`Supprimer la colonne "${col.nom_colonne}" ?`)) return
    try {
      await deleteCentralCol(selectedTable.code, col.id)
      showMsg('Colonne supprimee')
      loadColonnes(selectedTable.code)
    } catch (e) {
      showMsg(e.response?.data?.detail || 'Erreur', 'error')
    }
  }

  // Client : toggler une colonne
  const handleToggleCol = async (col) => {
    if (col.obligatoire) return   // ne peut pas toggler une colonne obligatoire
    try {
      await toggleClientCol(selectedTable.code, col.id, { inclus: !col.inclus })
      setColonnes(cols => cols.map(c => c.id === col.id ? { ...c, inclus: !c.inclus } : c))
    } catch (e) {
      showMsg(e.response?.data?.detail || 'Erreur', 'error')
    }
  }

  // Superadmin : publier les colonnes vers tous les clients
  const handlePublish = async () => {
    try {
      const res = await publishCols(selectedTable.code)
      showMsg(res.data?.message || 'Colonnes publiees')
    } catch (e) {
      showMsg('Erreur publication', 'error')
    }
  }

  // ── Vue liste des tables ──
  if (!selectedTable) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        {toast && (
          <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg text-sm font-medium text-white ${toast.type === 'error' ? 'bg-red-600' : 'bg-green-600'}`}>
            {toast.msg}
          </div>
        )}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Database className="w-6 h-6 text-blue-600" />
            Colonnes ETL
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {isSuperAdmin
              ? 'Definissez les colonnes officielles du catalogue par table Sage'
              : 'Personnalisez les colonnes incluses dans votre synchronisation'
            }
          </p>
        </div>

        {loadingTables ? (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement...
          </div>
        ) : tables.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <Database className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">Aucune table ETL disponible</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {tables.map(table => (
              <button
                key={table.code || table.id}
                onClick={() => handleSelectTable(table)}
                className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-sm transition-all text-left"
              >
                <div>
                  <p className="font-semibold text-gray-900 dark:text-white">{table.nom || table.table_name}</p>
                  <p className="text-xs text-gray-400 mt-0.5 font-mono">{table.code}</p>
                  {table.description && (
                    <p className="text-xs text-gray-500 mt-1">{table.description}</p>
                  )}
                </div>
                <ChevronLeft className="w-5 h-5 text-gray-300 rotate-180" />
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── Vue colonnes d'une table ──
  const colsObligatoires = colonnes.filter(c => c.obligatoire)
  const colsOptionnelles = colonnes.filter(c => !c.obligatoire)

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg text-sm font-medium text-white ${toast.type === 'error' ? 'bg-red-600' : 'bg-green-600'}`}>
          {toast.msg}
        </div>
      )}

      {showForm && (
        <ColonneFormModal
          initial={editingCol}
          onSave={handleSaveCol}
          onClose={() => { setShowForm(false); setEditingCol(null) }}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">{selectedTable.nom || selectedTable.table_name}</h2>
            <p className="text-xs text-gray-400 font-mono">{selectedTable.code}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isSuperAdmin && (
            <>
              <button
                onClick={handlePublish}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
              >
                <CheckCircle className="w-4 h-4" /> Publier vers clients
              </button>
              <button
                onClick={() => { setEditingCol(null); setShowForm(true) }}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" /> Ajouter
              </button>
            </>
          )}
          <button
            onClick={() => loadColonnes(selectedTable.code)}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {loadingCols ? (
        <div className="flex items-center justify-center py-16 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement des colonnes...
        </div>
      ) : colonnes.length === 0 ? (
        <div className="text-center py-16 text-gray-400 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <Database className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Aucune colonne definie pour cette table</p>
          {isSuperAdmin && (
            <button
              onClick={() => setShowForm(true)}
              className="mt-3 text-sm text-blue-600 hover:underline"
            >
              + Ajouter la premiere colonne
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {/* Colonnes obligatoires */}
          {colsObligatoires.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-red-100 dark:border-red-900/30 overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2.5 bg-red-50 dark:bg-red-900/20 border-b border-red-100 dark:border-red-900/30">
                <Lock className="w-4 h-4 text-red-500" />
                <span className="text-sm font-semibold text-red-700 dark:text-red-400">
                  Colonnes obligatoires ({colsObligatoires.length}) — toujours incluses
                </span>
              </div>
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {colsObligatoires.map(col => (
                  <ColonneRow
                    key={col.id}
                    col={col}
                    isSuperAdmin={isSuperAdmin}
                    onEdit={() => { setEditingCol(col); setShowForm(true) }}
                    onDelete={() => handleDeleteCol(col)}
                    onToggle={() => {}}
                    locked
                  />
                ))}
              </div>
            </div>
          )}

          {/* Colonnes optionnelles */}
          {colsOptionnelles.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700">
                <Eye className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-semibold text-gray-600 dark:text-gray-300">
                  Colonnes optionnelles ({colsOptionnelles.length})
                  {!isSuperAdmin && <span className="font-normal text-gray-400 ml-1">— activez/desactivez selon vos besoins</span>}
                </span>
              </div>
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {colsOptionnelles.map(col => (
                  <ColonneRow
                    key={col.id}
                    col={col}
                    isSuperAdmin={isSuperAdmin}
                    onEdit={() => { setEditingCol(col); setShowForm(true) }}
                    onDelete={() => handleDeleteCol(col)}
                    onToggle={() => handleToggleCol(col)}
                    locked={false}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── ColonneRow ────────────────────────────────────────────────
function ColonneRow({ col, isSuperAdmin, onEdit, onDelete, onToggle, locked }) {
  return (
    <div className={`flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors
      ${!col.actif ? 'opacity-50' : ''}
      ${!col.visible_client && isSuperAdmin ? 'italic' : ''}`}
    >
      {/* Toggle client */}
      {!isSuperAdmin && (
        <button
          onClick={onToggle}
          disabled={locked}
          className={`flex-shrink-0 transition-colors ${locked ? 'cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <div className={`w-9 h-5 rounded-full relative transition-colors
            ${locked ? 'bg-red-400' : col.inclus ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'}`}>
            <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform
              ${locked ? 'right-0.5' : col.inclus ? 'right-0.5' : 'left-0.5'}`} />
          </div>
        </button>
      )}

      {/* Type badge */}
      <span className={`flex-shrink-0 text-xs px-1.5 py-0.5 rounded font-mono font-medium ${typeColor(col.type_donnee)}`}>
        {col.type_donnee}{col.longueur ? `(${col.longueur})` : ''}
      </span>

      {/* Nom */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm text-gray-800 dark:text-gray-200 truncate">
            {col.nom_colonne}
          </span>
          {locked && <Lock className="w-3 h-3 text-red-400 flex-shrink-0" />}
          {!col.visible_client && isSuperAdmin && (
            <span className="text-xs text-gray-400 flex items-center gap-0.5">
              <EyeOff className="w-3 h-3" /> interne
            </span>
          )}
          {col.alias && !isSuperAdmin && (
            <span className="text-xs text-blue-500 italic">"{col.alias}"</span>
          )}
        </div>
        {col.description && (
          <p className="text-xs text-gray-400 dark:text-gray-500 truncate mt-0.5">{col.description}</p>
        )}
      </div>

      {/* Valeur defaut */}
      {col.valeur_defaut && (
        <span className="text-xs text-gray-400 font-mono hidden sm:inline">
          def:{col.valeur_defaut}
        </span>
      )}

      {/* Actions superadmin */}
      {isSuperAdmin && (
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={onEdit}
            className="p-1.5 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onDelete}
            className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
