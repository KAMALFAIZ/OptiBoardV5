import { useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import {
  getPivotsV2, getPivotV2, createPivotV2, updatePivotV2, deletePivotV2,
  previewPivotV2, getPivotV2Fields, getUnifiedDataSourceFields
} from '../services/api'
import DataSourceSelector from '../components/DataSourceSelector'
import { FieldList, DropZone, FormatRuleEditor, PivotTable } from '../components/PivotV2'
import {
  ArrowLeft, Plus, Trash2, Save, Play, Eye, Loader2,
  Settings2, Rows3, Columns3, BarChart3, Palette,
  ToggleLeft, ToggleRight, Globe, Lock, Search, X, Sparkles,
  TrendingUp, BookOpen, Users, Landmark, LayoutGrid
} from 'lucide-react'
import AIBuilderGenerator from '../components/ai/AIBuilderGenerator'

const TABS = [
  { id: 'general', label: 'General', icon: Settings2 },
  { id: 'config', label: 'Axes & Valeurs', icon: Rows3 },
  { id: 'formatting', label: 'Formatage', icon: Palette },
  { id: 'preview', label: 'Apercu', icon: Eye },
]

const COMPARISON_MODES = [
  { value: '', label: 'Desactive' },
  { value: 'annee', label: 'Annee N vs N-1' },
  { value: 'mois', label: 'Mois M vs M-1' },
  { value: 'trimestre', label: 'Trimestre Q vs Q-1' },
]

const APPLICATION_OPTIONS = [
  { value: '', label: '-- Aucune application --' },
  { value: 'commercial', label: 'Gestion Commerciale' },
  { value: 'comptabilite', label: 'Comptabilité' },
  { value: 'paie', label: 'Paie' },
  { value: 'tresorerie', label: 'Gestion Trésorerie' },
]

const APP_DOT = {
  commercial:   'bg-blue-500',
  comptabilite: 'bg-emerald-500',
  paie:         'bg-orange-400',
  tresorerie:   'bg-violet-500',
}
const APP_TEXT = {
  commercial:   'text-blue-600 dark:text-blue-400',
  comptabilite: 'text-emerald-600 dark:text-emerald-400',
  paie:         'text-orange-500 dark:text-orange-400',
  tresorerie:   'text-violet-600 dark:text-violet-400',
}
const APP_BG = {
  commercial:   'bg-blue-100 dark:bg-blue-900/30',
  comptabilite: 'bg-emerald-100 dark:bg-emerald-900/30',
  paie:         'bg-orange-100 dark:bg-orange-900/30',
  tresorerie:   'bg-violet-100 dark:bg-violet-900/30',
}
const APP_LABEL = {
  commercial: 'Commerciale', comptabilite: 'Comptabilité',
  paie: 'Paie', tresorerie: 'Trésorerie',
}


// Generateur d'ID unique pour les champs dans les zones
let _uidCounter = 0
const genUid = () => `_f${++_uidCounter}_${Date.now()}`
const ensureUids = (items) => (items || []).map(f => f._uid ? f : { ...f, _uid: genUid() })
const stripUids = (items) => (items || []).map(({ _uid, ...rest }) => rest)

// Parse JSON string ou retourne le tableau directement
const safeArray = (val) => {
  if (Array.isArray(val)) return val
  if (typeof val === 'string') {
    try { const parsed = JSON.parse(val); return Array.isArray(parsed) ? parsed : [] }
    catch { return [] }
  }
  return []
}

export default function PivotBuilderV2() {
  const { user } = useAuth()
  const { filters: globalFilters } = useGlobalFilters()

  // Liste des pivots
  const [pivots, setPivots] = useState([])
  const [selectedPivotId, setSelectedPivotId] = useState(null)
  const [listLoading, setListLoading] = useState(true)
  const [sidebarSearch, setSidebarSearch] = useState('')
  const [sidebarAppFilter, setSidebarAppFilter] = useState('')
  const [sidebarWidth, setSidebarWidth] = useState(256)
  const sidebarDragging = useRef(false)

  const handleSidebarResizeStart = useCallback((e) => {
    e.preventDefault()
    sidebarDragging.current = true
    const startX = e.clientX
    const startWidth = sidebarWidth
    const onMouseMove = (e) => {
      if (!sidebarDragging.current) return
      setSidebarWidth(Math.min(Math.max(startWidth + (e.clientX - startX), 160), 520))
    }
    const onMouseUp = () => {
      sidebarDragging.current = false
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }, [sidebarWidth])

  // Config du pivot actif
  const [config, setConfig] = useState({
    nom: '',
    description: '',
    data_source_id: null,
    data_source_code: null,
    drilldown_data_source_code: null,
    rows_config: [],
    columns_config: [],
    filters_config: [],
    values_config: [],
    show_grand_totals: true,
    show_subtotals: true,
    show_row_percent: false,
    show_col_percent: false,
    show_total_percent: false,
    comparison_mode: '',
    formatting_rules: [],
    source_params: [],
    is_public: false,
    application: '',
    grand_total_position: 'bottom',
    subtotal_position: 'bottom',
    show_summary_row: false,
    summary_functions: [],
    window_calculations: [],
  })

  // Champs disponibles
  const [availableFields, setAvailableFields] = useState([])
  const [fieldsLoading, setFieldsLoading] = useState(false)

  // UI state
  const [activeTab, setActiveTab] = useState('general')
  const [saving, setSaving] = useState(false)
  const [previewData, setPreviewData] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dirty, setDirty] = useState(false)
  const [showAIGenerator, setShowAIGenerator] = useState(false)

  // Charger la liste des pivots
  useEffect(() => {
    loadPivots()
  }, [])

  const loadPivots = async () => {
    setListLoading(true)
    try {
      const res = await getPivotsV2(user?.id)
      setPivots(res.data?.data || [])
    } catch (err) {
      console.error('Erreur chargement pivots:', err)
    } finally {
      setListLoading(false)
    }
  }

  // Affecter rapidement une application depuis la sidebar
  const handleQuickSetApp = async (e, pivotId, appValue) => {
    e.stopPropagation()
    try {
      await updatePivotV2(pivotId, { application: appValue })
      setPivots(prev => prev.map(p => p.id === pivotId ? { ...p, application: appValue } : p))
      if (selectedPivotId === pivotId) setConfig(prev => ({ ...prev, application: appValue }))
    } catch (err) {
      console.error('Erreur affectation application:', err)
    }
  }

  // Charger un pivot specifique
  const loadPivot = async (id) => {
    try {
      const res = await getPivotV2(id)
      if (res.data?.success) {
        const data = res.data.data
        setConfig({
          nom: data.nom || '',
          description: data.description || '',
          data_source_id: data.data_source_id,
          data_source_code: data.data_source_code,
          drilldown_data_source_code: data.drilldown_data_source_code || null,
          rows_config: ensureUids(data.rows_config),
          columns_config: ensureUids(data.columns_config),
          filters_config: ensureUids(data.filters_config),
          values_config: ensureUids(data.values_config),
          show_grand_totals: !!data.show_grand_totals,
          show_subtotals: !!data.show_subtotals,
          show_row_percent: !!data.show_row_percent,
          show_col_percent: !!data.show_col_percent,
          show_total_percent: !!data.show_total_percent,
          comparison_mode: data.comparison_mode || '',
          formatting_rules: data.formatting_rules || [],
          source_params: data.source_params || [],
          is_public: !!data.is_public,
          application: data.application || '',
          grand_total_position: data.grand_total_position || 'bottom',
          subtotal_position: data.subtotal_position || 'bottom',
          show_summary_row: !!data.show_summary_row,
          summary_functions: safeArray(data.summary_functions),
          window_calculations: safeArray(data.window_calculations),
        })
        setSelectedPivotId(id)
        setDirty(false)
        setPreviewData(null)

        // Charger les champs de la source
        if (data.data_source_code || data.data_source_id) {
          loadFields(data.data_source_code || data.data_source_id)
        }
      }
    } catch (err) {
      console.error('Erreur chargement pivot:', err)
      setError('Erreur de chargement du pivot')
    }
  }

  // Charger les champs d'une datasource
  const loadFields = async (identifier) => {
    setFieldsLoading(true)
    try {
      const res = await getUnifiedDataSourceFields(identifier)
      if (res.data?.success) {
        setAvailableFields(res.data.fields || [])
      } else if (res.data?.fields) {
        setAvailableFields(res.data.fields)
      }
    } catch (err) {
      // Essayer avec l'API V2
      try {
        const res2 = await getPivotV2Fields(identifier)
        setAvailableFields(res2.data?.fields || [])
      } catch (err2) {
        console.error('Erreur chargement champs:', err2)
        setAvailableFields([])
      }
    } finally {
      setFieldsLoading(false)
    }
  }

  // Handlers de modification
  const updateConfig = useCallback((key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }))
    setDirty(true)
  }, [])

  // DataSource change
  const handleSourceChange = (source) => {
    if (source) {
      updateConfig('data_source_code', source.code || null)
      updateConfig('data_source_id', source.id || null)
      loadFields(source.code || source.id)
    } else {
      updateConfig('data_source_code', null)
      updateConfig('data_source_id', null)
      setAvailableFields([])
    }
  }

  // Drag-drop handlers
  const handleFieldDrop = (fieldData, zone) => {
    const fieldType = fieldData.type || 'text'
    const newField = {
      _uid: genUid(),
      field: fieldData.field,
      label: fieldData.label || fieldData.field,
      type: fieldType,
    }

    // Pour les champs date, ajouter un regroupement par defaut
    if (fieldType === 'date') {
      newField.date_grouping = 'mois_annee'
    }

    // Si c'est pour les valeurs, ajouter les configs
    if (zone === 'values') {
      const valueField = {
        _uid: genUid(),
        field: fieldData.field,
        aggregation: 'SUM',
        label: fieldData.label || fieldData.field,
        format: fieldType === 'number' ? 'number' : 'text',
        decimals: 2,
      }
      updateConfig('values_config', [...config.values_config, valueField])
    } else {
      const configKey = `${zone}_config`
      updateConfig(configKey, [...(config[configKey] || []), newField])
    }
  }

  const handleFieldRemove = (uid, zone) => {
    const configKey = `${zone}_config`
    updateConfig(configKey, (config[configKey] || []).filter(f => f._uid !== uid))
  }

  const handleFieldReorder = (zone, fromIndex, toIndex) => {
    const configKey = `${zone}_config`
    const items = [...(config[configKey] || [])]
    const [moved] = items.splice(fromIndex, 1)
    items.splice(toIndex, 0, moved)
    updateConfig(configKey, items)
  }

  // Modifier les proprietes d'un champ (ex: date_grouping)
  const handleFieldChange = (uid, zone, changes) => {
    const configKey = `${zone}_config`
    const items = (config[configKey] || []).map(f =>
      f._uid === uid ? { ...f, ...changes } : f
    )
    updateConfig(configKey, items)
  }

  // Champs utilises (pour griser dans la liste)
  const usedFields = [
    ...config.rows_config,
    ...config.columns_config,
    ...config.filters_config,
    ...config.values_config,
  ]

  // Double-clic pour ajouter aux lignes
  const handleFieldDoubleClick = (field) => {
    handleFieldDrop(field, 'rows')
  }

  // Sauvegarder
  const handleSave = async () => {
    if (!config.nom.trim()) {
      setError('Le nom du pivot est requis')
      setActiveTab('general')
      return
    }

    setSaving(true)
    setError(null)
    try {
      const payload = {
        ...config,
        rows_config: stripUids(config.rows_config),
        columns_config: stripUids(config.columns_config),
        filters_config: stripUids(config.filters_config),
        values_config: stripUids(config.values_config),
        grand_total_position: config.grand_total_position || 'bottom',
        subtotal_position: config.subtotal_position || 'bottom',
        show_summary_row: !!config.show_summary_row,
        summary_functions: safeArray(config.summary_functions),
        window_calculations: safeArray(config.window_calculations),
        created_by: user?.id,
      }

      if (selectedPivotId) {
        await updatePivotV2(selectedPivotId, payload)
      } else {
        const res = await createPivotV2(payload)
        if (res.data?.id) {
          setSelectedPivotId(res.data.id)
        }
      }
      setDirty(false)
      await loadPivots()
    } catch (err) {
      console.error('Erreur sauvegarde:', err)
      setError('Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  // Supprimer
  const handleDelete = async (pivotId) => {
    const idToDelete = pivotId || selectedPivotId
    if (!idToDelete) return
    if (!window.confirm('Supprimer ce pivot ?')) return

    try {
      await deletePivotV2(idToDelete)
      if (idToDelete === selectedPivotId) {
        setSelectedPivotId(null)
        setConfig({ nom: '', description: '', data_source_id: null, data_source_code: null, rows_config: [], columns_config: [], filters_config: [], values_config: [], show_grand_totals: true, show_subtotals: true, show_row_percent: false, show_col_percent: false, show_total_percent: false, comparison_mode: '', formatting_rules: [], source_params: [], is_public: false, application: '', grand_total_position: 'bottom', subtotal_position: 'bottom', show_summary_row: false, summary_functions: [], window_calculations: [] })
        setPreviewData(null)
      }
      await loadPivots()
    } catch (err) {
      setError('Erreur suppression')
    }
  }

  // Import depuis IA
  const handleAIImport = async (pivotData) => {
    const { sql, nom, description, rows_config, columns_config, values_config,
      filters_config, show_grand_totals, show_subtotals, comparison_mode } = pivotData

    // Créer d'abord la datasource avec le SQL généré
    let dsId = null
    if (sql) {
      try {
        const { createDataSource } = await import('../services/api')
        const dsRes = await createDataSource({
          nom: `[IA] ${nom || 'Source pivot'}`,
          type: 'query',
          description: `Générée par IA pour: ${nom}`,
          query_template: sql,
          parameters: []
        })
        dsId = dsRes.data?.id
      } catch (e) {
        console.error('Erreur création datasource IA:', e)
      }
    }

    // Remplir le formulaire avec la config générée
    setSelectedPivotId(null)
    setConfig({
      nom: nom || 'Pivot IA',
      description: description || '',
      data_source_id: dsId,
      data_source_code: null,
      rows_config: ensureUids(rows_config || []),
      columns_config: ensureUids(columns_config || []),
      values_config: ensureUids(values_config || []),
      filters_config: ensureUids(filters_config || []),
      show_grand_totals: show_grand_totals !== false,
      show_subtotals: show_subtotals !== false,
      show_row_percent: false,
      show_col_percent: false,
      show_total_percent: false,
      comparison_mode: comparison_mode || '',
      formatting_rules: [],
      source_params: [],
      is_public: false,
      grand_total_position: 'bottom',
      subtotal_position: 'bottom',
      show_summary_row: false,
      summary_functions: [],
      window_calculations: [],
    })
    setDirty(true)
    setActiveTab('config')
    setShowAIGenerator(false)
  }

  // Nouveau pivot
  const handleNew = () => {
    setSelectedPivotId(null)
    setConfig({ nom: '', description: '', data_source_id: null, data_source_code: null, rows_config: [], columns_config: [], filters_config: [], values_config: [], show_grand_totals: true, show_subtotals: true, show_row_percent: false, show_col_percent: false, show_total_percent: false, comparison_mode: '', formatting_rules: [], source_params: [], is_public: false, application: '', grand_total_position: 'bottom', subtotal_position: 'bottom', show_summary_row: false, summary_functions: [], window_calculations: [] })
    setAvailableFields([])
    setPreviewData(null)
    setDirty(false)
    setActiveTab('general')
  }

  // Preview
  const handlePreview = async () => {
    if (!selectedPivotId) {
      setError('Sauvegardez le pivot avant de generer un apercu')
      return
    }
    if (!config.values_config || config.values_config.length === 0) {
      setError('Ajoutez au moins une mesure dans l\'onglet Valeurs avant de generer un apercu')
      return
    }
    if (!config.rows_config || config.rows_config.length === 0) {
      setError('Ajoutez au moins un champ en Lignes dans l\'onglet Axes')
      return
    }
    setPreviewLoading(true)
    setError(null)
    try {
      const ctx = {
        dateDebut: globalFilters?.dateDebut,
        dateFin: globalFilters?.dateFin,
        societe: globalFilters?.societe,
      }
      const res = await previewPivotV2(selectedPivotId, ctx)
      if (res.data?.success) {
        setPreviewData(res.data)
      } else {
        setError(res.data?.error || 'Erreur preview')
      }
    } catch (err) {
      setError('Erreur execution apercu')
    } finally {
      setPreviewLoading(false)
    }
  }

  return (
    <>
    <div className="flex h-full -m-3 lg:-m-4 overflow-hidden">
      {/* ── SIDEBAR ── */}
      <div className="bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 flex flex-col flex-shrink-0 relative" style={{ width: sidebarWidth }}>
        {/* Sidebar header */}
        <div className="px-4 pt-4 pb-3 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-[11px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">Pivots</h2>
            <div className="flex items-center gap-1">
              <button onClick={() => setShowAIGenerator(true)}
                className="p-1.5 rounded-lg bg-violet-50 dark:bg-violet-900/20 text-violet-600 dark:text-violet-400 hover:bg-violet-100 dark:hover:bg-violet-900/40 transition-colors" title="Générer par IA">
                <Sparkles size={13} />
              </button>
              <button onClick={handleNew}
                className="p-1.5 rounded-lg bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-900/40 transition-colors" title="Nouveau pivot">
                <Plus size={13} />
              </button>
            </div>
          </div>
          <div className="relative mb-2">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input type="text" value={sidebarSearch} onChange={(e) => setSidebarSearch(e.target.value)}
              placeholder="Rechercher..."
              className="w-full pl-8 pr-7 py-2 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-transparent dark:text-white placeholder-gray-400 outline-none transition-all" />
            {sidebarSearch && (
              <button onClick={() => setSidebarSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <select value={sidebarAppFilter} onChange={(e) => setSidebarAppFilter(e.target.value)}
            className="w-full px-2.5 py-2 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl dark:text-white focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none transition-all">
            <option value="">Toutes les applications</option>
            {APPLICATION_OPTIONS.filter(a => a.value).map(a => (
              <option key={a.value} value={a.value}>{a.label}</option>
            ))}
          </select>
        </div>

        {/* Liste */}
        <div className="flex-1 overflow-y-auto py-2 px-2">
          {listLoading ? (
            <div className="flex justify-center py-8"><Loader2 size={18} className="animate-spin text-gray-300" /></div>
          ) : pivots.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-6">Aucun pivot créé</p>
          ) : (
            <>
              {pivots
                .filter(p => (!sidebarSearch || p.nom.toLowerCase().includes(sidebarSearch.toLowerCase())) && (!sidebarAppFilter || p.application === sidebarAppFilter))
                .map(p => (
                  <div key={p.id} onClick={() => loadPivot(p.id)}
                    className={`group flex items-center gap-2 px-2 py-1.5 rounded-xl cursor-pointer transition-all duration-150 mb-0.5
                      ${selectedPivotId === p.id
                        ? 'bg-primary-50 dark:bg-primary-900/20 shadow-sm ring-1 ring-primary-200 dark:ring-primary-800'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-800/60'}`}>
                    <div className={`w-1 h-7 rounded-full flex-shrink-0 ${APP_DOT[p.application] || 'bg-gray-200 dark:bg-gray-700'}`} />
                    <div className={`flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center ${APP_BG[p.application] || 'bg-gray-100 dark:bg-gray-800'}`} title={p.application || ''}>
                      {p.application === 'commercial'   && <TrendingUp className="w-3 h-3 text-blue-600 dark:text-blue-400" strokeWidth={2.5} />}
                      {p.application === 'comptabilite' && <BookOpen   className="w-3 h-3 text-emerald-600 dark:text-emerald-400" strokeWidth={2.5} />}
                      {p.application === 'paie'         && <Users      className="w-3 h-3 text-orange-500 dark:text-orange-400" strokeWidth={2.5} />}
                      {p.application === 'tresorerie'   && <Landmark   className="w-3 h-3 text-violet-600 dark:text-violet-400" strokeWidth={2.5} />}
                      {!p.application                   && <LayoutGrid className="w-3 h-3 text-gray-300 dark:text-gray-600" strokeWidth={2} />}
                    </div>
                    <span className={`flex-1 truncate text-[11px] font-semibold ${selectedPivotId === p.id ? 'text-primary-700 dark:text-primary-400' : 'text-gray-800 dark:text-gray-200'}`}>
                      {p.nom}
                    </span>
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(p.id) }}
                      className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all flex-shrink-0">
                      <Trash2 className="w-3 h-3 text-red-400" />
                    </button>
                  </div>
                ))}
              {(sidebarSearch || sidebarAppFilter) && pivots.filter(p => (!sidebarSearch || p.nom.toLowerCase().includes(sidebarSearch.toLowerCase())) && (!sidebarAppFilter || p.application === sidebarAppFilter)).length === 0 && (
                <p className="text-xs text-gray-400 text-center py-4">Aucun résultat</p>
              )}
            </>
          )}
        </div>
        <div onMouseDown={handleSidebarResizeStart}
          className="absolute top-0 right-0 w-1.5 h-full cursor-col-resize hover:bg-primary-400/40 active:bg-primary-500/50 transition-colors z-10" />
      </div>

      {/* ── ZONE PRINCIPALE ── */}
      <div className="flex-1 flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-950">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
              <Settings2 size={15} className="text-primary-600 dark:text-primary-400" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-gray-900 dark:text-white truncate leading-tight">
                {selectedPivotId ? (config.nom || 'Sans nom') : 'Nouveau Pivot'}
              </h1>
              {dirty && <p className="text-[10px] text-amber-500 font-medium leading-none mt-0.5">Modifications non sauvegardées</p>}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {selectedPivotId && (
              <button onClick={handleDelete}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors">
                <Trash2 size={13} />Supprimer
              </button>
            )}
            <button onClick={handleSave} disabled={saving}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 transition-colors shadow-sm">
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              Sauvegarder
            </button>
          </div>
        </div>

        {/* Onglets */}
        <div className="flex items-center gap-1 px-4 py-2 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800">
          {TABS.map(tab => {
            const TabIcon = tab.icon
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl transition-all ${
                  activeTab === tab.id
                    ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200'
                }`}>
                <TabIcon size={13} />{tab.label}
              </button>
            )
          })}
        </div>

        {/* Erreur */}
        {error && (
          <div className="mx-6 mt-3 px-4 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 rounded-lg text-sm">
            {error}
            <button onClick={() => setError(null)} className="ml-2 underline">Fermer</button>
          </div>
        )}

        {/* Contenu de l'onglet */}
        <div className={`flex-1 ${activeTab === 'config' ? 'overflow-hidden' : 'overflow-y-auto'} p-6`}>
          {/* ONGLET GENERAL */}
          {activeTab === 'general' && (
            <div className="max-w-2xl space-y-4">
              {/* Card Identité */}
              <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 p-5 space-y-4 shadow-sm">
                <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">Identité</h3>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">Nom du pivot <span className="text-red-400">*</span></label>
                  <input type="text" value={config.nom} onChange={(e) => updateConfig('nom', e.target.value)}
                    placeholder="Ex: CA par Gamme et Commercial"
                    className="w-full px-3.5 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none transition-all placeholder-gray-400" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">Description</label>
                  <textarea value={config.description} onChange={(e) => updateConfig('description', e.target.value)}
                    rows={2} placeholder="Description optionnelle..."
                    className="w-full px-3.5 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none resize-none transition-all placeholder-gray-400" />
                </div>
              </div>

              {/* Card Source */}
              <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 p-5 space-y-4 shadow-sm">
                <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">Source de données</h3>
                <DataSourceSelector value={config.data_source_code || config.data_source_id} onChange={handleSourceChange} />
                <div>
                  <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">Source drilldown (détail lignes)</label>
                  <DataSourceSelector
                    value={config.drilldown_data_source_code}
                    onChange={(src) => updateConfig('drilldown_data_source_code', src?.code || null)}
                    placeholder="Même source (agrégée par défaut)"
                  />
                </div>
              </div>

              {/* Card Paramètres */}
              <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 p-5 space-y-4 shadow-sm">
                <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">Paramètres</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">Application</label>
                    <select value={config.application} onChange={(e) => updateConfig('application', e.target.value)}
                      className="w-full px-3 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none transition-all">
                      {APPLICATION_OPTIONS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">Mode comparaison</label>
                    <select value={config.comparison_mode} onChange={(e) => updateConfig('comparison_mode', e.target.value)}
                      className="w-full px-3 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none transition-all">
                      {COMPARISON_MODES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                    </select>
                  </div>
                </div>
                <div className="flex items-center gap-3 pt-1">
                  <button onClick={() => updateConfig('is_public', !config.is_public)} className="flex-shrink-0">
                    {config.is_public ? <ToggleRight size={22} className="text-primary-500" /> : <ToggleLeft size={22} className="text-gray-300 dark:text-gray-600" />}
                  </button>
                  <div>
                    <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">{config.is_public ? 'Public' : 'Privé'}</p>
                    <p className="text-[11px] text-gray-400">{config.is_public ? 'Visible par tous les utilisateurs' : 'Visible uniquement par vous'}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ONGLET AXES & VALEURS */}
          {activeTab === 'config' && (
            <div className="flex gap-6" style={{ height: 'calc(100vh - 240px)' }}>
              {/* Liste des champs */}
              <div className="w-64 flex-shrink-0 min-w-0 flex flex-col" style={{ maxHeight: '100%' }}>
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex-shrink-0">Champs disponibles</h3>
                {fieldsLoading ? (
                  <div className="flex justify-center py-8"><Loader2 size={20} className="animate-spin text-gray-400" /></div>
                ) : (
                  <FieldList
                    fields={availableFields}
                    usedFields={usedFields}
                    onFieldDoubleClick={handleFieldDoubleClick}
                  />
                )}
              </div>

              {/* Zones de drop + Valeurs */}
              <div className="flex-1 space-y-4 overflow-y-auto pr-2">
                <DropZone
                  zone="rows"
                  title="Lignes"
                  icon={Rows3}
                  fields={config.rows_config}
                  onDrop={handleFieldDrop}
                  onRemove={handleFieldRemove}
                  onReorder={(from, to) => handleFieldReorder('rows', from, to)}
                  onFieldChange={handleFieldChange}
                  placeholder="Glisser les champs pour les lignes"
                />

                <DropZone
                  zone="columns"
                  title="Colonnes"
                  icon={Columns3}
                  fields={config.columns_config}
                  onDrop={handleFieldDrop}
                  onRemove={handleFieldRemove}
                  onReorder={(from, to) => handleFieldReorder('columns', from, to)}
                  onFieldChange={handleFieldChange}
                  placeholder="Glisser le champ pour les colonnes (1 max)"
                  maxFields={1}
                />

                <DropZone
                  zone="filters"
                  title="Filtres"
                  fields={config.filters_config}
                  onDrop={handleFieldDrop}
                  onRemove={handleFieldRemove}
                  onReorder={(from, to) => handleFieldReorder('filters', from, to)}
                  placeholder="Glisser les champs filtres"
                />

                {/* Section Valeurs / Mesures - DropZone */}
                <DropZone
                  zone="values"
                  title="Mesures (Valeurs)"
                  icon={BarChart3}
                  fields={config.values_config}
                  onDrop={handleFieldDrop}
                  onRemove={handleFieldRemove}
                  onReorder={(from, to) => handleFieldReorder('values', from, to)}
                  onFieldChange={handleFieldChange}
                  placeholder="Glisser les champs numeriques pour les mesures"
                />

                {/* Options */}
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Options</h4>

                  {[
                    { key: 'show_grand_totals', label: 'Afficher totaux generaux' },
                    { key: 'show_subtotals', label: 'Afficher sous-totaux (si multi-lignes)' },
                    { key: 'show_row_percent', label: 'Calculer % du total ligne' },
                    { key: 'show_col_percent', label: 'Calculer % du total colonne' },
                    { key: 'show_total_percent', label: 'Calculer % du total general' },
                    { key: 'show_summary_row', label: 'Afficher ligne de resume (statistiques)' },
                  ].map(opt => (
                    <label key={opt.key} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!!config[opt.key]}
                        onChange={(e) => updateConfig(opt.key, e.target.checked)}
                        className="w-4 h-4 text-blue-500 rounded border-primary-300 dark:border-primary-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{opt.label}</span>
                    </label>
                  ))}

                  {/* Fonctions de resume si ligne resume activee */}
                  {config.show_summary_row && (
                    <div className="ml-6 space-y-1">
                      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400">Fonctions de resume</label>
                      <div className="flex flex-wrap gap-2">
                        {[
                          { value: 'SUM', label: 'Somme' },
                          { value: 'AVG', label: 'Moyenne' },
                          { value: 'COUNT', label: 'Comptage' },
                          { value: 'MIN', label: 'Min' },
                          { value: 'MAX', label: 'Max' },
                          { value: 'MEDIAN', label: 'Mediane' },
                          { value: 'VAR', label: 'Variance' },
                          { value: 'STDEV', label: 'Ecart-type' },
                        ].map(fn => {
                          const isChecked = safeArray(config.summary_functions).includes(fn.value)
                          return (
                            <label key={fn.value} className="flex items-center gap-1 text-xs cursor-pointer">
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={(e) => {
                                  const prev = safeArray(config.summary_functions)
                                  const next = e.target.checked
                                    ? [...prev, fn.value]
                                    : prev.filter(v => v !== fn.value)
                                  updateConfig('summary_functions', next)
                                }}
                                className="w-3 h-3 text-blue-500 rounded border-primary-300 dark:border-primary-600"
                              />
                              <span className="text-gray-600 dark:text-gray-400">{fn.label}</span>
                            </label>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Position des totaux */}
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Position totaux generaux</label>
                      <select
                        value={config.grand_total_position || 'bottom'}
                        onChange={(e) => updateConfig('grand_total_position', e.target.value)}
                        className="w-full text-sm px-2 py-1.5 bg-white dark:bg-gray-800 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      >
                        <option value="bottom">En bas</option>
                        <option value="top">En haut</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Position sous-totaux</label>
                      <select
                        value={config.subtotal_position || 'bottom'}
                        onChange={(e) => updateConfig('subtotal_position', e.target.value)}
                        className="w-full text-sm px-2 py-1.5 bg-white dark:bg-gray-800 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      >
                        <option value="bottom">En bas du groupe</option>
                        <option value="top">En haut du groupe</option>
                      </select>
                    </div>
                  </div>

                  {/* Calculs de fenetre */}
                  <div className="pt-3 border-t border-gray-100 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Calculs avances</h4>
                      <button
                        onClick={() => {
                          const wc = [...safeArray(config.window_calculations), {
                            id: `wc_${Date.now()}`,
                            type: 'running_total',
                            source_field: config.values_config?.[0]?.field || '',
                            label: 'Nouveau calcul',
                            format: 'number',
                            decimals: 2,
                          }]
                          updateConfig('window_calculations', wc)
                        }}
                        className="text-xs px-2 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
                      >
                        + Ajouter
                      </button>
                    </div>
                    {safeArray(config.window_calculations).length === 0 && (
                      <p className="text-xs text-gray-400 italic">Aucun calcul avance. Ajoutez un cumul, difference, rang ou expression.</p>
                    )}
                    {safeArray(config.window_calculations).map((wc, wcIdx) => (
                      <div key={wc.id || wcIdx} className="flex items-start gap-2 p-2 bg-gray-50 dark:bg-gray-800/30 rounded-lg mb-2">
                        <div className="flex-1 grid grid-cols-2 gap-2">
                          <div>
                            <label className="block text-[10px] text-gray-500 mb-0.5">Type</label>
                            <select
                              value={wc.type}
                              onChange={(e) => {
                                const arr = [...safeArray(config.window_calculations)]
                                arr[wcIdx] = { ...arr[wcIdx], type: e.target.value }
                                updateConfig('window_calculations', arr)
                              }}
                              className="w-full text-xs bg-white dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-1.5 py-1 focus:ring-1 focus:ring-blue-500 outline-none"
                            >
                              <option value="running_total">Cumul progressif</option>
                              <option value="difference">Difference (N vs N-1)</option>
                              <option value="pct_difference">% Variation</option>
                              <option value="rank">Classement</option>
                              <option value="expression">Expression</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-[10px] text-gray-500 mb-0.5">Champ source</label>
                            <select
                              value={wc.source_field || ''}
                              onChange={(e) => {
                                const arr = [...safeArray(config.window_calculations)]
                                arr[wcIdx] = { ...arr[wcIdx], source_field: e.target.value }
                                updateConfig('window_calculations', arr)
                              }}
                              className="w-full text-xs bg-white dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-1.5 py-1 focus:ring-1 focus:ring-blue-500 outline-none"
                            >
                              <option value="">-- Champ --</option>
                              {(config.values_config || []).map(vf => (
                                <option key={vf.field} value={vf.field}>{vf.label || vf.field}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label className="block text-[10px] text-gray-500 mb-0.5">Label</label>
                            <input
                              type="text"
                              value={wc.label || ''}
                              onChange={(e) => {
                                const arr = [...safeArray(config.window_calculations)]
                                arr[wcIdx] = { ...arr[wcIdx], label: e.target.value }
                                updateConfig('window_calculations', arr)
                              }}
                              className="w-full text-xs bg-white dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-1.5 py-1 focus:ring-1 focus:ring-blue-500 outline-none"
                            />
                          </div>
                          {wc.type === 'expression' && (
                            <div className="col-span-2">
                              <label className="block text-[10px] text-gray-500 mb-0.5">Expression (ex: [Montant TTC] / [Quantite])</label>
                              <input
                                type="text"
                                value={wc.expression || ''}
                                onChange={(e) => {
                                  const arr = [...safeArray(config.window_calculations)]
                                  arr[wcIdx] = { ...arr[wcIdx], expression: e.target.value }
                                  updateConfig('window_calculations', arr)
                                }}
                                placeholder="[Champ1] / [Champ2]"
                                className="w-full text-xs bg-white dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-1.5 py-1 focus:ring-1 focus:ring-blue-500 outline-none font-mono"
                              />
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => {
                            const arr = safeArray(config.window_calculations).filter((_, i) => i !== wcIdx)
                            updateConfig('window_calculations', arr)
                          }}
                          className="mt-4 p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors flex-shrink-0"
                          title="Supprimer"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ONGLET FORMATAGE */}
          {activeTab === 'formatting' && (
            <div className="max-w-3xl">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Regles de formatage conditionnel</h3>
              <FormatRuleEditor
                rules={config.formatting_rules}
                valueFields={config.values_config}
                onChange={(rules) => updateConfig('formatting_rules', rules)}
              />
            </div>
          )}

          {/* ONGLET APERCU */}
          {activeTab === 'preview' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <button
                  onClick={handlePreview}
                  disabled={previewLoading || !selectedPivotId}
                  className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 transition-colors flex items-center gap-2 text-sm"
                >
                  {previewLoading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                  Executer l'apercu
                </button>
                {!selectedPivotId && (
                  <span className="text-sm text-amber-500">Sauvegardez d'abord le pivot</span>
                )}
                {previewData?.sourceRows && (
                  <span className="text-xs text-gray-500">
                    {previewData.sourceRows} lignes source (limite: 100)
                  </span>
                )}
              </div>

              {previewData && previewData.sourceRows > 0 && (!previewData.data || previewData.data.length === 0) && (
                <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-amber-700 dark:text-amber-300 text-sm">
                  {previewData.sourceRows} lignes source trouvees mais aucune donnee pivotee generee.
                  Verifiez que vous avez configure au moins un champ en <strong>Lignes</strong> (onglet Axes) et une <strong>Mesure</strong> (onglet Valeurs).
                </div>
              )}

              {previewData && previewData.data && previewData.data.length > 0 && (
                <PivotTable
                  data={previewData.data}
                  pivotColumns={previewData.pivotColumns || []}
                  rowFields={previewData.rowFields || []}
                  columnField={previewData.columnField}
                  valueFields={previewData.valueFields || []}
                  formattingRules={config.formatting_rules}
                  windowCalculations={previewData.windowCalculations || []}
                  summaryFunctions={previewData.summaryFunctions || []}
                  options={{
                    showGrandTotals: config.show_grand_totals,
                    showSubtotals: config.show_subtotals,
                    showRowPercent: config.show_row_percent,
                    showColPercent: config.show_col_percent,
                    showTotalPercent: config.show_total_percent,
                  }}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>

    {showAIGenerator && (
      <AIBuilderGenerator
        mode="pivot"
        onImport={handleAIImport}
        onClose={() => setShowAIGenerator(false)}
      />
    )}
    </>
  )
}
