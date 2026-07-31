import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import {
  getPivotsV2, getPivotV2, createPivotV2, updatePivotV2, deletePivotV2,
  previewPivotV2, getPivotV2Fields, getUnifiedDataSourceFields, resetPivotV2UserPrefs,
  deleteDataSource, getMenusFlat, createMenu, updateMenu, deleteMenu
} from '../services/api'
import DataSourceSelector from '../components/DataSourceSelector'
import QueryBuilder from '../components/QueryBuilder'
import { FieldList, DropZone, FormatRuleEditor, PivotTable } from '../components/PivotV2'
import {
  ArrowLeft, Plus, Trash2, Save, Play, Eye, Loader2,
  Settings2, Rows3, Columns3, BarChart3, Palette,
  ToggleLeft, ToggleRight, Globe, Lock, Search, X, Sparkles,
  TrendingUp, BookOpen, Users, Landmark, LayoutGrid, Copy,
  ChevronLeft, ChevronRight, ChevronDown, Pencil, Link
} from 'lucide-react'
import AIBuilderGenerator from '../components/ai/AIBuilderGenerator'
import { useToast } from '../components/common/Toast'
import useSidebarResize from '../hooks/useSidebarResize'
import { APP_DOT, APP_BG } from '../utils/applicationThemes'

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

// Parse JSON string ou retourne le tableau directement.
// Les colonnes de configuration sont stockees en NVARCHAR(MAX) : selon le chemin de lecture,
// elles remontent tantot en tableau deja parse, tantot en chaine JSON brute.
const safeArray = (val) => {
  if (Array.isArray(val)) return val
  if (typeof val === 'string') {
    try { const parsed = JSON.parse(val); return Array.isArray(parsed) ? parsed : [] }
    catch { return [] }
  }
  return []
}

// Generateur d'ID unique pour les champs dans les zones
let _uidCounter = 0
const genUid = () => `_f${++_uidCounter}_${Date.now()}`
// Normalisation via safeArray avant tout .map : recevoir une chaine JSON faisait echouer
// le chargement (une chaine n'a pas de .map), et les zones du concepteur restaient vides.
const ensureUids = (items) => safeArray(items).map(f => f._uid ? f : { ...f, _uid: genUid() })
const stripUids = (items) => safeArray(items).map(({ _uid, ...rest }) => rest)

export default function PivotBuilderV2() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { filters: globalFilters } = useGlobalFilters()
  const toast = useToast()

  // Liste des pivots
  const [pivots, setPivots] = useState([])
  const [selectedPivotId, setSelectedPivotId] = useState(null)
  const [listLoading, setListLoading] = useState(true)
  const [sidebarSearch, setSidebarSearch] = useState('')
  const [sidebarAppFilter, setSidebarAppFilter] = useState('')
  const [showSidebar, setShowSidebar] = useState(true)
  const { sidebarWidth, handleSidebarResizeStart } = useSidebarResize(256)

  // Refonte UI : documentation en modale, calculs avances repliables
  const [showDocsModal, setShowDocsModal] = useState(false)
  const [showAdvancedCalcs, setShowAdvancedCalcs] = useState(false)

  // Source de donnees selectionnee (objet complet) + actions (creer/modifier/supprimer)
  const [selectedDataSource, setSelectedDataSource] = useState(null)
  const [showQueryBuilder, setShowQueryBuilder] = useState(false)
  const [editingSourceId, setEditingSourceId] = useState(null)
  const [sourceMenuOpen, setSourceMenuOpen] = useState(false)
  const [drilldownMenuOpen, setDrilldownMenuOpen] = useState(false)

  // Attacher ce pivot au menu dynamique
  const [showMenuModal, setShowMenuModal] = useState(false)
  const [menuFlat, setMenuFlat] = useState([])
  const [menuLoading, setMenuLoading] = useState(false)
  const [menuSaving, setMenuSaving] = useState(false)
  const [newMenuNom, setNewMenuNom] = useState('')
  const [newMenuCode, setNewMenuCode] = useState('')
  const [newMenuParentId, setNewMenuParentId] = useState('')
  const [attachExistingId, setAttachExistingId] = useState('')
  const [parentPickerOpen, setParentPickerOpen] = useState(false)
  const [parentSearch, setParentSearch] = useState('')
  const [existingPickerOpen, setExistingPickerOpen] = useState(false)
  const [existingSearch, setExistingSearch] = useState('')

  // Config du pivot actif
  const [config, setConfig] = useState({
    nom: '',
    description: '',
    data_source_id: null,
    data_source_code: null,
    drilldown_data_source_code: null,
    drilldown_field_mapping: {},
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
          drilldown_field_mapping: data.drilldown_field_mapping || {},
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
        setActiveTab('preview') // Apercu d'abord : on affiche le resultat en priorite
        setShowAdvancedCalcs(safeArray(data.window_calculations).length > 0)

        // Reconstruire la source selectionnee (pour le menu d'actions Créer/Modifier/Supprimer)
        if (data.data_source_id || data.data_source_code) {
          setSelectedDataSource({
            id: data.data_source_id || null,
            code: data.data_source_code || null,
            nom: data.data_source_nom || `Source ${data.data_source_code || data.data_source_id}`,
            origin: data.data_source_code ? 'template' : 'local'
          })
        } else {
          setSelectedDataSource(null)
        }

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
      setSelectedDataSource(source)
      loadFields(source.code || source.id)
    } else {
      updateConfig('data_source_code', null)
      updateConfig('data_source_id', null)
      setSelectedDataSource(null)
      setAvailableFields([])
    }
  }

  // Creer/modifier une source via le Query Builder (depuis le menu d'actions de la source)
  const handleQueryBuilderSave = (sourceId, sourceName) => {
    updateConfig('data_source_id', sourceId)
    updateConfig('data_source_code', null)
    setSelectedDataSource({ id: sourceId, code: null, nom: sourceName || `Source ${sourceId}`, origin: 'local' })
    loadFields(sourceId)
  }

  // Supprimer une source locale (depuis le menu d'actions de la source)
  const deleteDataSourceHandler = async (id) => {
    if (!confirm('Supprimer cette source de données?')) return
    try {
      await deleteDataSource(id)
      if (config.data_source_id === id) {
        updateConfig('data_source_id', null)
        updateConfig('data_source_code', null)
        setSelectedDataSource(null)
        setAvailableFields([])
      }
    } catch (err) {
      console.error('Erreur suppression datasource:', err)
      toast.error('Erreur lors de la suppression de la source de données')
    }
  }

  // Attacher/detacher ce pivot au menu dynamique
  const openMenuModal = async () => {
    if (!selectedPivotId) return
    setShowMenuModal(true)
    setNewMenuNom(config.nom || '')
    setNewMenuCode(
      (config.nom || '')
        .toLowerCase()
        .normalize('NFD').replace(/[̀-ͯ]/g, '')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/(^-|-$)/g, '')
    )
    setNewMenuParentId('')
    setAttachExistingId('')
    setParentPickerOpen(false)
    setParentSearch('')
    setExistingPickerOpen(false)
    setExistingSearch('')
    setMenuLoading(true)
    try {
      const res = await getMenusFlat()
      if (res.data.success === false) {
        console.error('Erreur backend /menus/flat:', res.data.error)
        toast.error(res.data.error || 'Erreur lors du chargement des menus', { title: 'Menus' })
        setMenuFlat([])
      } else {
        setMenuFlat(res.data.data || [])
      }
    } catch (err) {
      console.error('Erreur chargement menus:', err)
      toast.error(err.response?.data?.detail || err.message || 'Erreur lors du chargement des menus')
      setMenuFlat([])
    } finally {
      setMenuLoading(false)
    }
  }

  const refreshMenuFlat = async () => {
    try {
      const res = await getMenusFlat()
      if (res.data.success === false) {
        console.error('Erreur backend /menus/flat:', res.data.error)
        toast.error(res.data.error || 'Erreur lors du rechargement des menus', { title: 'Menus' })
        return
      }
      setMenuFlat(res.data.data || [])
    } catch (err) {
      console.error('Erreur rechargement menus:', err)
    }
  }

  const createAndAttachMenu = async () => {
    if (!selectedPivotId || !newMenuNom.trim() || !newMenuCode.trim()) return
    setMenuSaving(true)
    try {
      await createMenu({
        parent_id: newMenuParentId ? parseInt(newMenuParentId, 10) : null,
        nom: newMenuNom.trim(),
        code: newMenuCode.trim(),
        icon: 'Sigma',
        type: 'pivot-v2',
        target_id: selectedPivotId,
        url: '',
        ordre: 0,
        is_active: true
      })
      toast.success('Menu créé et rapport attaché')
      await refreshMenuFlat()
      setNewMenuNom('')
      setNewMenuCode('')
      setNewMenuParentId('')
    } catch (err) {
      console.error('Erreur création menu:', err)
      toast.error(err.response?.data?.detail || 'Erreur lors de la création du menu')
    } finally {
      setMenuSaving(false)
    }
  }

  const attachToExistingMenu = async () => {
    if (!selectedPivotId || !attachExistingId) return
    const menu = menuFlat.find(m => m.id === parseInt(attachExistingId, 10))
    if (!menu) return
    setMenuSaving(true)
    try {
      await updateMenu(menu.id, {
        parent_id: menu.parent_id,
        nom: menu.nom,
        code: menu.code,
        icon: menu.icon || 'Sigma',
        type: 'pivot-v2',
        target_id: selectedPivotId,
        url: menu.url || '',
        ordre: menu.ordre,
        is_active: menu.is_active
      })
      toast.success(`"${menu.nom}" pointe maintenant vers ce rapport`)
      await refreshMenuFlat()
      setAttachExistingId('')
    } catch (err) {
      console.error('Erreur attachement menu:', err)
      toast.error(err.response?.data?.detail || 'Erreur lors de l\'attachement')
    } finally {
      setMenuSaving(false)
    }
  }

  const detachMenu = async (menu) => {
    if (!confirm(`Détacher "${menu.nom}" du menu ?`)) return
    try {
      await deleteMenu(menu.id)
      toast.success('Menu détaché')
      await refreshMenuFlat()
    } catch (err) {
      console.error('Erreur détachement menu:', err)
      toast.error('Erreur lors du détachement')
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

    const fieldNames = new Set(availableFields.map(f => f.name))
    for (const wc of safeArray(config.window_calculations)) {
      if (wc.type === 'expression' && wc.expression) {
        if (/[;`${}\\]|--|\/\*/.test(wc.expression.replace(/\[[^\]]*\]/g, ''))) {
          setError('Expression contient des caracteres non autorises')
          setActiveTab('config')
          return
        }
        const refs = [...wc.expression.matchAll(/\[([^\]]+)\]/g)].map(m => m[1])
        const bad = refs.filter(r => fieldNames.size > 0 && !fieldNames.has(r))
        if (bad.length) {
          setError(`Champs inconnus dans l'expression : ${bad.join(', ')}`)
          setActiveTab('config')
          return
        }
      }
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

      let savedId = selectedPivotId
      if (selectedPivotId) {
        await updatePivotV2(selectedPivotId, payload)
      } else {
        const res = await createPivotV2(payload)
        if (res.data?.id) {
          savedId = res.data.id
          setSelectedPivotId(savedId)
        }
      }
      // Effacer les user prefs pour que la nouvelle config DB soit la source de vérité
      if (savedId && user?.id) {
        try { await resetPivotV2UserPrefs(savedId, user.id) } catch (_) {}
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

  // Dupliquer un pivot
  const handleClone = async (pivotId) => {
    try {
      const res = await getPivotV2(pivotId)
      if (!res.data?.success) return
      const src = res.data.data
      const clonePayload = {
        nom: `${src.nom} (copie)`,
        description: src.description || '',
        data_source_id: src.data_source_id,
        data_source_code: src.data_source_code,
        drilldown_data_source_code: src.drilldown_data_source_code || null,
        drilldown_field_mapping: src.drilldown_field_mapping || {},
        rows_config: safeArray(src.rows_config),
        columns_config: safeArray(src.columns_config),
        filters_config: safeArray(src.filters_config),
        values_config: safeArray(src.values_config),
        show_grand_totals: !!src.show_grand_totals,
        show_subtotals: !!src.show_subtotals,
        show_row_percent: !!src.show_row_percent,
        show_col_percent: !!src.show_col_percent,
        show_total_percent: !!src.show_total_percent,
        comparison_mode: src.comparison_mode || '',
        formatting_rules: src.formatting_rules || [],
        source_params: src.source_params || [],
        is_public: false,
        application: src.application || '',
        grand_total_position: src.grand_total_position || 'bottom',
        subtotal_position: src.subtotal_position || 'bottom',
        show_summary_row: !!src.show_summary_row,
        summary_functions: safeArray(src.summary_functions),
        window_calculations: safeArray(src.window_calculations),
        created_by: user?.id,
      }
      const createRes = await createPivotV2(clonePayload)
      if (createRes.data?.id) {
        toast.success(`Pivot "${src.nom}" dupliqué`)
        await loadPivots()
        loadPivot(createRes.data.id)
      }
    } catch (err) {
      console.error('Erreur duplication:', err)
      toast.error('Erreur lors de la duplication')
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
    setSelectedDataSource(dsId ? { id: dsId, code: null, nom: `[IA] ${nom || 'Source pivot'}`, origin: 'local' } : null)
  }

  // Nouveau pivot
  const handleNew = () => {
    setSelectedPivotId(null)
    setConfig({ nom: '', description: '', data_source_id: null, data_source_code: null, rows_config: [], columns_config: [], filters_config: [], values_config: [], show_grand_totals: true, show_subtotals: true, show_row_percent: false, show_col_percent: false, show_total_percent: false, comparison_mode: '', formatting_rules: [], source_params: [], is_public: false, application: '', grand_total_position: 'bottom', subtotal_position: 'bottom', show_summary_row: false, summary_functions: [], window_calculations: [] })
    setAvailableFields([])
    setPreviewData(null)
    setDirty(false)
    setActiveTab('general')
    setShowAdvancedCalcs(false)
    setSelectedDataSource(null)
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
      // Envoyer la config a l'ecran : l'apercu reflete les modifications en cours
      // (meme non sauvegardees) et ne depend plus de l'etat de la config en base.
      const liveConfig = {
        rows: stripUids(config.rows_config),
        columns: stripUids(config.columns_config),
        values: stripUids(config.values_config),
        filters: stripUids(config.filters_config),
      }
      const res = await previewPivotV2(selectedPivotId, ctx, liveConfig)
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
      <div className="bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 flex flex-col flex-shrink-0 relative overflow-hidden transition-[width] duration-200" style={{ width: showSidebar ? sidebarWidth : 0 }}>
        {/* Sidebar header */}
        <div className="px-4 pt-4 pb-3 border-b border-gray-100 dark:border-gray-800" style={{ width: sidebarWidth }}>
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
              <button onClick={() => setShowSidebar(false)}
                className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 transition-colors" title="Masquer les pivots">
                <ChevronLeft size={13} />
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
        <div className="flex-1 overflow-y-auto py-2 px-2" style={{ width: sidebarWidth }}>
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
                    <button onClick={(e) => { e.stopPropagation(); handleClone(p.id) }}
                      className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-all flex-shrink-0"
                      title="Dupliquer">
                      <Copy className="w-3 h-3 text-blue-400" />
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(p.id) }}
                      className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all flex-shrink-0"
                      title="Supprimer">
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
        {showSidebar && (
          <div onMouseDown={handleSidebarResizeStart}
            className="absolute top-0 right-0 w-1.5 h-full cursor-col-resize hover:bg-primary-400/40 active:bg-primary-500/50 transition-colors z-10" />
        )}
      </div>

      {/* Rail de bascule — toujours visible, même quand la barre est masquée */}
      <button
        onClick={() => setShowSidebar(v => !v)}
        title={showSidebar ? 'Masquer les pivots' : 'Afficher les pivots'}
        className="w-5 flex-shrink-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800 hover:bg-primary-100 dark:hover:bg-primary-900/40 border-r border-gray-200 dark:border-gray-700 text-gray-500 hover:text-primary-600 transition-colors"
      >
        {showSidebar ? <ChevronLeft className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
      </button>

      {/* ── ZONE PRINCIPALE ── */}
      <div className="flex-1 flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-950 min-w-0">
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
            <button onClick={() => setShowDocsModal(true)}
              title="Documentation du rapport"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-primary-600 rounded-xl transition-colors">
              <BookOpen size={13} />Documentation
            </button>
            {selectedPivotId && (
              <button onClick={openMenuModal}
                title="Attacher ce rapport à un menu dynamique"
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-primary-600 rounded-xl transition-colors">
                <Link size={13} />Menu
              </button>
            )}
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
                <div>
                  <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">Source principale (agrégation pivot)</label>
                  <div className="flex items-stretch gap-1.5">
                    <div className="flex-1 min-w-0">
                      <DataSourceSelector value={config.data_source_code || config.data_source_id} onChange={handleSourceChange} showCode={false} />
                    </div>
                    <div className="relative flex-shrink-0">
                      <button
                        onClick={() => setSourceMenuOpen(o => !o)}
                        title="Actions sur la source"
                        className="w-10 h-full flex items-center justify-center rounded-xl border border-gray-200 dark:border-gray-700 text-gray-500 hover:text-primary-600 hover:border-primary-400 dark:hover:border-primary-500 transition-colors"
                      >
                        <Settings2 className="w-4 h-4" />
                      </button>
                      {sourceMenuOpen && (
                        <>
                          <div className="fixed inset-0 z-40" onClick={() => setSourceMenuOpen(false)} />
                          <div className="absolute right-0 top-full mt-1 z-50 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl py-1 text-sm">
                            <button
                              onClick={() => { setSourceMenuOpen(false); setEditingSourceId(null); setShowQueryBuilder(true) }}
                              className="w-full flex items-center gap-2 px-3 py-2 text-left text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
                            >
                              <Plus className="w-4 h-4 text-primary-500" /> Créer une source
                            </button>
                            {selectedDataSource?.origin === 'local' && (
                              <>
                                <button
                                  onClick={() => { setSourceMenuOpen(false); setEditingSourceId(selectedDataSource.id); setShowQueryBuilder(true) }}
                                  className="w-full flex items-center gap-2 px-3 py-2 text-left text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
                                >
                                  <Pencil className="w-4 h-4 text-gray-400" /> Modifier la source
                                </button>
                                <button
                                  onClick={() => { setSourceMenuOpen(false); deleteDataSourceHandler(selectedDataSource.id) }}
                                  className="w-full flex items-center gap-2 px-3 py-2 text-left text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                                >
                                  <Trash2 className="w-4 h-4" /> Supprimer la source
                                </button>
                              </>
                            )}
                            {selectedDataSource?.origin === 'template' && (
                              <>
                                <button
                                  onClick={() => { setSourceMenuOpen(false); navigate(`/admin/datasources?search=${encodeURIComponent(selectedDataSource.code)}`) }}
                                  className="w-full flex items-center gap-2 px-3 py-2 text-left text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 border-t border-gray-100 dark:border-gray-700 mt-1"
                                >
                                  <Pencil className="w-4 h-4 text-gray-400" /> Modifier le template
                                </button>
                                <div className="px-3 py-1.5 text-xs text-gray-400 flex items-center gap-1.5">
                                  <Settings2 className="w-3.5 h-3.5" /> {selectedDataSource.code}
                                </div>
                              </>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="border-t border-gray-100 dark:border-gray-800 pt-4">
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-semibold text-gray-600 dark:text-gray-400">Source drilldown (detail lignes)</label>
                    {config.drilldown_data_source_code && (
                      <button
                        type="button"
                        onClick={() => { updateConfig('drilldown_data_source_code', null); updateConfig('drilldown_field_mapping', {}) }}
                        className="text-[10px] text-red-400 hover:text-red-600 transition-colors"
                      >
                        Retirer
                      </button>
                    )}
                  </div>
                  <div className="flex items-stretch gap-1.5">
                    <div className="flex-1 min-w-0">
                      <DataSourceSelector
                        value={config.drilldown_data_source_code}
                        onChange={(src) => updateConfig('drilldown_data_source_code', src?.code || null)}
                        placeholder="Meme source (agregee par defaut)"
                        showPreview={false}
                        showCode={false}
                      />
                    </div>
                    <div className="relative flex-shrink-0">
                      <button
                        type="button"
                        onClick={() => setDrilldownMenuOpen(o => !o)}
                        title="Actions sur la source drilldown"
                        className="w-10 h-full flex items-center justify-center rounded-xl border border-gray-200 dark:border-gray-700 text-gray-500 hover:text-primary-600 hover:border-primary-400 dark:hover:border-primary-500 transition-colors"
                      >
                        <Settings2 className="w-4 h-4" />
                      </button>
                      {drilldownMenuOpen && (
                        <>
                          <div className="fixed inset-0 z-40" onClick={() => setDrilldownMenuOpen(false)} />
                          <div className="absolute right-0 top-full mt-1 z-50 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl py-1 text-sm">
                            <button
                              type="button"
                              onClick={() => { setDrilldownMenuOpen(false); navigate('/admin/datasources') }}
                              className="w-full flex items-center gap-2 px-3 py-2 text-left text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
                            >
                              <Plus className="w-4 h-4 text-primary-500" /> Créer une source
                            </button>
                            {config.drilldown_data_source_code && (
                              <>
                                <button
                                  type="button"
                                  onClick={() => { setDrilldownMenuOpen(false); navigate(`/admin/datasources?search=${encodeURIComponent(config.drilldown_data_source_code)}`) }}
                                  className="w-full flex items-center gap-2 px-3 py-2 text-left text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 border-t border-gray-100 dark:border-gray-700 mt-1"
                                >
                                  <Pencil className="w-4 h-4 text-gray-400" /> Modifier le template
                                </button>
                                <div className="px-3 py-1.5 text-xs text-gray-400 flex items-center gap-1.5">
                                  <Settings2 className="w-3.5 h-3.5" /> {config.drilldown_data_source_code}
                                </div>
                              </>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                  {config.drilldown_data_source_code ? (
                    <>
                      <div className="mt-2 p-2.5 bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded-lg">
                        <p className="text-[11px] text-green-700 dark:text-green-400 font-medium">
                          Drilldown actif : {config.drilldown_data_source_code}
                        </p>
                        <p className="text-[10px] text-green-600 dark:text-green-500 mt-0.5">
                          Le clic sur une cellule chargera les donnees depuis cette source au lieu de la source principale.
                        </p>
                      </div>

                      {/* Mapping des champs drilldown */}
                      {(() => {
                        const pivotFields = [
                          ...config.rows_config.map(r => r.field),
                          ...(config.columns_config?.[0]?.field ? [config.columns_config[0].field] : []),
                        ].filter(Boolean)
                        if (pivotFields.length === 0) return null
                        const mapping = config.drilldown_field_mapping || {}
                        return (
                          <div className="mt-3 p-3 bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900 rounded-lg space-y-2">
                            <div className="flex items-center gap-1.5 mb-1">
                              <svg className="w-3.5 h-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                              <span className="text-[11px] font-semibold text-blue-700 dark:text-blue-400">Mapping des filtres</span>
                            </div>
                            <p className="text-[10px] text-blue-600/70 dark:text-blue-400/60 leading-tight">
                              Si les noms de champs different entre la source principale et la source drilldown, indiquez la correspondance.
                            </p>
                            <div className="space-y-1.5">
                              {pivotFields.map(field => (
                                <div key={field} className="flex items-center gap-2">
                                  <span className="text-[11px] text-gray-600 dark:text-gray-400 w-28 truncate flex-shrink-0" title={field}>{field}</span>
                                  <span className="text-gray-300 dark:text-gray-600 text-xs">→</span>
                                  <input
                                    type="text"
                                    value={mapping[field] || ''}
                                    onChange={(e) => {
                                      const val = e.target.value.trim()
                                      const newMapping = { ...mapping }
                                      if (val) newMapping[field] = val
                                      else delete newMapping[field]
                                      updateConfig('drilldown_field_mapping', newMapping)
                                    }}
                                    placeholder={field}
                                    className="flex-1 px-2 py-1 text-[11px] border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400 placeholder:text-gray-300 dark:placeholder:text-gray-600"
                                  />
                                </div>
                              ))}
                            </div>
                          </div>
                        )
                      })()}
                    </>
                  ) : (
                    <p className="mt-1.5 text-[10px] text-gray-400 leading-tight">
                      Source dediee pour le detail (drill-down). Recommande : une source ligne-par-ligne sans GROUP BY pour voir le detail de chaque cellule.
                    </p>
                  )}
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

                  {/* Calculs de fenetre — divulgation progressive (repliable, avance/rare) */}
                  <div className="pt-3 border-t border-gray-100 dark:border-gray-700">
                    <button
                      type="button"
                      onClick={() => setShowAdvancedCalcs(v => !v)}
                      className="w-full flex items-center justify-between mb-2 text-left"
                    >
                      <span className="flex items-center gap-1.5 text-sm font-semibold text-gray-700 dark:text-gray-300">
                        <ChevronDown size={14} className={`text-gray-400 transition-transform ${showAdvancedCalcs ? '' : '-rotate-90'}`} />
                        Calculs avances
                        {safeArray(config.window_calculations).length > 0 && (
                          <span className="text-[10px] font-bold px-1.5 rounded-full bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300">
                            {safeArray(config.window_calculations).length}
                          </span>
                        )}
                      </span>
                    </button>
                    {showAdvancedCalcs && (
                    <>
                    <div className="flex items-center justify-end mb-2">
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
                          {wc.type === 'expression' && (() => {
                            const expr = wc.expression || ''
                            const fieldNames = new Set(availableFields.map(f => f.name))
                            const referenced = [...expr.matchAll(/\[([^\]]+)\]/g)].map(m => m[1])
                            const invalid = referenced.filter(r => !fieldNames.has(r))
                            const hasUnsafe = /[;`${}\\]|--|\/\*/.test(expr.replace(/\[[^\]]*\]/g, ''))
                            return (
                            <div className="col-span-2">
                              <label className="block text-[10px] text-gray-500 mb-0.5">Expression (ex: [Montant TTC] / [Quantite])</label>
                              <input
                                type="text"
                                value={expr}
                                onChange={(e) => {
                                  const arr = [...safeArray(config.window_calculations)]
                                  arr[wcIdx] = { ...arr[wcIdx], expression: e.target.value }
                                  updateConfig('window_calculations', arr)
                                }}
                                placeholder="[Champ1] / [Champ2]"
                                className={`w-full text-xs bg-white dark:bg-gray-700 border rounded px-1.5 py-1 focus:ring-1 focus:ring-blue-500 outline-none font-mono
                                  ${(invalid.length > 0 || hasUnsafe) ? 'border-red-400 dark:border-red-600' : 'border-primary-300 dark:border-primary-600'}`}
                              />
                              {invalid.length > 0 && (
                                <p className="text-[10px] text-red-500 mt-0.5">Champs inconnus : {invalid.join(', ')}</p>
                              )}
                              {hasUnsafe && (
                                <p className="text-[10px] text-red-500 mt-0.5">Caracteres non autorises detectes</p>
                              )}
                            </div>
                            )
                          })()}
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
                    </>
                    )}
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

    {/* Modal Documentation du rapport */}
    {showDocsModal && (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/50" onClick={() => setShowDocsModal(false)} />
        <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 w-[560px] max-w-[92vw] max-h-[85vh] overflow-y-auto">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-5 h-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Documentation du rapport</h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Objectif</label>
              <textarea value={config.doc_description || ''} onChange={e => updateConfig('doc_description', e.target.value)} rows={3}
                placeholder="Decrivez ce que ce rapport affiche..."
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Descriptif des colonnes</label>
              <textarea value={config.doc_fields || ''} onChange={e => updateConfig('doc_fields', e.target.value)} rows={4}
                placeholder="Ex: CA HT = chiffre d'affaires hors taxes&#10;Marge = CA HT - Achats&#10;Client = raison sociale..."
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Formule / Logique</label>
              <textarea value={config.doc_formula || ''} onChange={e => updateConfig('doc_formula', e.target.value)} rows={2}
                placeholder="Ex: SUM(CA HT) - SUM(Achats)..."
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Avantage</label>
              <textarea value={config.doc_advantage || ''} onChange={e => updateConfig('doc_advantage', e.target.value)} rows={2}
                placeholder="A quoi sert ce rapport, quel gain pour l'utilisateur..."
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white" />
            </div>
            <div className="p-2.5 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <p className="text-xs text-blue-600 dark:text-blue-400">
                Cette documentation sera visible par tous les utilisateurs au clic sur le titre du rapport.
              </p>
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <button onClick={() => setShowDocsModal(false)} className="btn-primary">Fermer</button>
          </div>
        </div>
      </div>
    )}

    {/* Query Builder Modal — creer/modifier une source locale */}
    <QueryBuilder
      isOpen={showQueryBuilder}
      onClose={() => { setShowQueryBuilder(false); setEditingSourceId(null) }}
      onSave={handleQueryBuilderSave}
      targetType="pivot"
      initialSourceId={editingSourceId}
    />

    {/* Modal Attacher au menu dynamique */}
    {showMenuModal && (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/50" onClick={() => setShowMenuModal(false)} />
        <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-[560px] max-w-[92vw] max-h-[85vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Link className="w-5 h-5 text-primary-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Attacher au menu dynamique</h2>
            </div>
            <button onClick={() => setShowMenuModal(false)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
              <X className="w-5 h-5" />
            </button>
          </div>

          {menuLoading ? (
            <div className="py-10 text-center text-gray-400">
              <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
              Chargement des menus...
            </div>
          ) : (() => {
            const linkedMenus = menuFlat.filter(m => m.type === 'pivot-v2' && m.target_id === selectedPivotId)
            const attachableMenus = menuFlat.filter(m => m.type === 'pivot-v2' && m.target_id !== selectedPivotId && m.is_custom === true)
            return (
              <div className="space-y-5">
                {/* Menus actuellement liés */}
                <div>
                  <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                    Menus liés à ce rapport
                  </label>
                  {linkedMenus.length === 0 ? (
                    <p className="text-sm text-gray-400">Ce rapport n'est encore attaché à aucun menu.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {linkedMenus.map(m => (
                        <div key={m.id} className="flex items-center justify-between px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-sm">
                          <span className="flex items-center gap-2 text-gray-700 dark:text-gray-200 min-w-0 truncate">
                            <Rows3 className="w-3.5 h-3.5 text-primary-500 flex-shrink-0" />
                            <span className="truncate">{m.parent_name ? `${m.parent_name} > ` : ''}{m.nom}</span>
                            {!m.is_active && <span className="text-[10px] text-orange-500 font-semibold flex-shrink-0">masqué</span>}
                          </span>
                          {m.is_custom === true ? (
                            <button onClick={() => detachMenu(m)} className="text-red-500 hover:text-red-700 text-xs font-medium flex-shrink-0 ml-2">
                              Détacher
                            </button>
                          ) : (
                            <span className="text-[10px] text-gray-400 flex-shrink-0 ml-2">standard</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Créer un nouveau menu */}
                <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
                  <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                    Créer un nouveau menu pour ce rapport
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-600 dark:text-gray-300 mb-1">Nom</label>
                      <input
                        value={newMenuNom}
                        onChange={e => setNewMenuNom(e.target.value)}
                        className="w-full px-2.5 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700 dark:text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 dark:text-gray-300 mb-1">Code</label>
                      <input
                        value={newMenuCode}
                        onChange={e => setNewMenuCode(e.target.value.toLowerCase().replace(/\s+/g, '-'))}
                        className="w-full px-2.5 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700 dark:text-white"
                      />
                    </div>
                  </div>
                  <div className="mt-3 relative">
                    <label className="block text-xs text-gray-600 dark:text-gray-300 mb-1">Emplacement (parent)</label>
                    <button
                      type="button"
                      onClick={() => setParentPickerOpen(o => !o)}
                      className="w-full flex items-center justify-between gap-2 px-2.5 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700 dark:text-white text-left"
                    >
                      <span className="truncate">
                        {newMenuParentId ? (() => {
                          const m = menuFlat.find(x => String(x.id) === String(newMenuParentId))
                          return m ? `${m.parent_name ? m.parent_name + ' > ' : ''}${m.nom}` : '-- Racine --'
                        })() : '-- Racine --'}
                      </span>
                      <ChevronRight className={`w-3.5 h-3.5 text-gray-400 flex-shrink-0 transition-transform ${parentPickerOpen ? 'rotate-90' : ''}`} />
                    </button>
                    {parentPickerOpen && (
                      <>
                        <div className="fixed inset-0 z-40" onClick={() => setParentPickerOpen(false)} />
                        <div className="absolute left-0 right-0 top-full mt-1 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl max-h-64 flex flex-col">
                          <div className="p-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
                            <div className="relative">
                              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                              <input
                                autoFocus
                                value={parentSearch}
                                onChange={e => setParentSearch(e.target.value)}
                                placeholder="Rechercher un dossier..."
                                className="w-full pl-7 pr-2 py-1.5 text-xs bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded outline-none dark:text-white"
                              />
                            </div>
                          </div>
                          <div className="flex-1 overflow-y-auto py-1">
                            <button
                              type="button"
                              onClick={() => { setNewMenuParentId(''); setParentPickerOpen(false); setParentSearch('') }}
                              className={`w-full text-left px-3 py-1.5 text-sm ${!newMenuParentId ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 font-medium' : 'text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'}`}
                            >
                              -- Racine --
                            </button>
                            {menuFlat
                              .filter(m => {
                                const q = parentSearch.trim().toLowerCase()
                                if (!q) return true
                                return m.nom.toLowerCase().includes(q) || (m.parent_name || '').toLowerCase().includes(q) || (m.code || '').toLowerCase().includes(q)
                              })
                              .map(m => (
                                <button
                                  key={m.id}
                                  type="button"
                                  onClick={() => { setNewMenuParentId(String(m.id)); setParentPickerOpen(false); setParentSearch('') }}
                                  className={`w-full text-left px-3 py-1.5 text-sm truncate ${String(newMenuParentId) === String(m.id) ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 font-medium' : 'text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'}`}
                                >
                                  {m.parent_name ? `${m.parent_name} > ` : ''}{m.nom}
                                </button>
                              ))}
                            {parentSearch.trim() && menuFlat.filter(m => m.nom.toLowerCase().includes(parentSearch.trim().toLowerCase())).length === 0 && (
                              <p className="px-3 py-2 text-xs text-gray-400">Aucun résultat</p>
                            )}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                  <button
                    onClick={createAndAttachMenu}
                    disabled={menuSaving || !newMenuNom.trim() || !newMenuCode.trim()}
                    className="btn-primary mt-3 flex items-center gap-2"
                  >
                    {menuSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    Créer et attacher
                  </button>
                </div>

                {/* Attacher à un menu existant */}
                {attachableMenus.length > 0 && (
                  <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
                    <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                      Ou réattacher un menu existant
                    </label>
                    <div className="flex items-center gap-2">
                      <div className="relative flex-1 min-w-0">
                        <button
                          type="button"
                          onClick={() => setExistingPickerOpen(o => !o)}
                          className="w-full flex items-center justify-between gap-2 px-2.5 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700 dark:text-white text-left"
                        >
                          <span className="truncate">
                            {attachExistingId ? (() => {
                              const m = attachableMenus.find(x => String(x.id) === String(attachExistingId))
                              return m ? `${m.parent_name ? m.parent_name + ' > ' : ''}${m.nom}` : '-- Sélectionner un menu Pivot --'
                            })() : '-- Sélectionner un menu Pivot --'}
                          </span>
                          <ChevronRight className={`w-3.5 h-3.5 text-gray-400 flex-shrink-0 transition-transform ${existingPickerOpen ? 'rotate-90' : ''}`} />
                        </button>
                        {existingPickerOpen && (
                          <>
                            <div className="fixed inset-0 z-40" onClick={() => setExistingPickerOpen(false)} />
                            <div className="absolute left-0 right-0 top-full mt-1 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl max-h-64 flex flex-col">
                              <div className="p-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
                                <div className="relative">
                                  <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                                  <input
                                    autoFocus
                                    value={existingSearch}
                                    onChange={e => setExistingSearch(e.target.value)}
                                    placeholder="Rechercher un menu..."
                                    className="w-full pl-7 pr-2 py-1.5 text-xs bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded outline-none dark:text-white"
                                  />
                                </div>
                              </div>
                              <div className="flex-1 overflow-y-auto py-1">
                                {attachableMenus
                                  .filter(m => {
                                    const q = existingSearch.trim().toLowerCase()
                                    if (!q) return true
                                    return m.nom.toLowerCase().includes(q) || (m.parent_name || '').toLowerCase().includes(q) || (m.code || '').toLowerCase().includes(q)
                                  })
                                  .map(m => (
                                    <button
                                      key={m.id}
                                      type="button"
                                      onClick={() => { setAttachExistingId(String(m.id)); setExistingPickerOpen(false); setExistingSearch('') }}
                                      className={`w-full text-left px-3 py-1.5 text-sm truncate ${String(attachExistingId) === String(m.id) ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 font-medium' : 'text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'}`}
                                    >
                                      {m.parent_name ? `${m.parent_name} > ` : ''}{m.nom}
                                    </button>
                                  ))}
                                {existingSearch.trim() && attachableMenus.filter(m => m.nom.toLowerCase().includes(existingSearch.trim().toLowerCase())).length === 0 && (
                                  <p className="px-3 py-2 text-xs text-gray-400">Aucun résultat</p>
                                )}
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                      <button onClick={attachToExistingMenu} disabled={menuSaving || !attachExistingId} className="btn-primary whitespace-nowrap flex-shrink-0">
                        Attacher
                      </button>
                    </div>
                    <p className="text-xs text-gray-400 mt-1.5">Le menu sélectionné pointera désormais vers ce rapport à la place du sien.</p>
                  </div>
                )}
              </div>
            )
          })()}
        </div>
      </div>
    )}

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
