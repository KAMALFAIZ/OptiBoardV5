import { useState, useEffect, useCallback, useRef } from 'react'
import useSidebarResize from '../hooks/useSidebarResize'
import { useAuth } from '../context/AuthContext'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import DataSourceSelector from '../components/DataSourceSelector'
import {
  getSpreadsheets, getSpreadsheet, createSpreadsheet, updateSpreadsheet,
  deleteSpreadsheet, getSpreadsheetData, getUnifiedDataSourceFields,
  importSpreadsheetExcel
} from '../services/api'
import {
  Plus, Trash2, Save, Play, Eye, Loader2, Search, X, Settings2,
  FileSpreadsheet, Layers, ArrowLeft, ToggleLeft, ToggleRight,
  Globe, Lock, GripVertical, ChevronDown, ChevronUp,
  TrendingUp, BookOpen, Users, Landmark, LayoutGrid, Upload
} from 'lucide-react'
import { Workbook } from '@fortune-sheet/react'
import '@fortune-sheet/react/dist/index.css'

const TABS = [
  { id: 'general', label: 'General', icon: Settings2 },
  { id: 'sheets', label: 'Feuilles', icon: Layers },
  { id: 'preview', label: 'Apercu', icon: Eye },
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
const APP_LABEL = {
  commercial: 'Commerciale', comptabilite: 'Comptabilité',
  paie: 'Paie', tresorerie: 'Trésorerie',
}

export default function SpreadsheetBuilder() {
  const { user } = useAuth()
  const { filters: globalFilters } = useGlobalFilters()

  const [spreadsheets, setSpreadsheets] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [listLoading, setListLoading] = useState(true)
  const [sidebarSearch, setSidebarSearch] = useState('')
  const [sidebarAppFilter, setSidebarAppFilter] = useState('')
  const { sidebarWidth, handleSidebarResizeStart } = useSidebarResize(256)

  const [config, setConfig] = useState({
    nom: '',
    description: '',
    sheets: [{ name: 'Feuille 1', data_source_code: null, data_source_id: null, column_mapping: [], options: {} }],
    features: {},
    application: '',
    is_public: false,
  })

  const [activeTab, setActiveTab] = useState('general')
  const [activeSheetIdx, setActiveSheetIdx] = useState(0)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [dirty, setDirty] = useState(false)
  const [previewData, setPreviewData] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [fieldsPerSheet, setFieldsPerSheet] = useState({})
  const [importing, setImporting] = useState(false)
  const fileInputRef = useRef(null)

  useEffect(() => { loadList() }, [])

  const loadList = async () => {
    setListLoading(true)
    try {
      const res = await getSpreadsheets(user?.id)
      setSpreadsheets(res.data?.data || [])
    } catch (err) {
      console.error('Erreur chargement spreadsheets:', err)
    } finally {
      setListLoading(false)
    }
  }

  const loadSpreadsheet = async (id) => {
    try {
      const res = await getSpreadsheet(id)
      if (res.data?.success) {
        const d = res.data.data
        const sheets = (d.sheets_config && d.sheets_config.length > 0)
          ? d.sheets_config
          : [{ name: 'Feuille 1', data_source_code: null, data_source_id: null, column_mapping: [], options: {} }]
        setConfig({
          nom: d.nom || '',
          description: d.description || '',
          sheets,
          features: d.features || {},
          application: d.application || '',
          is_public: !!d.is_public,
        })
        setSelectedId(id)
        setDirty(false)
        setPreviewData(null)
        setActiveSheetIdx(0)

        sheets.forEach((s, i) => {
          if (s.data_source_code || s.data_source_id) {
            loadFieldsForSheet(i, s.data_source_code || s.data_source_id)
          }
        })
      }
    } catch (err) {
      console.error('Erreur chargement spreadsheet:', err)
      setError('Erreur de chargement')
    }
  }

  const loadFieldsForSheet = async (sheetIdx, identifier) => {
    try {
      const res = await getUnifiedDataSourceFields(identifier)
      if (res.data?.success || res.data?.fields) {
        setFieldsPerSheet(prev => ({ ...prev, [sheetIdx]: res.data.fields || [] }))
      }
    } catch (err) {
      console.error('Erreur chargement champs:', err)
    }
  }

  const updateConfig = useCallback((key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }))
    setDirty(true)
  }, [])

  const updateSheet = useCallback((idx, key, value) => {
    setConfig(prev => {
      const sheets = [...prev.sheets]
      sheets[idx] = { ...sheets[idx], [key]: value }
      return { ...prev, sheets }
    })
    setDirty(true)
  }, [])

  const addSheet = () => {
    const newSheet = {
      name: `Feuille ${config.sheets.length + 1}`,
      data_source_code: null,
      data_source_id: null,
      column_mapping: [],
      options: {},
    }
    updateConfig('sheets', [...config.sheets, newSheet])
    setActiveSheetIdx(config.sheets.length)
  }

  const removeSheet = (idx) => {
    if (config.sheets.length <= 1) return
    const sheets = config.sheets.filter((_, i) => i !== idx)
    updateConfig('sheets', sheets)
    if (activeSheetIdx >= sheets.length) setActiveSheetIdx(sheets.length - 1)
  }

  const handleSourceChange = (source, sheetIdx) => {
    if (source) {
      updateSheet(sheetIdx, 'data_source_code', source.code || null)
      updateSheet(sheetIdx, 'data_source_id', source.id || null)
      loadFieldsForSheet(sheetIdx, source.code || source.id)
    } else {
      updateSheet(sheetIdx, 'data_source_code', null)
      updateSheet(sheetIdx, 'data_source_id', null)
      setFieldsPerSheet(prev => { const n = { ...prev }; delete n[sheetIdx]; return n })
    }
  }

  const handleSave = async () => {
    if (!config.nom.trim()) {
      setError('Le nom est requis')
      setActiveTab('general')
      return
    }
    if (config.sheets.length === 0) {
      setError('Au moins une feuille est requise')
      return
    }

    setSaving(true)
    setError(null)
    try {
      const payload = {
        nom: config.nom,
        description: config.description,
        sheets: config.sheets,
        features: config.features,
        application: config.application,
        is_public: config.is_public,
      }

      if (selectedId) {
        await updateSpreadsheet(selectedId, payload)
      } else {
        const res = await createSpreadsheet(payload)
        if (res.data?.id) setSelectedId(res.data.id)
      }
      setDirty(false)
      await loadList()
    } catch (err) {
      setError('Erreur sauvegarde: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    const target = id || selectedId
    if (!target) return
    if (!window.confirm('Supprimer ce classeur ?')) return
    try {
      await deleteSpreadsheet(target)
      if (target === selectedId) {
        setSelectedId(null)
        handleNew()
      }
      await loadList()
    } catch (err) {
      setError('Erreur suppression')
    }
  }

  const handleNew = () => {
    setSelectedId(null)
    setConfig({
      nom: '',
      description: '',
      sheets: [{ name: 'Feuille 1', data_source_code: null, data_source_id: null, column_mapping: [], options: {} }],
      features: {},
      application: '',
      is_public: false,
    })
    setFieldsPerSheet({})
    setPreviewData(null)
    setDirty(false)
    setActiveTab('general')
    setActiveSheetIdx(0)
  }

  const handlePreview = async () => {
    if (!selectedId) {
      setError('Sauvegardez le classeur avant de generer un apercu')
      return
    }
    const hasContent = config.sheets.some(s => s.data_source_code || s.data_source_id || (s.imported_celldata && s.imported_celldata.length > 0))
    if (!hasContent) {
      setError('Configurez au moins une source de donnees ou importez un fichier Excel')
      return
    }
    setPreviewLoading(true)
    setError(null)
    try {
      const context = {
        dateDebut: globalFilters?.dateDebut,
        dateFin: globalFilters?.dateFin,
        societe: globalFilters?.societe,
      }
      const res = await getSpreadsheetData(selectedId, context)
      if (res.data?.success) {
        const fortuneSheets = (res.data.sheets || []).map((s, i) => ({
          name: s.name || `Feuille ${i + 1}`,
          celldata: s.celldata || [],
          order: i,
          row: Math.max((s.row_count || 0) + 20, 80),
          column: Math.max((s.column_count || 0) + 10, 26),
          config: s.config || {},
          status: i === 0 ? 1 : 0,
        }))
        setPreviewData(fortuneSheets)
        setActiveTab('preview')
      }
    } catch (err) {
      setError('Erreur apercu: ' + (err.response?.data?.detail || err.message))
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleImportExcel = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setImporting(true)
    setError(null)
    try {
      const res = await importSpreadsheetExcel(file)
      if (res.data?.success) {
        const importedSheets = (res.data.sheets || []).map((s, i) => ({
          name: s.name || `Feuille ${i + 1}`,
          data_source_code: null,
          data_source_id: null,
          column_mapping: [],
          options: {},
          imported_celldata: s.celldata,
          imported_config: s.config || {},
          imported_row_count: s.row_count || 0,
          imported_column_count: s.column_count || 0,
        }))
        if (importedSheets.length > 0) {
          updateConfig('sheets', importedSheets)
          const baseName = file.name.replace(/\.(xlsx|xls)$/i, '')
          if (!config.nom) updateConfig('nom', baseName)
          setActiveSheetIdx(0)
          setFieldsPerSheet({})

          const fortuneSheets = importedSheets.map((s, i) => ({
            name: s.name,
            celldata: s.imported_celldata || [],
            order: i,
            row: Math.max((s.imported_row_count || 0) + 20, 80),
            column: Math.max((s.imported_column_count || 0) + 10, 26),
            config: s.imported_config || {},
            status: i === 0 ? 1 : 0,
          }))
          setPreviewData(fortuneSheets)
          setActiveTab('preview')
        }
      }
    } catch (err) {
      setError('Erreur import: ' + (err.response?.data?.detail || err.message))
    } finally {
      setImporting(false)
    }
  }

  const filteredList = spreadsheets.filter(s =>
    (!sidebarSearch || s.nom?.toLowerCase().includes(sidebarSearch.toLowerCase())) &&
    (!sidebarAppFilter || s.application === sidebarAppFilter)
  )

  const currentSheet = config.sheets[activeSheetIdx] || {}
  const currentFields = fieldsPerSheet[activeSheetIdx] || []

  return (
    <div className="flex h-full bg-gray-50 dark:bg-gray-900">
      {/* ── SIDEBAR ── */}
      <div className="bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col" style={{ width: sidebarWidth, minWidth: 160 }}>
        <div className="p-3 border-b border-gray-100 dark:border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <FileSpreadsheet size={13} /> Classeurs
            </h3>
            <button onClick={handleNew}
              className="p-1.5 rounded-lg bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-900/40 transition-colors" title="Nouveau classeur">
              <Plus size={13} />
            </button>
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

        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {listLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-gray-400" /></div>
          ) : (
            <>
              {filteredList.map(s => (
                <div key={s.id}
                  onClick={() => loadSpreadsheet(s.id)}
                  className={`group flex items-center gap-2 px-2.5 py-2 rounded-xl cursor-pointer transition-all text-xs
                    ${selectedId === s.id ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 font-medium' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 text-gray-700 dark:text-gray-300'}`}>
                  {s.application && <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${APP_DOT[s.application] || 'bg-gray-400'}`} />}
                  <span className="truncate flex-1">{s.nom}</span>
                  <button onClick={(e) => { e.stopPropagation(); handleDelete(s.id) }}
                    className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all flex-shrink-0">
                    <Trash2 className="w-3 h-3 text-red-400" />
                  </button>
                </div>
              ))}
              {filteredList.length === 0 && (
                <p className="text-xs text-gray-400 text-center py-4">
                  {sidebarSearch || sidebarAppFilter ? 'Aucun resultat' : 'Aucun classeur'}
                </p>
              )}
            </>
          )}
        </div>

        {/* Resize handle */}
        <div onMouseDown={handleSidebarResizeStart}
          className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-primary-200 dark:hover:bg-primary-800 transition-colors z-10"
          style={{ left: sidebarWidth - 3 }} />
      </div>

      {/* ── MAIN ── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-2 flex items-center gap-2">
          <div className="flex gap-1">
            {TABS.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                  ${activeTab === tab.id ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'}`}>
                <tab.icon size={14} />
                {tab.label}
              </button>
            ))}
          </div>
          <div className="flex-1" />
          {error && (
            <span className="text-xs text-red-500 mr-2">{error}</span>
          )}
          <input ref={fileInputRef} type="file" accept=".xlsx,.xls" onChange={handleImportExcel} className="hidden" />
          <button onClick={() => fileInputRef.current?.click()} disabled={importing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/40 disabled:opacity-40 transition-colors">
            {importing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
            Importer Excel
          </button>
          <button onClick={handlePreview} disabled={previewLoading || !selectedId}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 disabled:opacity-40 transition-colors">
            {previewLoading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            Apercu
          </button>
          <button onClick={handleSave} disabled={saving || !config.nom.trim()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-40 transition-colors">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            {selectedId ? 'Sauvegarder' : 'Creer'}
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {/* ── TAB: General ── */}
          {activeTab === 'general' && (
            <div className="max-w-2xl mx-auto space-y-4">
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-4 flex items-center gap-2">
                  <FileSpreadsheet size={16} className="text-primary-500" /> Identite du classeur
                </h3>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Nom *</label>
                    <input type="text" value={config.nom} onChange={(e) => updateConfig('nom', e.target.value)}
                      placeholder="Ex: Analyse des ventes par mois"
                      className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-transparent dark:text-white outline-none" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Description</label>
                    <textarea value={config.description} onChange={(e) => updateConfig('description', e.target.value)}
                      placeholder="Description optionnelle..."
                      rows={2}
                      className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-transparent dark:text-white outline-none resize-none" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Application</label>
                      <select value={config.application} onChange={(e) => updateConfig('application', e.target.value)}
                        className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl dark:text-white focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none">
                        {APPLICATION_OPTIONS.map(a => (
                          <option key={a.value} value={a.value}>{a.label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex items-end">
                      <button onClick={() => updateConfig('is_public', !config.is_public)}
                        className="flex items-center gap-2 px-3 py-2 text-sm rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                        {config.is_public ? <Globe size={14} className="text-green-500" /> : <Lock size={14} className="text-gray-400" />}
                        <span className="text-xs text-gray-600 dark:text-gray-400">
                          {config.is_public ? 'Public' : 'Prive'}
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── TAB: Feuilles ── */}
          {activeTab === 'sheets' && (
            <div className="max-w-3xl mx-auto space-y-4">
              {/* Sheet tabs */}
              <div className="flex items-center gap-2 flex-wrap">
                {config.sheets.map((sheet, i) => (
                  <button key={i} onClick={() => setActiveSheetIdx(i)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border
                      ${activeSheetIdx === i ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 border-primary-300 dark:border-primary-600' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                    <Layers size={12} />
                    {sheet.name || `Feuille ${i + 1}`}
                    {config.sheets.length > 1 && (
                      <X size={10} className="ml-1 hover:text-red-500" onClick={(e) => { e.stopPropagation(); removeSheet(i) }} />
                    )}
                  </button>
                ))}
                <button onClick={addSheet}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border border-dashed border-gray-300 dark:border-gray-600">
                  <Plus size={12} /> Ajouter
                </button>
              </div>

              {/* Active sheet config */}
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-200 dark:border-gray-700 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Nom de la feuille</label>
                  <input type="text" value={currentSheet.name || ''} onChange={(e) => updateSheet(activeSheetIdx, 'name', e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-transparent dark:text-white outline-none" />
                </div>

                {currentSheet.imported_celldata?.length > 0 ? (
                  <div className="flex items-center gap-3 p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl">
                    <FileSpreadsheet size={18} className="text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">Donnees importees depuis Excel</p>
                      <p className="text-xs text-emerald-600/70 dark:text-emerald-400/70">
                        {currentSheet.imported_celldata.length} cellules — {currentSheet.imported_row_count || '?'} lignes x {currentSheet.imported_column_count || '?'} colonnes
                      </p>
                    </div>
                    <button onClick={() => {
                      updateSheet(activeSheetIdx, 'imported_celldata', null)
                      updateSheet(activeSheetIdx, 'imported_config', null)
                      updateSheet(activeSheetIdx, 'imported_row_count', null)
                      updateSheet(activeSheetIdx, 'imported_column_count', null)
                    }}
                      className="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      title="Supprimer les donnees importees et utiliser une source de donnees">
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Source de donnees</label>
                    <DataSourceSelector
                      value={currentSheet.data_source_code || currentSheet.data_source_id}
                      onChange={(source) => handleSourceChange(source, activeSheetIdx)}
                    />
                  </div>
                )}

                {/* Column mapping */}
                {currentFields.length > 0 && (
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">
                      Colonnes a afficher ({currentFields.length} champs disponibles)
                    </label>
                    <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="bg-gray-50 dark:bg-gray-900">
                            <th className="px-3 py-2 text-left font-medium text-gray-500">Inclure</th>
                            <th className="px-3 py-2 text-left font-medium text-gray-500">Champ source</th>
                            <th className="px-3 py-2 text-left font-medium text-gray-500">Label affiche</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                          {currentFields.map((field, fi) => {
                            const mapping = (currentSheet.column_mapping || [])
                            const mapped = mapping.find(m => m.field === field.name)
                            const isIncluded = !mapping.length || !!mapped

                            return (
                              <tr key={fi} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                                <td className="px-3 py-1.5">
                                  <input type="checkbox" checked={isIncluded}
                                    onChange={(e) => {
                                      let newMapping = [...(currentSheet.column_mapping || [])]
                                      if (!newMapping.length) {
                                        newMapping = currentFields.map(f => ({ field: f.name, label: f.name }))
                                      }
                                      if (e.target.checked) {
                                        if (!newMapping.find(m => m.field === field.name)) {
                                          newMapping.push({ field: field.name, label: field.name })
                                        }
                                      } else {
                                        newMapping = newMapping.filter(m => m.field !== field.name)
                                      }
                                      updateSheet(activeSheetIdx, 'column_mapping', newMapping)
                                    }}
                                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                                </td>
                                <td className="px-3 py-1.5 font-mono text-gray-700 dark:text-gray-300">{field.name}</td>
                                <td className="px-3 py-1.5">
                                  <input type="text"
                                    value={mapped?.label || field.name}
                                    onChange={(e) => {
                                      let newMapping = [...(currentSheet.column_mapping || [])]
                                      if (!newMapping.length) {
                                        newMapping = currentFields.map(f => ({ field: f.name, label: f.name }))
                                      }
                                      const idx = newMapping.findIndex(m => m.field === field.name)
                                      if (idx >= 0) {
                                        newMapping[idx] = { ...newMapping[idx], label: e.target.value }
                                      } else {
                                        newMapping.push({ field: field.name, label: e.target.value })
                                      }
                                      updateSheet(activeSheetIdx, 'column_mapping', newMapping)
                                    }}
                                    className="w-full px-2 py-1 text-xs bg-transparent border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-primary-400 dark:text-white outline-none" />
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── TAB: Apercu ── */}
          {activeTab === 'preview' && (
            <div className="h-full flex flex-col">
              {previewLoading ? (
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center">
                    <Loader2 className="w-8 h-8 animate-spin text-primary-500 mx-auto mb-2" />
                    <p className="text-sm text-gray-500">Chargement des donnees...</p>
                  </div>
                </div>
              ) : previewData && previewData.length > 0 ? (
                <div className="flex-1 border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden bg-white">
                  <Workbook data={previewData} onChange={() => {}} />
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center">
                    <FileSpreadsheet className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-sm text-gray-500 mb-2">Aucun apercu disponible</p>
                    <p className="text-xs text-gray-400">Cliquez sur "Apercu" pour charger les donnees</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
