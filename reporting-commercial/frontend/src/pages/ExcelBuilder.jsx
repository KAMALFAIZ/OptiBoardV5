import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import {
  Plus, Save, Trash2, Eye, FileSpreadsheet, GripVertical,
  ChevronDown, ChevronRight, Loader2, X, Download, ExternalLink,
  Settings, Table2, RefreshCw, AlertCircle, CheckCircle2
} from 'lucide-react'
import {
  getExcelBuilders,
  getExcelBuilder,
  createExcelBuilder,
  updateExcelBuilder,
  deleteExcelBuilder,
  exportExcelBuilder,
} from '../services/api'

const MONTHS = ['janv', 'févr', 'mars', 'avr', 'mai', 'juin', 'juil', 'août', 'sept', 'oct', 'nov', 'déc']

const YEARS = Array.from({ length: 7 }, (_, i) => 2020 + i)

const ROW_TYPES = [
  { value: 'data', label: 'Donnée' },
  { value: 'total', label: 'Total' },
  { value: 'formula', label: 'Formule' },
]

const AGGREGATES = [
  { value: 'SUM', label: 'Somme (SUM)' },
  { value: 'COUNT', label: 'Compte (COUNT)' },
  { value: 'AVG', label: 'Moyenne (AVG)' },
]

const SECTION_COLORS = [
  '#dbeafe', '#dcfce7', '#fef9c3', '#fce7f3', '#ede9fe',
  '#ffedd5', '#f1f5f9', '#fef2f2', '#d1fae5', '#e0f2fe',
]

function emptyConfig() {
  return {
    title: '',
    year: new Date().getFullYear(),
    months: MONTHS,
    sections: [],
  }
}

function emptySection() {
  return {
    id: crypto.randomUUID(),
    label: 'Nouvelle section',
    color: SECTION_COLORS[0],
    rows: [],
  }
}

function emptyRow() {
  return {
    id: crypto.randomUUID(),
    label: 'Nouvelle ligne',
    type: 'data',
    source_table: '',
    aggregate: 'SUM',
    filters: {},
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function hexToRgba(hex, alpha = 0.3) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  if (!result) return `rgba(0,0,0,${alpha})`
  return `rgba(${parseInt(result[1], 16)},${parseInt(result[2], 16)},${parseInt(result[3], 16)},${alpha})`
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Alert({ type, message, onClose }) {
  const styles = type === 'error'
    ? 'bg-red-50 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-800 dark:text-red-200'
    : 'bg-green-50 dark:bg-green-900/30 border-green-300 dark:border-green-700 text-green-800 dark:text-green-200'
  const Icon = type === 'error' ? AlertCircle : CheckCircle2
  return (
    <div className={`flex items-center gap-2 px-4 py-3 rounded-lg border text-sm ${styles}`}>
      <Icon size={16} className="shrink-0" />
      <span className="flex-1">{message}</span>
      {onClose && (
        <button onClick={onClose} className="shrink-0 opacity-60 hover:opacity-100">
          <X size={14} />
        </button>
      )}
    </div>
  )
}

function BuilderCard({ builder, isSelected, onSelect, onDelete }) {
  return (
    <div
      onClick={() => onSelect(builder.id)}
      className={`group relative cursor-pointer rounded-xl border px-4 py-3 transition-all ${
        isSelected
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-sm'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-sm'
      }`}
    >
      <div className="flex items-start gap-2">
        <FileSpreadsheet size={16} className={`mt-0.5 shrink-0 ${isSelected ? 'text-blue-500' : 'text-gray-400'}`} />
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium truncate ${isSelected ? 'text-blue-700 dark:text-blue-300' : 'text-gray-800 dark:text-gray-200'}`}>
            {builder.name || 'Sans titre'}
          </p>
          {builder.description && (
            <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">{builder.description}</p>
          )}
        </div>
        <button
          onClick={e => { e.stopPropagation(); onDelete(builder.id) }}
          className="shrink-0 opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 transition-opacity"
          title="Supprimer"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}

function RowEditor({ row, onChange, onDelete }) {
  return (
    <div className="flex flex-col gap-2 bg-gray-50 dark:bg-gray-900/40 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2">
        <GripVertical size={14} className="text-gray-300 dark:text-gray-600 shrink-0 cursor-grab" />
        <input
          type="text"
          value={row.label}
          onChange={e => onChange({ ...row, label: e.target.value })}
          placeholder="Libellé de la ligne"
          className="flex-1 px-2 py-1 text-sm rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
        <select
          value={row.type}
          onChange={e => onChange({ ...row, type: e.target.value })}
          className="px-2 py-1 text-xs rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-400"
        >
          {ROW_TYPES.map(t => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        <button onClick={onDelete} className="text-red-400 hover:text-red-600 shrink-0" title="Supprimer la ligne">
          <X size={14} />
        </button>
      </div>
      {row.type === 'data' && (
        <div className="flex items-center gap-2 pl-5">
          <input
            type="text"
            value={row.source_table || ''}
            onChange={e => onChange({ ...row, source_table: e.target.value })}
            placeholder="Table source (ex: ventes, charges...)"
            className="flex-1 px-2 py-1 text-xs rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          <select
            value={row.aggregate || 'SUM'}
            onChange={e => onChange({ ...row, aggregate: e.target.value })}
            className="px-2 py-1 text-xs rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-400"
          >
            {AGGREGATES.map(a => (
              <option key={a.value} value={a.value}>{a.label}</option>
            ))}
          </select>
        </div>
      )}
      {row.type === 'formula' && (
        <div className="pl-5">
          <input
            type="text"
            value={row.formula || ''}
            onChange={e => onChange({ ...row, formula: e.target.value })}
            placeholder="Formule (ex: [Ligne1] + [Ligne2])"
            className="w-full px-2 py-1 text-xs rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
        </div>
      )}
      {row.type === 'total' && (
        <div className="pl-5">
          <input
            type="color"
            value={row.color || '#1d4ed8'}
            onChange={e => onChange({ ...row, color: e.target.value })}
            title="Couleur du total"
            className="h-7 w-16 rounded border border-gray-200 dark:border-gray-600 cursor-pointer"
          />
        </div>
      )}
    </div>
  )
}

function SectionEditor({ section, onChange, onDelete, sectionIndex }) {
  const [collapsed, setCollapsed] = useState(false)

  const updateRow = (rowIndex, updatedRow) => {
    const newRows = section.rows.map((r, i) => i === rowIndex ? updatedRow : r)
    onChange({ ...section, rows: newRows })
  }

  const deleteRow = (rowIndex) => {
    const newRows = section.rows.filter((_, i) => i !== rowIndex)
    onChange({ ...section, rows: newRows })
  }

  const addRow = () => {
    onChange({ ...section, rows: [...section.rows, emptyRow()] })
  }

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Section header */}
      <div
        className="flex items-center gap-2 px-4 py-3"
        style={{ backgroundColor: section.color || '#f1f5f9' }}
      >
        <GripVertical size={14} className="text-gray-400 shrink-0 cursor-grab" />
        <button
          onClick={() => setCollapsed(c => !c)}
          className="text-gray-500 hover:text-gray-700 shrink-0"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
        </button>
        <input
          type="text"
          value={section.label}
          onChange={e => onChange({ ...section, label: e.target.value })}
          placeholder="Libellé de la section"
          className="flex-1 bg-transparent text-sm font-semibold text-gray-800 placeholder-gray-400 focus:outline-none"
        />
        <div className="flex items-center gap-2 shrink-0">
          <label className="text-xs text-gray-600 font-medium">Couleur :</label>
          <input
            type="color"
            value={section.color || '#dbeafe'}
            onChange={e => onChange({ ...section, color: e.target.value })}
            className="h-6 w-10 rounded border border-gray-300 cursor-pointer"
            title="Couleur de la section"
          />
          <button
            onClick={onDelete}
            className="text-red-400 hover:text-red-600 ml-1"
            title="Supprimer la section"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Rows */}
      {!collapsed && (
        <div className="bg-white dark:bg-gray-800 p-3 flex flex-col gap-2">
          {section.rows.length === 0 && (
            <p className="text-xs text-gray-400 dark:text-gray-500 italic text-center py-2">
              Aucune ligne — cliquez sur "Ajouter Ligne" pour commencer.
            </p>
          )}
          {section.rows.map((row, rowIndex) => (
            <RowEditor
              key={row.id}
              row={row}
              onChange={updated => updateRow(rowIndex, updated)}
              onDelete={() => deleteRow(rowIndex)}
            />
          ))}
          <button
            onClick={addRow}
            className="flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 mt-1 w-fit"
          >
            <Plus size={13} />
            Ajouter Ligne
          </button>
        </div>
      )}
    </div>
  )
}

function PreviewTab({ config }) {
  const months = config.months || MONTHS

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
      <table className="min-w-full text-xs border-collapse">
        <thead>
          <tr className="bg-gray-100 dark:bg-gray-800">
            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700 w-56">
              {config.title || 'Rapport'} — {config.year || new Date().getFullYear()}
            </th>
            {months.map(m => (
              <th
                key={m}
                className="px-3 py-2 text-center font-semibold text-gray-600 dark:text-gray-400 border-b border-l border-gray-200 dark:border-gray-700 uppercase tracking-wide"
              >
                {m}
              </th>
            ))}
            <th className="px-3 py-2 text-center font-semibold text-gray-700 dark:text-gray-300 border-b border-l border-gray-200 dark:border-gray-700 bg-gray-200 dark:bg-gray-700">
              TOTAL
            </th>
          </tr>
        </thead>
        <tbody>
          {(!config.sections || config.sections.length === 0) && (
            <tr>
              <td
                colSpan={months.length + 2}
                className="px-4 py-8 text-center text-gray-400 dark:text-gray-500 italic"
              >
                Aucune section configurée.
              </td>
            </tr>
          )}
          {(config.sections || []).map(section => (
            <>
              {/* Section header row */}
              <tr key={`section-${section.id}`}>
                <td
                  colSpan={months.length + 2}
                  className="px-4 py-2 font-bold text-gray-800 text-xs uppercase tracking-widest border-t border-gray-200 dark:border-gray-700"
                  style={{ backgroundColor: section.color || '#f1f5f9' }}
                >
                  {section.label || 'Section'}
                </td>
              </tr>
              {/* Data rows */}
              {(section.rows || []).map(row => {
                const isTotal = row.type === 'total'
                const isFormula = row.type === 'formula'
                const bgStyle = isTotal
                  ? { backgroundColor: row.color ? hexToRgba(row.color, 0.12) : '#eff6ff' }
                  : {}
                return (
                  <tr
                    key={`row-${row.id}`}
                    className="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                    style={bgStyle}
                  >
                    <td
                      className={`px-4 py-1.5 border-r border-gray-100 dark:border-gray-800 ${
                        isTotal
                          ? 'font-bold text-gray-800 dark:text-gray-200'
                          : isFormula
                          ? 'italic text-gray-600 dark:text-gray-400'
                          : 'text-gray-700 dark:text-gray-300'
                      }`}
                    >
                      {row.label || '—'}
                      {row.type !== 'data' && (
                        <span className="ml-2 text-gray-400 dark:text-gray-500 font-normal not-italic text-[10px]">
                          [{ROW_TYPES.find(t => t.value === row.type)?.label}]
                        </span>
                      )}
                    </td>
                    {months.map(m => (
                      <td
                        key={m}
                        className="px-3 py-1.5 text-right text-gray-400 dark:text-gray-600 border-l border-gray-100 dark:border-gray-800"
                      >
                        —
                      </td>
                    ))}
                    <td className="px-3 py-1.5 text-right text-gray-400 dark:text-gray-600 border-l border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 font-semibold">
                      —
                    </td>
                  </tr>
                )
              })}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function ExcelBuilder() {
  const { user } = useAuth()
  const { darkMode } = useTheme()

  // ── State ──────────────────────────────────────────────────────────────────
  const [builders, setBuilders] = useState([])
  const [selectedBuilder, setSelectedBuilder] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [exporting, setExporting] = useState(false)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [config, setConfig] = useState(emptyConfig())
  const [activeTab, setActiveTab] = useState('config')

  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // ── Load builders list ─────────────────────────────────────────────────────
  const loadBuilders = useCallback(async () => {
    try {
      setLoading(true)
      const res = await getExcelBuilders(user?.id)
      setBuilders(res.data || [])
    } catch (err) {
      setError('Impossible de charger les builders Excel.')
    } finally {
      setLoading(false)
    }
  }, [user?.id])

  useEffect(() => {
    loadBuilders()
  }, [loadBuilders])

  // ── Auto-dismiss messages ──────────────────────────────────────────────────
  useEffect(() => {
    if (!success) return
    const t = setTimeout(() => setSuccess(null), 4000)
    return () => clearTimeout(t)
  }, [success])

  useEffect(() => {
    if (!error) return
    const t = setTimeout(() => setError(null), 6000)
    return () => clearTimeout(t)
  }, [error])

  // ── Select a builder ──────────────────────────────────────────────────────
  const handleSelectBuilder = useCallback(async (id) => {
    try {
      setLoading(true)
      const res = await getExcelBuilder(id)
      const b = res.data
      setSelectedBuilder(b)
      setName(b.name || '')
      setDescription(b.description || '')
      const rawConfig = typeof b.config === 'string' ? JSON.parse(b.config) : (b.config || emptyConfig())
      setConfig({
        ...emptyConfig(),
        ...rawConfig,
      })
      setActiveTab('config')
    } catch (err) {
      setError('Impossible de charger ce builder.')
    } finally {
      setLoading(false)
    }
  }, [])

  // ── New builder ────────────────────────────────────────────────────────────
  const handleNew = useCallback(() => {
    setSelectedBuilder(null)
    setName('')
    setDescription('')
    setConfig(emptyConfig())
    setActiveTab('config')
    setError(null)
    setSuccess(null)
  }, [])

  // ── Delete builder ─────────────────────────────────────────────────────────
  const handleDelete = useCallback(async (id) => {
    if (!window.confirm('Supprimer ce builder Excel ?')) return
    try {
      await deleteExcelBuilder(id)
      if (selectedBuilder?.id === id) handleNew()
      await loadBuilders()
      setSuccess('Builder supprimé.')
    } catch (err) {
      setError('Erreur lors de la suppression.')
    }
  }, [selectedBuilder, handleNew, loadBuilders])

  // ── Save builder ───────────────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (!name.trim()) {
      setError('Veuillez saisir un nom pour le builder.')
      return
    }
    try {
      setSaving(true)
      setError(null)
      const payload = {
        name: name.trim(),
        description: description.trim(),
        config,
        user_id: user?.id,
      }
      let res
      if (selectedBuilder?.id) {
        res = await updateExcelBuilder(selectedBuilder.id, payload)
        setSelectedBuilder(res.data)
        setSuccess('Builder mis à jour avec succès.')
      } else {
        res = await createExcelBuilder(payload)
        setSelectedBuilder(res.data)
        setSuccess('Builder créé avec succès.')
      }
      await loadBuilders()
    } catch (err) {
      setError('Erreur lors de la sauvegarde.')
    } finally {
      setSaving(false)
    }
  }, [name, description, config, user?.id, selectedBuilder, loadBuilders])

  // ── Export ─────────────────────────────────────────────────────────────────
  const handleExport = useCallback(async () => {
    if (!selectedBuilder?.id) {
      setError('Veuillez d\'abord sauvegarder le builder avant d\'exporter.')
      return
    }
    try {
      setExporting(true)
      setError(null)
      const blob = await exportExcelBuilder(selectedBuilder.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `rapport_${(name || 'export').replace(/\s+/g, '_')}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      setSuccess('Export Excel déclenché.')
    } catch (err) {
      setError('Erreur lors de l\'export Excel.')
    } finally {
      setExporting(false)
    }
  }, [selectedBuilder, name])

  // ── Config helpers ─────────────────────────────────────────────────────────
  const addSection = useCallback(() => {
    setConfig(c => ({
      ...c,
      sections: [...(c.sections || []), emptySection()],
    }))
  }, [])

  const updateSection = useCallback((index, updated) => {
    setConfig(c => ({
      ...c,
      sections: c.sections.map((s, i) => i === index ? updated : s),
    }))
  }, [])

  const deleteSection = useCallback((index) => {
    setConfig(c => ({
      ...c,
      sections: c.sections.filter((_, i) => i !== index),
    }))
  }, [])

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className={`flex h-screen overflow-hidden ${darkMode ? 'dark' : ''}`}>

      {/* ── Left Sidebar ──────────────────────────────────────────────────── */}
      <aside className="w-80 shrink-0 flex flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Sidebar header */}
        <div className="px-4 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <FileSpreadsheet size={20} className="text-blue-500" />
              <h2 className="text-base font-bold text-gray-800 dark:text-gray-100">Excel Builder</h2>
            </div>
          </div>
          <button
            onClick={handleNew}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
          >
            <Plus size={16} />
            Nouveau Builder
          </button>
        </div>

        {/* Builders list */}
        <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
          {loading && builders.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-gray-400">
              <Loader2 size={20} className="animate-spin mr-2" />
              Chargement...
            </div>
          ) : builders.length === 0 ? (
            <p className="text-xs text-gray-400 dark:text-gray-500 italic text-center mt-8 px-4">
              Aucun builder Excel. Créez-en un avec le bouton ci-dessus.
            </p>
          ) : (
            builders.map(b => (
              <BuilderCard
                key={b.id}
                builder={b}
                isSelected={selectedBuilder?.id === b.id}
                onSelect={handleSelectBuilder}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>
      </aside>

      {/* ── Right Main Panel ──────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-950">

        {/* Top bar */}
        <div className="px-6 py-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex items-center gap-4">
          <div className="flex-1 min-w-0 flex flex-col gap-1">
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Nom du builder..."
              className="text-xl font-bold bg-transparent text-gray-800 dark:text-gray-100 placeholder-gray-300 dark:placeholder-gray-600 focus:outline-none border-b border-transparent focus:border-blue-400 transition-colors pb-0.5"
            />
            <input
              type="text"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Description (optionnel)..."
              className="text-sm bg-transparent text-gray-500 dark:text-gray-400 placeholder-gray-300 dark:placeholder-gray-600 focus:outline-none border-b border-transparent focus:border-blue-300 transition-colors"
            />
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            {selectedBuilder?.id && (
              <a
                href={`/excel-builder-view/${selectedBuilder.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 text-sm text-gray-600 dark:text-gray-300 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                title="Visualiser"
              >
                <ExternalLink size={15} />
                Visualiser
              </a>
            )}
            <button
              onClick={handleExport}
              disabled={exporting || !selectedBuilder?.id}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 text-sm text-gray-600 dark:text-gray-300 hover:border-emerald-400 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              title="Exporter en Excel"
            >
              {exporting ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
              Exporter Excel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
            >
              {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
              Sauvegarder
            </button>
          </div>
        </div>

        {/* Messages */}
        {(error || success) && (
          <div className="px-6 pt-3">
            {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
            {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} />}
          </div>
        )}

        {/* Tabs */}
        <div className="px-6 pt-4 flex items-center gap-1 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
          <button
            onClick={() => setActiveTab('config')}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'config'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
          >
            <Settings size={15} />
            Configuration
          </button>
          <button
            onClick={() => setActiveTab('apercu')}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'apercu'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
          >
            <Table2 size={15} />
            Aperçu
          </button>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">

          {/* ── Configuration tab ──────────────────────────────────────────── */}
          {activeTab === 'config' && (
            <div className="p-6 flex flex-col gap-6 max-w-5xl">

              {/* Global settings */}
              <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2">
                  <Settings size={15} />
                  Paramètres généraux
                </h3>
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Titre du rapport</label>
                    <input
                      type="text"
                      value={config.title || ''}
                      onChange={e => setConfig(c => ({ ...c, title: e.target.value }))}
                      placeholder="Ex: Produits et Charges 2024"
                      className="px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-400 w-72"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Année</label>
                    <select
                      value={config.year || new Date().getFullYear()}
                      onChange={e => setConfig(c => ({ ...c, year: Number(e.target.value) }))}
                      className="px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
                    >
                      {YEARS.map(y => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-col gap-1 flex-1 min-w-60">
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                      Colonnes mois ({(config.months || MONTHS).length} sélectionnées)
                    </label>
                    <div className="flex flex-wrap gap-1">
                      {MONTHS.map(m => {
                        const active = (config.months || MONTHS).includes(m)
                        return (
                          <button
                            key={m}
                            onClick={() => {
                              const current = config.months || MONTHS
                              setConfig(c => ({
                                ...c,
                                months: active
                                  ? current.filter(x => x !== m)
                                  : [...current, m],
                              }))
                            }}
                            className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                              active
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                            }`}
                          >
                            {m}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                </div>
              </div>

              {/* Sections */}
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                    <Eye size={15} />
                    Sections
                    <span className="ml-1 text-xs font-normal text-gray-400">
                      ({(config.sections || []).length})
                    </span>
                  </h3>
                  <button
                    onClick={addSection}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50 text-xs font-medium transition-colors border border-blue-200 dark:border-blue-700"
                  >
                    <Plus size={13} />
                    Ajouter Section
                  </button>
                </div>

                {(config.sections || []).length === 0 && (
                  <div className="rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700 py-12 text-center">
                    <FileSpreadsheet size={32} className="mx-auto mb-3 text-gray-300 dark:text-gray-600" />
                    <p className="text-sm text-gray-400 dark:text-gray-500">
                      Aucune section. Cliquez sur "Ajouter Section" pour structurer votre rapport.
                    </p>
                  </div>
                )}

                {(config.sections || []).map((section, index) => (
                  <SectionEditor
                    key={section.id}
                    section={section}
                    sectionIndex={index}
                    onChange={updated => updateSection(index, updated)}
                    onDelete={() => deleteSection(index)}
                  />
                ))}

                {(config.sections || []).length > 0 && (
                  <button
                    onClick={addSection}
                    className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700 text-sm text-gray-400 dark:text-gray-500 hover:border-blue-300 dark:hover:border-blue-600 hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
                  >
                    <Plus size={15} />
                    Ajouter une section
                  </button>
                )}
              </div>
            </div>
          )}

          {/* ── Aperçu tab ─────────────────────────────────────────────────── */}
          {activeTab === 'apercu' && (
            <div className="p-6 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                  <Table2 size={15} />
                  Aperçu de la structure
                </h3>
                <p className="text-xs text-gray-400 dark:text-gray-500 italic">
                  Les données réelles s'afficheront après exécution.
                </p>
              </div>
              <PreviewTab config={config} />

              {/* Summary stats */}
              <div className="flex gap-4 mt-2">
                <div className="flex-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 text-center">
                  <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {(config.sections || []).length}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Sections</p>
                </div>
                <div className="flex-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 text-center">
                  <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                    {(config.sections || []).reduce((acc, s) => acc + (s.rows || []).length, 0)}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Lignes au total</p>
                </div>
                <div className="flex-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 text-center">
                  <p className="text-2xl font-bold text-violet-600 dark:text-violet-400">
                    {(config.months || MONTHS).length}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Colonnes mois</p>
                </div>
                <div className="flex-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 text-center">
                  <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                    {config.year || new Date().getFullYear()}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Année</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Bottom action bar */}
        <div className="px-6 py-3 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="text-xs text-gray-400 dark:text-gray-500">
            {selectedBuilder?.id
              ? `ID : ${selectedBuilder.id}`
              : 'Nouveau builder — non sauvegardé'}
          </div>
          <div className="flex items-center gap-2">
            {selectedBuilder?.id && (
              <a
                href={`/excel-builder-view/${selectedBuilder.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
              >
                <ExternalLink size={13} />
                Visualiser
              </a>
            )}
            <button
              onClick={handleExport}
              disabled={exporting || !selectedBuilder?.id}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-emerald-400 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {exporting ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
              Exporter Excel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-xs font-medium transition-colors"
            >
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              Sauvegarder
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
