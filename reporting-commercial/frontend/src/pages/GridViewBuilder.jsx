import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { AgGridReact } from 'ag-grid-react'
import {
  Plus, Save, Trash2, Play, RefreshCw, X, GripVertical, Search,
  Table, Columns, Settings, Eye, EyeOff, ArrowUpDown, Pin, Layers,
  AlignLeft, AlignCenter, AlignRight, ChevronLeft, ChevronRight, Database, Settings2, Pencil, Sparkles,
  TrendingUp, BookOpen, Users, Landmark, LayoutGrid, Link
} from 'lucide-react'
import AIBuilderGenerator from '../components/ai/AIBuilderGenerator'
import Loading from '../components/common/Loading'
import QueryBuilder from '../components/QueryBuilder'
import DataSourceSelector from '../components/DataSourceSelector'
import {
  getGridViews, getGridView, createGridView, updateGridView, deleteGridView,
  getGridData, getDataSources, getDataSource, executeQuery, deleteDataSource,
  getUnifiedDataSourceFields, previewUnifiedDataSource, getUnifiedDataSource,
  getUserGridPrefs, saveUserGridPrefs, getSocietes,
  getMenusFlat, createMenu, updateMenu, deleteMenu
} from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useToast } from '../components/common/Toast'
import useSidebarResize from '../hooks/useSidebarResize'
import { mapColumnsToColDefs, buildTotalsRow } from '../utils/agGridColumnMapper'
import { AG_GRID_LOCALE_FR } from '../utils/agGridLocaleFr'
import { APP_DOT, APP_BG } from '../utils/applicationThemes'

const FORMATS = [
  { value: '', label: 'Aucun' },
  { value: 'number', label: 'Nombre' },
  { value: 'currency', label: 'Devise' },
  { value: 'percent', label: 'Pourcentage' },
  { value: 'date', label: 'Date' }
]

const ALIGNS = [
  { value: 'left', icon: AlignLeft },
  { value: 'center', icon: AlignCenter },
  { value: 'right', icon: AlignRight }
]

export default function GridViewBuilder() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { darkMode } = useTheme()
  const toast = useToast()
  const previewGridRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [grids, setGrids] = useState([])
  const [dataSources, setDataSources] = useState([])
  const [currentGrid, setCurrentGrid] = useState(null)
  const [fields, setFields] = useState([])
  const [saving, setSaving] = useState(false)
  const [showNewModal, setShowNewModal] = useState(false)
  const [newGridName, setNewGridName] = useState('')
  const [newGridApp, setNewGridApp] = useState('')
  const [showAIGenerator, setShowAIGenerator] = useState(false)
  const [previewMode, setPreviewMode] = useState(false)
  const [showQueryBuilder, setShowQueryBuilder] = useState(false)
  const [editingSourceId, setEditingSourceId] = useState(null) // null = nouvelle source, id = modifier source existante
  const [sidebarSearch, setSidebarSearch] = useState('')
  const [sidebarAppFilter, setSidebarAppFilter] = useState('')
  const { sidebarWidth, handleSidebarResizeStart } = useSidebarResize(256)

  // Refonte UI : tiroir des colonnes, filtres, documentation, menu source
  const [showColumnsDrawer, setShowColumnsDrawer] = useState(false)
  const [columnSearch, setColumnSearch] = useState('')
  const [sourceMenuOpen, setSourceMenuOpen] = useState(false)
  const [showFiltersPanel, setShowFiltersPanel] = useState(false)
  const [showDocsModal, setShowDocsModal] = useState(false)
  const [showSidebar, setShowSidebar] = useState(true)
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

  // Gestion des paramètres de la source
  const [sourceParams, setSourceParams] = useState([])
  const [paramValues, setParamValues] = useState({})
  const [showParamsModal, setShowParamsModal] = useState(false)
  const [selectOptions, setSelectOptions] = useState({}) // Options pour les paramètres de type select
  const [loadingOptions, setLoadingOptions] = useState(false)

  // Configuration de la grille
  const APPLICATION_OPTIONS = [
    { value: '', label: '-- Aucune application --' },
    { value: 'commercial', label: 'Gestion Commerciale' },
    { value: 'comptabilite', label: 'Comptabilité' },
    { value: 'paie', label: 'Paie' },
    { value: 'tresorerie', label: 'Gestion Trésorerie' },
  ]

  const [config, setConfig] = useState({
    data_source_id: null,
    data_source_code: null, // Nouveau: code du template
    application: '',
    columns: [],
    page_size: 25,
    show_totals: false,
    total_columns: [],
    default_sort: null,
    features: {
      show_search: true,
      show_column_filters: true,
      show_grouping: true,
      show_column_toggle: true,
      show_export: true,
      show_pagination: true,
      show_page_size: true,
      allow_sorting: true,
      display_full_height: true
    }
  })

  // Datasource selectionnee (objet complet)
  const [selectedDataSource, setSelectedDataSource] = useState(null)

  // Donnees de preview — allPreviewData contient TOUTES les lignes (AG Grid gère la pagination)
  const [previewData, setPreviewData] = useState([])
  const [allPreviewData, setAllPreviewData] = useState([])
  const [previewLoading, setPreviewLoading] = useState(false)
  const [reloadingColumns, setReloadingColumns] = useState(false)
  const [pagination, setPagination] = useState({ page: 1, total: 0, totalPages: 0 })
  const [totals, setTotals] = useState({})
  const [previewError, setPreviewError] = useState(null) // Erreur lors de l'aperçu

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    // Charger les champs quand la datasource change (par ID ou code)
    const identifier = config.data_source_code || config.data_source_id
    if (identifier) {
      loadFieldsFromDataSource(identifier)
    }
  }, [config.data_source_id, config.data_source_code])

  // Auto-charger les options select quand les paramètres changent (pour affichage inline)
  useEffect(() => {
    if (sourceParams.length > 0) {
      loadSelectOptions()
    }
  }, [sourceParams])

  const handleQuickSetAppGV = async (e, gridId, appValue) => {
    e.stopPropagation()
    try {
      await updateGridView(gridId, { application: appValue })
      setGrids(prev => prev.map(g => g.id === gridId ? { ...g, application: appValue } : g))
      if (currentGrid?.id === gridId) setCurrentGrid(prev => ({ ...prev, application: appValue }))
    } catch (err) {
      console.error('Erreur affectation application:', err)
    }
  }

  const loadData = async () => {
    setLoading(true)
    const [gridsResult, sourcesResult] = await Promise.allSettled([
      getGridViews(),
      getDataSources()
    ])
    if (gridsResult.status === 'fulfilled') {
      setGrids(gridsResult.value.data.data || [])
    } else {
      console.error('Erreur chargement grilles:', gridsResult.reason)
    }
    if (sourcesResult.status === 'fulfilled') {
      setDataSources(sourcesResult.value.data.data || [])
    } else {
      console.error('Erreur chargement datasources:', sourcesResult.reason)
    }
    setLoading(false)
  }

  // Handler pour la selection d'une DataSource via le nouveau composant
  const handleDataSourceChange = (datasource) => {
    setSelectedDataSource(datasource)
    setConfig({
      ...config,
      data_source_id: datasource?.id || null,
      data_source_code: datasource?.code || null,
      columns: [] // Reset les colonnes
    })
    setFields([])
    setSourceParams([])
    setParamValues({})
  }

  // Charger les champs depuis une datasource (template ou locale)
  const loadFieldsFromDataSource = async (identifier) => {
    try {
      // Utiliser l'API unifiee pour les champs
      const fieldsResponse = await getUnifiedDataSourceFields(identifier)
      const sourceFields = fieldsResponse.data.fields || []
      setFields(sourceFields)

      // Charger les parametres depuis l'API unifiee
      const dsResponse = await getUnifiedDataSource(identifier)
      if (dsResponse.data.success && dsResponse.data.data) {
        const dsData = dsResponse.data.data
        let params = dsData.parameters || dsData.extracted_params || []

        // Parser si c'est une string JSON
        if (typeof params === 'string') {
          try {
            params = JSON.parse(params)
          } catch {
            params = []
          }
        }

        if (Array.isArray(params) && params.length > 0) {
          setSourceParams(params)
          const defaults = {}
          params.forEach(p => {
            const paramName = p.name?.replace('@', '') || p.name
            defaults[p.name || `@${paramName}`] = p.default || p.defaultValue || ''
          })
          setParamValues(defaults)
        } else {
          setSourceParams([])
          setParamValues({})
        }
      }

      // Initialiser les colonnes si aucune configuree
      if (config.columns.length === 0 && sourceFields.length > 0) {
        setConfig(prev => ({
          ...prev,
          columns: sourceFields.map(f => ({
            field: f.name,
            header: f.name,
            width: null,
            sortable: true,
            filterable: true,
            format: f.type === 'number' ? 'number' : '',
            align: f.type === 'number' ? 'right' : 'left',
            visible: true,
            pinned: null,
            groupBy: false
          }))
        }))
      }
    } catch (error) {
      console.error('Erreur chargement champs:', error)
      setFields([])
      setSourceParams([])
    }
  }

  // Resynchroniser les colonnes depuis le DataSource (après modif SQL)
  const resyncColumnsFromDataSource = async () => {
    const identifier = config.data_source_code || config.data_source_id
    if (!identifier) return
    setReloadingColumns(true)
    try {
      const fieldsResponse = await getUnifiedDataSourceFields(identifier)
      const resp = fieldsResponse.data
      const sourceFields = resp.fields || []

      if (!resp.success && resp.error) {
        toast.error(resp.error, { title: 'Erreur colonnes' })
        return
      }
      if (sourceFields.length === 0) {
        toast.warning('Aucune colonne retournée par le DataSource. Vérifiez la requête SQL et la connexion DWH.')
        return
      }

      setFields(sourceFields)

      // Fusion intelligente : garder la config existante, ajouter les nouvelles, supprimer les disparues
      const existingByField = {}
      config.columns.forEach(col => { existingByField[col.field] = col })

      const merged = sourceFields.map(f => existingByField[f.name] || {
        field: f.name,
        header: f.name,
        width: null,
        sortable: true,
        filterable: true,
        format: f.type === 'number' ? 'number' : '',
        align: f.type === 'number' ? 'right' : 'left',
        visible: true,
        pinned: null,
        groupBy: false
      })

      const added = merged.filter(c => !existingByField[c.field]).map(c => c.field)
      const removed = config.columns.filter(c => !sourceFields.find(f => f.name === c.field)).map(c => c.field)

      setConfig(prev => ({ ...prev, columns: merged }))

      const msgs = []
      if (added.length) msgs.push(`+ Ajoutées : ${added.join(', ')}`)
      if (removed.length) msgs.push(`- Supprimées : ${removed.join(', ')}`)
      if (!msgs.length) msgs.push('Aucune modification — les colonnes correspondent déjà à la requête.')
      toast.info(msgs.join('\n'), { title: 'Synchronisation colonnes' })
    } catch (error) {
      console.error('Erreur resync colonnes:', error)
      toast.error(`Erreur réseau : ${error.message}`)
    } finally {
      setReloadingColumns(false)
    }
  }

  const handleQueryBuilderSave = async (sourceId, sourceName) => {
    // Recharger les sources de données
    await loadData()
    // Sélectionner la nouvelle source
    setConfig({ ...config, data_source_id: sourceId, columns: [] })
  }

  const loadGrid = async (id) => {
    try {
      const response = await getGridView(id)
      const grid = response.data.data
      setCurrentGrid(grid)

      // Recuperer la datasource code si disponible
      const dsCode = grid.data_source_code || null
      const dsId = grid.data_source_id || null

      // Charger les prefs utilisateur si disponibles
      let userColumns = grid.columns || []
      if (user?.id && grid.id) {
        try {
          const prefsRes = await getUserGridPrefs(grid.id, user.id)
          if (prefsRes.data.has_prefs && prefsRes.data.data?.length > 0) {
            userColumns = prefsRes.data.data
          }
        } catch (e) { /* utiliser config par defaut */ }
      }

      // Reconcilier groupBy par colonne avec default_group_by (source de verite)
      const savedGroupBy = grid.default_group_by || []
      if (savedGroupBy.length > 0) {
        userColumns = userColumns.map(col => ({
          ...col,
          groupBy: savedGroupBy.includes(col.field) ? true : (col.groupBy === true)
        }))
      }

      setConfig({
        data_source_id: dsId,
        data_source_code: dsCode,
        application: grid.application || '',
        columns: userColumns,
        page_size: grid.page_size || 25,
        show_totals: grid.show_totals || false,
        total_columns: grid.total_columns || [],
        default_sort: grid.default_sort || null,
        features: grid.features || {
          show_search: true,
          show_column_filters: true,
          show_grouping: true,
          show_column_toggle: true,
          show_export: true,
          show_pagination: true,
          show_page_size: true,
          allow_sorting: true,
          display_full_height: true
        },
        doc_description: grid.doc_description || '',
        doc_fields: grid.doc_fields || '',
        doc_formula: grid.doc_formula || '',
        doc_advantage: grid.doc_advantage || '',
      })

      // Mettre a jour selectedDataSource si on a un ID
      if (dsId || dsCode) {
        setSelectedDataSource({
          id: dsId,
          code: dsCode,
          nom: grid.data_source_nom || `Source ${dsId || dsCode}`,
          origin: dsCode ? 'template' : 'local'
        })
      } else {
        setSelectedDataSource(null)
      }

      setPreviewData([])
      setPreviewMode(false)
    } catch (error) {
      console.error('Erreur chargement grille:', error)
    }
  }

  const handleAIImport = async (gridData) => {
    const { sql, nom, columns, page_size, show_totals, total_columns } = gridData
    try {
      // Créer la datasource avec le SQL généré
      let dsId = null
      if (sql) {
        const apiModule = await import('../services/api')
        const dsRes = await apiModule.createDataSource({
          nom: `[IA] ${nom || 'Source grille'}`,
          type: 'query',
          description: `Générée par IA pour: ${nom}`,
          query_template: sql,
          parameters: []
        })
        dsId = dsRes.data?.id
      }

      // Créer la grille avec la config générée
      const response = await createGridView({ nom: nom || 'Grille IA' })
      const newId = response.data?.id
      if (newId) {
        // Sauvegarder la config complète
        await updateGridView(newId, {
          data_source_id: dsId,
          columns: (columns || []).map(c => ({
            field: String(c.field),
            header: String(c.header),
            width: c.width ? parseInt(c.width) : null,
            sortable: c.sortable !== false,
            filterable: c.filterable !== false,
            format: c.format || null,
            align: c.align || 'left',
            visible: c.visible !== false,
            pinned: null,
          })),
          page_size: page_size || 25,
          show_totals: !!show_totals,
          total_columns: total_columns || [],
        })
        setShowAIGenerator(false)
        await loadData()
        await loadGrid(newId)
      }
    } catch (e) {
      console.error('Erreur import IA gridview:', e)
    }
  }

  const createNewGrid = async () => {
    if (!newGridName.trim()) return

    try {
      // Envoi minimal - le backend a des valeurs par défaut
      const response = await createGridView({
        nom: newGridName,
        ...(newGridApp && { application: newGridApp })
      })
      setShowNewModal(false)
      setNewGridName('')
      setNewGridApp('')
      await loadData()
      await loadGrid(response.data.id)
    } catch (error) {
      console.error('Erreur creation:', error)
    }
  }

  const saveGrid = async () => {
    if (!currentGrid) return

    setSaving(true)
    try {
      // 1. Nettoyer colonnes : garder uniquement les champs Pydantic valides
      const sanitizedColumns = (config.columns || [])
        .filter(c => c && c.field && c.header)
        .map(c => ({
          field: String(c.field),
          header: String(c.header),
          width: c.width != null ? parseInt(c.width, 10) || null : null,
          sortable: c.sortable !== false,
          filterable: c.filterable !== false,
          format: c.format || null,
          align: c.align || 'left',
          visible: c.visible !== false,
          pinned: c.pinned || null,
          groupBy: c.groupBy === true
        }))

      // 2. Groupement par defaut
      const default_group_by = sanitizedColumns
        .filter(c => c.groupBy)
        .map(c => c.field)

      // 3. data_source_id : entier ou null
      let dsId = config.data_source_id
      if (dsId != null) {
        const parsed = parseInt(dsId, 10)
        dsId = isNaN(parsed) ? null : parsed
      }

      // 4. Features : objet propre avec tous les booleens
      const cleanFeatures = config.features ? {
        show_search: config.features.show_search !== false,
        show_column_filters: config.features.show_column_filters !== false,
        show_grouping: config.features.show_grouping !== false,
        show_column_toggle: config.features.show_column_toggle !== false,
        show_export: config.features.show_export !== false,
        show_pagination: config.features.show_pagination !== false,
        show_page_size: config.features.show_page_size !== false,
        allow_sorting: config.features.allow_sorting !== false,
        display_full_height: config.features.display_full_height !== false
      } : null

      // 5. Envoi avec TOUT nettoye
      await updateGridView(currentGrid.id, {
        data_source_id: dsId,
        data_source_code: config.data_source_code || null,
        application: config.application || null,
        columns: sanitizedColumns,
        page_size: parseInt(config.page_size, 10) || 25,
        show_totals: !!config.show_totals,
        total_columns: Array.isArray(config.total_columns) ? config.total_columns : [],
        default_sort: config.default_sort || null,
        default_group_by,
        features: cleanFeatures,
        doc_description: config.doc_description || null,
        doc_fields: config.doc_fields || null,
        doc_formula: config.doc_formula || null,
        doc_advantage: config.doc_advantage || null,
      })

      // Sauvegarder prefs utilisateur avec colonnes nettoyees
      if (user?.id) {
        await saveUserGridPrefs(currentGrid.id, user.id, sanitizedColumns)
      }
      toast.success('Grille sauvegardée !')
    } catch (error) {
      console.error('Erreur sauvegarde:', error)
      const detail = error.response?.data?.detail
      const msg = Array.isArray(detail)
        ? detail.map(d => d.msg || JSON.stringify(d)).join('\n')
        : (typeof detail === 'string' ? detail : error.message)
      toast.error(msg, { title: 'Erreur sauvegarde' })
    } finally {
      setSaving(false)
    }
  }

  const deleteGridHandler = async (id) => {
    if (!confirm('Supprimer cette grille?')) return

    try {
      await deleteGridView(id)
      if (currentGrid?.id === id) {
        setCurrentGrid(null)
        setConfig({
          data_source_id: null,
          columns: [],
          page_size: 25,
          show_totals: false,
          total_columns: [],
          default_sort: null,
          features: {
            show_search: true,
            show_column_filters: true,
            show_grouping: true,
            show_column_toggle: true,
            show_export: true,
            show_pagination: true,
            show_page_size: true,
            allow_sorting: true
          }
        })
        setPreviewData([])
      }
      loadData()
    } catch (error) {
      console.error('Erreur suppression:', error)
    }
  }

  // Supprimer une datasource
  const deleteDataSourceHandler = async (id) => {
    if (!confirm('Supprimer cette source de données?')) return

    try {
      await deleteDataSource(id)
      // Si c'est la source actuellement sélectionnée, la désélectionner
      if (config.data_source_id === id) {
        setConfig({ ...config, data_source_id: null, columns: [] })
        setFields([])
        setSourceParams([])
      }
      loadData()
    } catch (error) {
      console.error('Erreur suppression datasource:', error)
      toast.error('Erreur lors de la suppression de la source de données')
    }
  }

  // Modifier une datasource (ouvrir Query Builder avec la source)
  const editDataSource = (sourceId) => {
    setShowQueryBuilder(true)
  }

  // Attacher/detacher ce GridView au menu dynamique
  const openMenuModal = async () => {
    if (!currentGrid) return
    setShowMenuModal(true)
    setNewMenuNom(currentGrid.nom || '')
    setNewMenuCode(
      (currentGrid.nom || '')
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
    if (!currentGrid || !newMenuNom.trim() || !newMenuCode.trim()) return
    setMenuSaving(true)
    try {
      await createMenu({
        parent_id: newMenuParentId ? parseInt(newMenuParentId, 10) : null,
        nom: newMenuNom.trim(),
        code: newMenuCode.trim(),
        icon: 'FileSpreadsheet',
        type: 'gridview',
        target_id: currentGrid.id,
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
    if (!currentGrid || !attachExistingId) return
    const menu = menuFlat.find(m => m.id === parseInt(attachExistingId, 10))
    if (!menu) return
    setMenuSaving(true)
    try {
      await updateMenu(menu.id, {
        parent_id: menu.parent_id,
        nom: menu.nom,
        code: menu.code,
        icon: menu.icon || 'FileSpreadsheet',
        type: 'gridview',
        target_id: currentGrid.id,
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

  // Charger les options pour les paramètres de type select ou multiselect
  const loadSelectOptions = async () => {
    const selectParams = sourceParams.filter(p =>
      p.type === 'select' || p.type === 'multiselect'
    )
    if (selectParams.length === 0) return

    setLoadingOptions(true)
    const newOptions = {}

    for (const param of selectParams) {
      try {
        if (param.query || param.defaultValue) {
          // SQL query définie : l'utiliser en priorité (même pour source 'societe')
          const queryToExecute = param.query || param.defaultValue
          const response = await executeQuery(queryToExecute, 500)
          if (response.data.success && response.data.data) {
            let options = response.data.data.map(row => ({
              value: row.value ?? row.Value ?? row.VALUE ?? row.code ?? row.Code ?? Object.values(row)[0],
              label: row.label ?? row.Label ?? row.LABEL ?? row.libelle ?? row.Libelle ?? Object.values(row)[1] ?? Object.values(row)[0]
            }))
            if (param.allow_null !== false) {
              options = [{ value: '', label: param.null_label || '(Tous)' }, ...options]
            }
            newOptions[param.name] = options
          }
        } else if (param.source === 'societe') {
          // Pas de requête SQL : charger la liste des sociétés depuis l'API
          const response = await getSocietes()
          if (response.data.success && response.data.data) {
            let options = response.data.data.map(s => ({
              value: s.code ?? Object.values(s)[0],
              label: s.nom ?? s.code ?? Object.values(s)[0]
            }))
            if (param.allow_null !== false) {
              options = [{ value: '', label: param.null_label || '(Toutes)' }, ...options]
            }
            newOptions[param.name] = options
          }
        }
      } catch (error) {
        console.error(`Erreur chargement options pour ${param.name}:`, error)
        newOptions[param.name] = []
      }
    }

    setSelectOptions(newOptions)
    setLoadingOptions(false)
  }

  // Vérifier si des paramètres sont requis et afficher la modale
  const handlePreviewClick = async () => {
    // Supporter data_source_code (templates) OU data_source_id (legacy)
    const hasSource = config.data_source_code || config.data_source_id
    if (!currentGrid || !hasSource) return

    // Si des paramètres sont définis, afficher la modale
    if (sourceParams.length > 0) {
      setShowParamsModal(true)
      // Charger les options pour les paramètres de type select
      await loadSelectOptions()
    } else {
      loadPreview(1)
    }
  }

  // Exécuter l'aperçu avec les paramètres saisis
  const executePreviewWithParams = () => {
    setShowParamsModal(false)
    loadPreview(1)
  }

  const loadPreview = async (page = 1) => {
    // Supporter data_source_code (templates) OU data_source_id (legacy)
    const hasSource = config.data_source_code || config.data_source_id
    if (!currentGrid || !hasSource) return

    setPreviewLoading(true)
    setPreviewError(null) // Reset erreur
    try {
      // Sauvegarder d'abord (avec les mêmes nettoyages que saveGrid)
      const sanitizedColumns = (config.columns || [])
        .filter(c => c && c.field && c.header)
        .map(c => ({
          field: String(c.field),
          header: String(c.header),
          width: c.width != null ? parseInt(c.width, 10) || null : null,
          sortable: c.sortable !== false,
          filterable: c.filterable !== false,
          format: c.format || null,
          align: c.align || 'left',
          visible: c.visible !== false,
          pinned: c.pinned || null,
          groupBy: c.groupBy === true
        }))
      const cleanFeatures = config.features ? {
        show_search: config.features.show_search !== false,
        show_column_filters: config.features.show_column_filters !== false,
        show_grouping: config.features.show_grouping !== false,
        show_column_toggle: config.features.show_column_toggle !== false,
        show_export: config.features.show_export !== false,
        show_pagination: config.features.show_pagination !== false,
        show_page_size: config.features.show_page_size !== false,
        allow_sorting: config.features.allow_sorting !== false,
        display_full_height: config.features.display_full_height !== false
      } : null
      let dsId = config.data_source_id
      if (dsId != null) { const parsed = parseInt(dsId, 10); dsId = isNaN(parsed) ? null : parsed }
      await updateGridView(currentGrid.id, {
        data_source_id: dsId,
        data_source_code: config.data_source_code || null,
        columns: sanitizedColumns,
        page_size: parseInt(config.page_size, 10) || 25,
        show_totals: !!config.show_totals,
        total_columns: Array.isArray(config.total_columns) ? config.total_columns : [],
        default_sort: config.default_sort || null,
        features: cleanFeatures,
        doc_description: config.doc_description || null,
        doc_fields: config.doc_fields || null,
        doc_formula: config.doc_formula || null,
        doc_advantage: config.doc_advantage || null,
      })

      // Construire le contexte avec les valeurs des paramètres
      const context = {}
      sourceParams.forEach(p => {
        // Convertir le nom du paramètre (ex: @dateDebut -> dateDebut)
        const key = p.name.replace('@', '')
        const value = paramValues[p.name]
        // Ne pas inclure les valeurs vides - laisser le backend utiliser les défauts
        if (value && value.trim && value.trim() !== '') {
          context[key] = value
        } else if (value && typeof value === 'number') {
          context[key] = value
        }
      })

      let response
      if (config.data_source_code) {
        response = await previewUnifiedDataSource(config.data_source_code, context)
        const allData = response.data.data || []

        // Stocker TOUTES les données — AG Grid gère la pagination
        setAllPreviewData(allData)
        setPreviewData(allData)
        setPagination({ page: 1, total: allData.length, totalPages: 1 })

        // Calculer les totaux
        const calculatedTotals = {}
        if (config.total_columns && config.total_columns.length > 0) {
          config.total_columns.forEach(col => {
            calculatedTotals[col] = allData.reduce((sum, row) => {
              const val = row[col]
              return sum + (typeof val === 'number' ? val : 0)
            }, 0)
          })
        }
        setTotals(calculatedTotals)
      } else {
        // Legacy: utiliser getGridData pour les sources locales
        response = await getGridData(currentGrid.id, {
          page,
          page_size: config.page_size,
          sort_field: config.default_sort?.field,
          sort_direction: config.default_sort?.direction,
          context
        })

        const legacyData = response.data.data || []
        setAllPreviewData(legacyData)
        setPreviewData(legacyData)
        setPagination({
          page: response.data.page,
          total: response.data.total,
          totalPages: response.data.total_pages
        })
        setTotals(response.data.totals || {})
      }

      setPreviewMode(true)
    } catch (error) {
      console.error('Erreur preview:', error)
      // Extraire le message d'erreur
      const errorMessage = error.response?.data?.error
        || error.response?.data?.message
        || error.message
        || 'Erreur lors de l\'exécution de la requête'
      setPreviewError(errorMessage)
      setPreviewData([])
      setPreviewMode(true) // Afficher quand même pour montrer l'erreur
    } finally {
      setPreviewLoading(false)
    }
  }

  const updateColumn = (index, updates) => {
    const newColumns = [...config.columns]
    newColumns[index] = { ...newColumns[index], ...updates }
    setConfig({ ...config, columns: newColumns })
  }

  const toggleColumnVisibility = (index) => {
    updateColumn(index, { visible: !config.columns[index].visible })
  }

  const setAllColumnsVisible = (visible) => {
    setConfig(prev => ({ ...prev, columns: prev.columns.map(c => ({ ...c, visible })) }))
  }

  const toggleTotalColumn = (field) => {
    if (config.total_columns.includes(field)) {
      setConfig({ ...config, total_columns: config.total_columns.filter(c => c !== field) })
    } else {
      setConfig({ ...config, total_columns: [...config.total_columns, field] })
    }
  }

  const formatValue = (value, format) => {
    if (value === null || value === undefined) return ''

    switch (format) {
      case 'number':
        return typeof value === 'number'
          ? value.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
          : value
      case 'currency':
        return typeof value === 'number'
          ? value.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : value
      case 'percent':
        return typeof value === 'number'
          ? (value * 100).toFixed(2) + '%'
          : value
      case 'date':
        try {
          const d = new Date(value)
          if (isNaN(d.getTime())) return value
          return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
        } catch { return value }
      default:
        return typeof value === 'number'
          ? value.toLocaleString('fr-FR')
          : value
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // AG Grid Preview — colonnes, totaux, features
  // ═══════════════════════════════════════════════════════════════════
  const previewFeatures = useMemo(() => ({
    show_search: true,
    show_column_filters: true,
    show_grouping: true,
    show_column_toggle: true,
    show_export: true,
    show_pagination: true,
    show_page_size: true,
    allow_sorting: true,
    ...(config.features || {})
  }), [config.features])

  const previewColDefs = useMemo(() => {
    if (!config.columns.length || !allPreviewData.length) return []
    return mapColumnsToColDefs(config.columns, previewFeatures)
  }, [config.columns, allPreviewData, previewFeatures])

  const previewDefaultColDef = useMemo(() => ({
    sortable: true,
    resizable: true,
    filter: true,
    filterParams: { buttons: ['reset'] },
    suppressHeaderMenuButton: true,
    suppressHeaderContextMenu: true
  }), [])

  const previewTotalsRow = useMemo(() => {
    if (!config.show_totals || !config.total_columns?.length || !allPreviewData.length) return undefined
    return buildTotalsRow(config.total_columns, allPreviewData, config.columns)
  }, [config.show_totals, config.total_columns, allPreviewData, config.columns])

  if (loading) {
    return <Loading message="Chargement du GridView Builder..." />
  }

  return (
    <div className="h-full flex flex-col -m-3 lg:-m-4">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
            <Table size={15} className="text-primary-600 dark:text-primary-400" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-bold text-gray-900 dark:text-white truncate leading-tight">
              {currentGrid ? currentGrid.nom : 'GridView Builder'}
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {currentGrid && (
            <>
              <button
                onClick={handlePreviewClick}
                disabled={previewLoading || (!config.data_source_id && !config.data_source_code)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-colors disabled:opacity-50"
              >
                {previewLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                Aperçu
              </button>
              <button
                onClick={saveGrid}
                disabled={saving}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 transition-colors shadow-sm"
              >
                {saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Sauvegarder
              </button>
            </>
          )}
          <button
            onClick={() => setShowAIGenerator(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-gradient-to-r from-violet-600 to-purple-600 text-white hover:from-violet-700 hover:to-purple-700 transition-all shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5" />IA
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div className="bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 flex flex-col flex-shrink-0 relative overflow-hidden transition-[width] duration-200" style={{ width: showSidebar ? sidebarWidth : 0 }}>
          <div className="px-4 pt-4 pb-3 border-b border-gray-100 dark:border-gray-800" style={{ width: sidebarWidth }}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[11px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">Grilles</h2>
              <div className="flex items-center gap-1">
                <button onClick={() => setShowAIGenerator(true)}
                  className="p-1.5 rounded-lg bg-violet-50 dark:bg-violet-900/20 text-violet-600 dark:text-violet-400 hover:bg-violet-100 dark:hover:bg-violet-900/40 transition-colors" title="Générer par IA">
                  <Sparkles size={13} />
                </button>
                <button onClick={() => setShowNewModal(true)}
                  className="p-1.5 rounded-lg bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-900/40 transition-colors" title="Nouvelle grille">
                  <Plus size={13} />
                </button>
                <button onClick={() => setShowSidebar(false)}
                  className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 transition-colors" title="Masquer les grilles">
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
          <div className="flex-1 overflow-y-auto py-2 px-2" style={{ width: sidebarWidth }}>
            {grids.length === 0 ? (
              <p className="text-xs text-gray-400 text-center py-6">Aucune grille créée</p>
            ) : (
              <>
                {grids
                  .filter(g => (!sidebarSearch || g.nom.toLowerCase().includes(sidebarSearch.toLowerCase())) && (!sidebarAppFilter || g.application === sidebarAppFilter))
                  .map(g => (
                    <div key={g.id} onClick={() => loadGrid(g.id)}
                      className={`group flex items-center gap-2 px-2 py-1.5 rounded-xl cursor-pointer transition-all duration-150 mb-0.5
                        ${currentGrid?.id === g.id
                          ? 'bg-primary-50 dark:bg-primary-900/20 shadow-sm ring-1 ring-primary-200 dark:ring-primary-800'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-800/60'}`}>
                      <div className={`w-1 h-7 rounded-full flex-shrink-0 ${APP_DOT[g.application] || 'bg-gray-200 dark:bg-gray-700'}`} />
                      <div className={`flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center ${APP_BG[g.application] || 'bg-gray-100 dark:bg-gray-800'}`} title={g.application || ''}>
                        {g.application === 'commercial'   && <TrendingUp className="w-3 h-3 text-blue-600 dark:text-blue-400" strokeWidth={2.5} />}
                        {g.application === 'comptabilite' && <BookOpen   className="w-3 h-3 text-emerald-600 dark:text-emerald-400" strokeWidth={2.5} />}
                        {g.application === 'paie'         && <Users      className="w-3 h-3 text-orange-500 dark:text-orange-400" strokeWidth={2.5} />}
                        {g.application === 'tresorerie'   && <Landmark   className="w-3 h-3 text-violet-600 dark:text-violet-400" strokeWidth={2.5} />}
                        {!g.application                   && <LayoutGrid className="w-3 h-3 text-gray-300 dark:text-gray-600" strokeWidth={2} />}
                      </div>
                      <span className={`flex-1 truncate text-[11px] font-semibold ${currentGrid?.id === g.id ? 'text-primary-700 dark:text-primary-400' : 'text-gray-800 dark:text-gray-200'}`}>
                        {g.nom}
                      </span>
                      <button onClick={(e) => { e.stopPropagation(); deleteGridHandler(g.id) }}
                        className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all flex-shrink-0">
                        <Trash2 className="w-3 h-3 text-red-400" />
                      </button>
                    </div>
                  ))}
                {(sidebarSearch || sidebarAppFilter) && grids.filter(g => (!sidebarSearch || g.nom.toLowerCase().includes(sidebarSearch.toLowerCase())) && (!sidebarAppFilter || g.application === sidebarAppFilter)).length === 0 && (
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
          title={showSidebar ? 'Masquer les grilles' : 'Afficher les grilles'}
          className="w-5 flex-shrink-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800 hover:bg-primary-100 dark:hover:bg-primary-900/40 border-r border-gray-200 dark:border-gray-700 text-gray-500 hover:text-primary-600 transition-colors"
        >
          {showSidebar ? <ChevronLeft className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>

        {/* Zone principale */}
        {currentGrid ? (
          <div className="flex-1 flex flex-col overflow-hidden relative min-w-0">
            {/* Barre de configuration compacte */}
            <div className="flex items-end gap-2 px-4 py-2.5 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex-wrap flex-shrink-0 relative">
              <div className="flex items-center gap-1.5 flex-1 min-w-[240px] max-w-[420px]">
                <div className="flex-1 min-w-0">
                  <DataSourceSelector
                    value={config.data_source_code || config.data_source_id}
                    onChange={handleDataSourceChange}
                    showPreview={true}
                    showCode={false}
                    onPreview={() => {}}
                    placeholder="Sélectionner un template ou une source..."
                  />
                </div>
                <div className="relative flex-shrink-0">
                  <button
                    onClick={() => setSourceMenuOpen(o => !o)}
                    title="Actions sur la source"
                    className="w-9 h-9 flex items-center justify-center rounded-xl border border-gray-200 dark:border-gray-700 text-gray-500 hover:text-primary-600 hover:border-primary-400 dark:hover:border-primary-500 transition-colors"
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
                        {selectedDataSource && (
                          <button
                            onClick={() => { setSourceMenuOpen(false); resyncColumnsFromDataSource() }}
                            disabled={reloadingColumns}
                            className="w-full flex items-center gap-2 px-3 py-2 text-left text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 disabled:opacity-50"
                            title="Resynchroniser les colonnes depuis la requête SQL (ajoute les nouvelles colonnes, supprime les disparues, conserve la config existante)"
                          >
                            <RefreshCw className={`w-4 h-4 ${reloadingColumns ? 'animate-spin' : ''}`} /> Régénérer les colonnes
                          </button>
                        )}
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

              <div className="w-px h-8 bg-gray-200 dark:bg-gray-700 flex-shrink-0 hidden md:block" />

                {/* Paramètres de la source de données (inline, style modal) */}
                {sourceParams.length > 0 && showFiltersPanel && (() => {
                  // Presets de période rapide (calculs locaux, sans GlobalFilterContext)
                  const applyPeriod = (type) => {
                    const today = new Date()
                    const y = today.getFullYear()
                    let d1, d2
                    if (type === 'year') {
                      d1 = `${y}-01-01`; d2 = `${y}-12-31`
                    } else if (type === 'prev_year') {
                      d1 = `${y-1}-01-01`; d2 = `${y-1}-12-31`
                    } else if (type === 'month') {
                      const m = String(today.getMonth() + 1).padStart(2, '0')
                      const last = new Date(y, today.getMonth() + 1, 0).getDate()
                      d1 = `${y}-${m}-01`; d2 = `${y}-${m}-${String(last).padStart(2, '0')}`
                    } else if (type === 'quarter') {
                      const q = Math.floor(today.getMonth() / 3)
                      const sm = q * 3 + 1; const em = sm + 2
                      const last = new Date(y, em, 0).getDate()
                      d1 = `${y}-${String(sm).padStart(2, '0')}-01`
                      d2 = `${y}-${String(em).padStart(2, '0')}-${String(last).padStart(2, '0')}`
                    }
                    const next = { ...paramValues }
                    sourceParams.forEach(p => {
                      const gk = p.global_key || p.name
                      if (gk === 'dateDebut' || p.name === 'dateDebut') next[p.name] = d1
                      if (gk === 'dateFin'   || p.name === 'dateFin')   next[p.name] = d2
                    })
                    setParamValues(next)
                  }

                  const hasDateParams = sourceParams.some(p =>
                    p.type === 'date' || p.global_key === 'dateDebut' || p.global_key === 'dateFin'
                  )

                  const periodPresets = [
                    { label: 'Année en cours',    key: 'year'      },
                    { label: 'Année précédente',  key: 'prev_year' },
                    { label: 'Mois en cours',     key: 'month'     },
                    { label: 'Trimestre en cours',key: 'quarter'   },
                  ]

                  const handleReset = () => {
                    const defaults = {}
                    sourceParams.forEach(p => {
                      defaults[p.name] = p.default || p.defaultValue || p.default_value || ''
                    })
                    setParamValues(defaults)
                  }

                  return (
                    <div className="absolute left-0 top-full mt-2 z-40 w-[600px] max-w-[92vw] border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 shadow-2xl">
                      {/* Header */}
                      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                        <Settings2 className="w-4 h-4 text-primary-500" />
                        <span className="text-sm font-semibold text-gray-900 dark:text-white">Paramètres</span>
                      </div>

                      <div className="px-4 py-3">
                        <div className="flex flex-wrap gap-4 items-start">
                        {/* Période rapide */}
                        {hasDateParams && (
                          <div className="min-w-[200px]">
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">
                              Période rapide
                            </label>
                            <div className="grid grid-cols-2 gap-1.5">
                              {periodPresets.map((preset) => (
                                <button
                                  key={preset.key}
                                  type="button"
                                  onClick={() => applyPeriod(preset.key)}
                                  className="px-2 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300 text-left"
                                >
                                  {preset.label}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Champs de paramètres */}
                        {sourceParams.map((param, idx) => {
                          const isSelect = param.type === 'select' || param.type === 'multiselect'
                          const isMulti  = param.type === 'multiselect'
                          const opts     = selectOptions[param.name] || []
                          return (
                            <div key={idx} className="min-w-[160px] flex-1">
                              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                                {param.label || param.name.replace('@', '')}
                                {param.required && <span className="text-red-500 ml-1">*</span>}
                              </label>

                              {isSelect ? (
                                loadingOptions ? (
                                  <div className="flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-xs text-gray-500">
                                    <RefreshCw className="w-3 h-3 animate-spin" /> Chargement…
                                  </div>
                                ) : isMulti ? (
                                  <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-1.5 max-h-32 overflow-y-auto bg-white dark:bg-gray-700 space-y-0.5">
                                    {opts.length === 0
                                      ? <span className="text-xs text-gray-400">Aucune option</span>
                                      : opts.map((opt, j) => (
                                        <label key={j} className="flex items-center gap-2 px-1 py-0.5 hover:bg-gray-50 dark:hover:bg-gray-600 rounded cursor-pointer">
                                          <input
                                            type="checkbox"
                                            checked={(paramValues[param.name] || []).includes(opt.value)}
                                            onChange={(e) => {
                                              const cur = paramValues[param.name] || []
                                              setParamValues({ ...paramValues, [param.name]: e.target.checked ? [...cur, opt.value] : cur.filter(v => v !== opt.value) })
                                            }}
                                            className="rounded border-gray-300 text-primary-600"
                                          />
                                          <span className="text-xs text-gray-700 dark:text-gray-300">{opt.label}</span>
                                        </label>
                                      ))
                                    }
                                  </div>
                                ) : (
                                  <select
                                    value={paramValues[param.name] || ''}
                                    onChange={(e) => setParamValues({ ...paramValues, [param.name]: e.target.value })}
                                    className="w-full px-2 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                                  >
                                    <option value="">Toutes les sociétés</option>
                                    {opts.filter(o => o.value).map((opt, j) => (
                                      <option key={j} value={opt.value}>{opt.label}</option>
                                    ))}
                                  </select>
                                )
                              ) : (
                                <input
                                  type={param.type === 'date' ? 'date' : param.type === 'number' || param.type === 'int' ? 'number' : 'text'}
                                  value={paramValues[param.name] || ''}
                                  onChange={(e) => setParamValues({ ...paramValues, [param.name]: e.target.value })}
                                  placeholder={param.label || param.name}
                                  className="w-full px-2 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                                />
                              )}
                            </div>
                          )
                        })}
                        </div>{/* end flex flex-wrap */}
                      </div>

                      {/* Footer */}
                      <div className="flex items-center justify-between px-4 py-2.5 border-t border-gray-100 dark:border-gray-700">
                        <button
                          type="button"
                          onClick={handleReset}
                          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                        >
                          <X className="w-3 h-3" /> Réinitialiser
                        </button>
                        <button
                          type="button"
                          onClick={() => { loadSelectOptions(); loadPreview(1); setShowFiltersPanel(false) }}
                          disabled={previewLoading}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-white"
                          style={{ backgroundColor: 'var(--color-primary-600)' }}
                        >
                          <Eye className="w-3 h-3" />
                          Appliquer
                        </button>
                      </div>
                    </div>
                  )
                })()}

                {/* Application */}
                <div className="flex flex-col flex-shrink-0">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-400 mb-0.5 pl-0.5">Application</label>
                  <select
                    value={config.application}
                    onChange={(e) => setConfig({ ...config, application: e.target.value })}
                    className="h-8 px-2 text-xs font-semibold border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none"
                  >
                    {APPLICATION_OPTIONS.map(a => (
                      <option key={a.value} value={a.value}>{a.label}</option>
                    ))}
                  </select>
                </div>

                {/* Lignes par page */}
                <div className="flex flex-col flex-shrink-0">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-400 mb-0.5 pl-0.5">Lignes / page</label>
                  <select
                    value={config.page_size}
                    onChange={(e) => setConfig({ ...config, page_size: parseInt(e.target.value) })}
                    className="h-8 px-2 text-xs font-semibold border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none"
                  >
                    <option value="10">10</option>
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                    <option value="200">200</option>
                    <option value="500">500</option>
                  </select>
                </div>

                {/* Bascules d'affichage */}
                <button
                  onClick={() => setConfig({ ...config, show_totals: !config.show_totals })}
                  title="Afficher la ligne des totaux"
                  className={`flex items-center gap-1.5 h-8 px-2.5 rounded-lg text-xs font-semibold border transition-colors flex-shrink-0 ${
                    config.show_totals
                      ? 'bg-primary-50 border-primary-200 text-primary-700 dark:bg-primary-900/30 dark:border-primary-700 dark:text-primary-300'
                      : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:border-gray-300'
                  }`}
                >
                  <span className="text-[13px] font-bold leading-none">Σ</span> Totaux
                </button>
                <button
                  onClick={() => setConfig({ ...config, features: { ...config.features, display_full_height: !config.features.display_full_height } })}
                  title="Ajuster les colonnes à la largeur du tableau"
                  className={`flex items-center gap-1.5 h-8 px-2.5 rounded-lg text-xs font-semibold border transition-colors flex-shrink-0 ${
                    config.features.display_full_height
                      ? 'bg-primary-50 border-primary-200 text-primary-700 dark:bg-primary-900/30 dark:border-primary-700 dark:text-primary-300'
                      : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:border-gray-300'
                  }`}
                >
                  <LayoutGrid className="w-3.5 h-3.5" /> 100%
                </button>

                {sourceParams.length > 0 && (
                  <button
                    onClick={() => setShowFiltersPanel(o => !o)}
                    title="Paramètres de la source"
                    className={`flex items-center gap-1.5 h-8 px-2.5 rounded-lg text-xs font-semibold border transition-colors flex-shrink-0 ${
                      showFiltersPanel
                        ? 'bg-primary-600 border-primary-600 text-white'
                        : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:border-gray-300'
                    }`}
                  >
                    <Settings2 className="w-3.5 h-3.5" /> Filtres
                    <span className={`text-[10px] font-extrabold px-1.5 rounded-full ${showFiltersPanel ? 'bg-white/25' : 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'}`}>
                      {sourceParams.length}
                    </span>
                  </button>
                )}

                <div className="flex-1 hidden lg:block" />

                {/* Documentation */}
                <button
                  onClick={() => setShowDocsModal(true)}
                  title="Documentation du rapport"
                  className="flex items-center gap-1.5 h-8 px-2.5 rounded-lg text-xs font-semibold border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:border-primary-400 hover:text-primary-600 flex-shrink-0"
                >
                  <BookOpen className="w-3.5 h-3.5" /> Documentation
                </button>

                {/* Attacher au menu dynamique */}
                <button
                  onClick={openMenuModal}
                  title="Attacher ce rapport à un menu dynamique"
                  className="flex items-center gap-1.5 h-8 px-2.5 rounded-lg text-xs font-semibold border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:border-primary-400 hover:text-primary-600 flex-shrink-0"
                >
                  <Link className="w-3.5 h-3.5" /> Menu
                </button>

                {/* Bouton tiroir colonnes */}
                <button
                  onClick={() => setShowColumnsDrawer(o => !o)}
                  disabled={config.columns.length === 0}
                  title="Configurer les colonnes"
                  className={`flex items-center gap-2 h-8 px-3 rounded-lg text-xs font-bold border transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0 ${
                    showColumnsDrawer
                      ? 'bg-primary-600 border-primary-600 text-white'
                      : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-primary-400 hover:text-primary-600'
                  }`}
                >
                  <Columns className="w-3.5 h-3.5" />
                  Colonnes
                  <span className={`text-[11px] font-extrabold px-1.5 py-0.5 rounded-full ${showColumnsDrawer ? 'bg-white/25 text-white' : 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'}`}>
                    {config.columns.length}
                  </span>
                </button>
              </div>

            {/* Tiroir de configuration des colonnes (divulgation progressive) */}
            <div
              className={`absolute inset-0 z-20 bg-gray-900/20 dark:bg-black/40 transition-opacity duration-200 ${showColumnsDrawer ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
              onClick={() => setShowColumnsDrawer(false)}
            />
            <div className={`absolute top-0 right-0 h-full w-[420px] max-w-[92%] z-30 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 shadow-2xl flex flex-col transition-transform duration-300 ease-out ${showColumnsDrawer ? 'translate-x-0' : 'translate-x-full'}`}>
              {/* En-tête du tiroir */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <Columns className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white">Colonnes</h3>
                  <span className="text-[11px] font-extrabold text-primary-700 dark:text-primary-300 bg-primary-100 dark:bg-primary-900/40 px-2 py-0.5 rounded-full">
                    {config.columns.length}
                  </span>
                </div>
                <button onClick={() => setShowColumnsDrawer(false)} title="Fermer"
                  className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Outils : recherche + bascule globale */}
              <div className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-100 dark:border-gray-700/60 flex-shrink-0">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                  <input
                    type="text"
                    value={columnSearch}
                    onChange={(e) => setColumnSearch(e.target.value)}
                    placeholder="Filtrer les colonnes..."
                    className="w-full pl-8 pr-3 h-8 text-xs bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-400 focus:border-transparent dark:text-white outline-none"
                  />
                </div>
                <button
                  onClick={() => setAllColumnsVisible(!config.columns.every(c => c.visible))}
                  className="text-[11px] font-semibold text-gray-500 hover:text-primary-600 whitespace-nowrap px-1"
                >
                  {config.columns.every(c => c.visible) ? 'Tout masquer' : 'Tout afficher'}
                </button>
              </div>

              {/* Liste des colonnes — une carte par colonne */}
              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {config.columns.map((col, i) => {
                  const q = columnSearch.trim().toLowerCase()
                  if (q && !col.field.toLowerCase().includes(q) && !(col.header || '').toLowerCase().includes(q)) return null
                  const canTotal = col.format === 'number' || col.format === 'currency'
                  return (
                    <div key={col.field}
                      className={`border rounded-xl p-2.5 transition-colors ${col.visible
                        ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                        : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40 opacity-60'}`}>
                      {/* Ligne 1 : visibilité + en-tête + placement */}
                      <div className="flex items-center gap-2">
                        <GripVertical className="w-3.5 h-3.5 text-gray-300 dark:text-gray-600 flex-shrink-0" />
                        <button
                          onClick={() => toggleColumnVisibility(i)}
                          title={col.visible ? 'Masquer la colonne' : 'Afficher la colonne'}
                          className={`w-7 h-7 flex items-center justify-center rounded-lg flex-shrink-0 ${col.visible
                            ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-400'}`}
                        >
                          {col.visible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                        </button>
                        <input
                          type="text"
                          value={col.header}
                          onChange={(e) => updateColumn(i, { header: e.target.value })}
                          className="flex-1 min-w-0 h-7 px-2 text-xs font-semibold border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none"
                        />
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <button
                            onClick={() => updateColumn(i, { pinned: col.pinned === 'left' ? null : 'left' })}
                            title="Figer à gauche"
                            className={`w-7 h-7 flex items-center justify-center rounded-lg border ${col.pinned === 'left'
                              ? 'bg-sky-50 border-transparent text-sky-600 dark:bg-sky-900/30 dark:text-sky-400'
                              : 'border-gray-200 dark:border-gray-600 text-gray-400 hover:text-gray-600'}`}
                          >
                            <Pin className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => updateColumn(i, { groupBy: !col.groupBy })}
                            title="Grouper par cette colonne"
                            className={`w-7 h-7 flex items-center justify-center rounded-lg border ${col.groupBy
                              ? 'bg-amber-50 border-transparent text-amber-600 dark:bg-amber-900/30 dark:text-amber-400'
                              : 'border-gray-200 dark:border-gray-600 text-gray-400 hover:text-gray-600'}`}
                          >
                            <Layers className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                      {/* Ligne 2 : champ + format + alignement + tri + total */}
                      <div className="flex items-center gap-2 mt-2 pl-[38px]">
                        <span className="font-mono text-[10px] text-gray-400 dark:text-gray-500 truncate max-w-[88px] flex-shrink-0" title={col.field}>{col.field}</span>
                        <select
                          value={col.format || ''}
                          onChange={(e) => updateColumn(i, { format: e.target.value })}
                          className="h-7 px-1.5 text-[11px] font-medium border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 dark:text-gray-200 outline-none focus:ring-2 focus:ring-primary-400"
                        >
                          {FORMATS.map(f => (<option key={f.value} value={f.value}>{f.label}</option>))}
                        </select>
                        <div className="flex border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden ml-auto">
                          {ALIGNS.map(a => (
                            <button
                              key={a.value}
                              onClick={() => updateColumn(i, { align: a.value })}
                              title={`Aligner : ${a.value}`}
                              className={`w-6 h-7 flex items-center justify-center ${col.align === a.value
                                ? 'bg-primary-600 text-white'
                                : 'bg-gray-50 dark:bg-gray-700 text-gray-400 hover:text-gray-600'}`}
                            >
                              <a.icon className="w-3 h-3" />
                            </button>
                          ))}
                        </div>
                        <button
                          onClick={() => updateColumn(i, { sortable: !col.sortable })}
                          title={col.sortable ? 'Tri activé' : 'Tri désactivé'}
                          className={`w-7 h-7 flex items-center justify-center rounded-lg border flex-shrink-0 ${col.sortable
                            ? 'bg-primary-50 border-transparent text-primary-600 dark:bg-primary-900/30 dark:text-primary-400'
                            : 'border-gray-200 dark:border-gray-600 text-gray-400 hover:text-gray-600'}`}
                        >
                          <ArrowUpDown className="w-3.5 h-3.5" />
                        </button>
                        {config.show_totals && (
                          <button
                            onClick={() => canTotal && toggleTotalColumn(col.field)}
                            disabled={!canTotal}
                            title={canTotal ? 'Inclure dans les totaux' : 'Nécessite un format Nombre ou Devise'}
                            className={`w-7 h-7 flex items-center justify-center rounded-lg border flex-shrink-0 text-[13px] font-bold disabled:opacity-30 disabled:cursor-not-allowed ${config.total_columns.includes(col.field)
                              ? 'bg-primary-50 border-transparent text-primary-600 dark:bg-primary-900/30 dark:text-primary-400'
                              : 'border-gray-200 dark:border-gray-600 text-gray-400 hover:text-gray-600'}`}
                          >
                            Σ
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
                {config.columns.length === 0 && (
                  <div className="text-center text-gray-400 py-10 text-sm">
                    <Columns className="w-10 h-10 mx-auto mb-2 opacity-40" />
                    Sélectionnez une source de données<br />pour configurer les colonnes.
                  </div>
                )}
              </div>
            </div>

            {/* Preview de la grille — AG Grid identique au GridView Display */}
            <div className="flex-1 flex flex-col overflow-hidden bg-slate-50 dark:bg-gray-950 p-2" style={{ minHeight: '200px' }}>
              {/* Affichage de l'erreur */}
              {previewError && (
                <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 text-red-500">
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                        Erreur lors de l'exécution de la requête
                      </h3>
                      <p className="mt-1 text-sm text-red-700 dark:text-red-300 whitespace-pre-wrap font-mono">
                        {previewError}
                      </p>
                    </div>
                    <button
                      onClick={() => setPreviewError(null)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
              {!previewMode || allPreviewData.length === 0 ? (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <div className="text-center">
                    <Table className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>Configurez la grille et cliquez sur Aperçu</p>
                  </div>
                </div>
              ) : (
                <div className={`h-full ${darkMode ? 'ag-theme-quartz-dark' : 'ag-theme-quartz'}`}>
                  <AgGridReact
                    ref={previewGridRef}
                    theme="legacy"
                    rowData={allPreviewData}
                    columnDefs={previewColDefs}
                    defaultColDef={previewDefaultColDef}
                    localeText={AG_GRID_LOCALE_FR}
                    animateRows={false}
                    enableCellTextSelection={true}
                    ensureDomOrder={true}
                    pagination={true}
                    paginationPageSize={config.page_size || 25}
                    paginationPageSizeSelector={[10, 25, 50, 100, 200]}
                    pinnedBottomRowData={previewTotalsRow}
                    suppressMenuHide={true}
                    suppressHeaderContextMenu={true}
                    domLayout="normal"
                    onGridReady={(params) => {
                      if (config.features.display_full_height) {
                        setTimeout(() => params.api.sizeColumnsToFit(), 100)
                      } else {
                        setTimeout(() => params.api.autoSizeAllColumns(), 100)
                      }
                    }}
                  />
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-slate-50 dark:bg-gray-950 min-w-0">
            <div className="text-center text-gray-500">
              <Table className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium mb-2">Bienvenue dans le GridView Builder</p>
              <p className="text-sm mb-4">Créez des vues grille personnalisées</p>
              <button onClick={() => setShowNewModal(true)} className="btn-primary">
                <Plus className="w-4 h-4 mr-2" />
                Créer une Grille
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal nouvelle grille */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowNewModal(false)} />
          <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-96">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Nouvelle Grille
            </h2>
            <input
              type="text"
              value={newGridName}
              onChange={(e) => setNewGridName(e.target.value)}
              placeholder="Nom de la grille"
              className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white mb-3"
              autoFocus
              onKeyDown={e => e.key === 'Enter' && createNewGrid()}
            />
            <select
              value={newGridApp}
              onChange={e => setNewGridApp(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 dark:text-white mb-4 focus:ring-2 focus:ring-primary-400 outline-none"
            >
              <option value="">-- Application (optionnel) --</option>
              {APPLICATION_OPTIONS.filter(a => a.value).map(a => (
                <option key={a.value} value={a.value}>{a.label}</option>
              ))}
            </select>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowNewModal(false)} className="btn-secondary">
                Annuler
              </button>
              <button onClick={createNewGrid} disabled={!newGridName.trim()} className="btn-primary">
                Créer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Query Builder Modal */}
      <QueryBuilder
        isOpen={showQueryBuilder}
        onClose={() => {
          setShowQueryBuilder(false)
          setEditingSourceId(null)
        }}
        onSave={handleQueryBuilderSave}
        targetType="gridview"
        initialSourceId={editingSourceId}
      />

      {/* Modal Documentation du rapport */}
      {showDocsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowDocsModal(false)} />
          <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-[560px] max-w-[92vw] max-h-[85vh] overflow-y-auto">
            <div className="flex items-center gap-2 mb-4">
              <BookOpen className="w-5 h-5 text-primary-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Documentation du rapport</h2>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Objectif</label>
                <textarea value={config.doc_description || ''} onChange={e => setConfig({ ...config, doc_description: e.target.value })} rows={2}
                  placeholder="Decrivez ce que ce rapport affiche..."
                  className="w-full px-2.5 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-1 focus:ring-primary-500 dark:bg-gray-700 dark:text-white" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Descriptif des colonnes</label>
                <textarea value={config.doc_fields || ''} onChange={e => setConfig({ ...config, doc_fields: e.target.value })} rows={3}
                  placeholder="Ex: CA HT = chiffre d'affaires hors taxes&#10;Marge = CA HT - Achats..."
                  className="w-full px-2.5 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-1 focus:ring-primary-500 dark:bg-gray-700 dark:text-white" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Formule / Logique</label>
                <textarea value={config.doc_formula || ''} onChange={e => setConfig({ ...config, doc_formula: e.target.value })} rows={2}
                  placeholder="Ex: SUM(CA HT) - SUM(Achats)..."
                  className="w-full px-2.5 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-1 focus:ring-primary-500 dark:bg-gray-700 dark:text-white" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Avantage</label>
                <textarea value={config.doc_advantage || ''} onChange={e => setConfig({ ...config, doc_advantage: e.target.value })} rows={2}
                  placeholder="A quoi sert ce rapport..."
                  className="w-full px-2.5 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-1 focus:ring-primary-500 dark:bg-gray-700 dark:text-white" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setShowDocsModal(false)} className="btn-primary">Fermer</button>
            </div>
          </div>
        </div>
      )}

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
                <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
                Chargement des menus...
              </div>
            ) : (() => {
              const linkedMenus = menuFlat.filter(m => m.type === 'gridview' && m.target_id === currentGrid?.id)
              const attachableMenus = menuFlat.filter(m => m.type === 'gridview' && m.target_id !== currentGrid?.id && m.is_custom === true)
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
                              <LayoutGrid className="w-3.5 h-3.5 text-primary-500 flex-shrink-0" />
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
                                  return (m.nom || '').toLowerCase().includes(q) || (m.parent_name || '').toLowerCase().includes(q) || (m.code || '').toLowerCase().includes(q)
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
                              {parentSearch.trim() && menuFlat.filter(m => (m.nom || '').toLowerCase().includes(parentSearch.trim().toLowerCase())).length === 0 && (
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
                      {menuSaving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
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
                                return m ? `${m.parent_name ? m.parent_name + ' > ' : ''}${m.nom}` : '-- Sélectionner un menu GridView --'
                              })() : '-- Sélectionner un menu GridView --'}
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
                                      return (m.nom || '').toLowerCase().includes(q) || (m.parent_name || '').toLowerCase().includes(q) || (m.code || '').toLowerCase().includes(q)
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
                                  {existingSearch.trim() && attachableMenus.filter(m => (m.nom || '').toLowerCase().includes(existingSearch.trim().toLowerCase())).length === 0 && (
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

      {/* Modal Paramètres — même style que GridViewDisplay */}
      {showParamsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowParamsModal(false)} />
          <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-[500px] max-w-[90vw]">
            <div className="flex items-center gap-2 mb-4">
              <Settings2 className="w-5 h-5 text-primary-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Paramètres du rapport
              </h2>
            </div>

            <p className="text-sm text-gray-500 mb-4">
              Veuillez saisir les paramètres pour afficher les données du rapport.
            </p>

            <div className="space-y-4 mb-6">
              {sourceParams.map((param, i) => (
                <div key={i}>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {param.label || param.name.replace('@', '')}
                    {param.required && <span className="text-red-500 ml-1">*</span>}
                  </label>

                  {(param.type === 'select' || param.type === 'multiselect') ? (
                    loadingOptions ? (
                      <div className="flex items-center gap-2 px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-gray-50 dark:bg-gray-700">
                        <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />
                        <span className="text-sm text-gray-500">Chargement des options...</span>
                      </div>
                    ) : param.type === 'multiselect' ? (
                      <div className="border border-primary-300 dark:border-primary-600 rounded-lg p-2 max-h-48 overflow-y-auto bg-white dark:bg-gray-700">
                        {(selectOptions[param.name] || []).length === 0 ? (
                          <span className="text-sm text-gray-500">Aucune option disponible</span>
                        ) : (
                          <div className="space-y-1">
                            {(selectOptions[param.name] || []).map((opt, j) => (
                              <label key={j} className="flex items-center gap-2 p-1 hover:bg-gray-100 dark:hover:bg-gray-600 rounded cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={(paramValues[param.name] || []).includes(opt.value)}
                                  onChange={(e) => {
                                    const currentValues = paramValues[param.name] || []
                                    const newValues = e.target.checked
                                      ? [...currentValues, opt.value]
                                      : currentValues.filter(v => v !== opt.value)
                                    setParamValues({ ...paramValues, [param.name]: newValues })
                                  }}
                                  className="rounded border-primary-300 text-primary-600 focus:ring-primary-500"
                                />
                                <span className="text-sm text-gray-700 dark:text-gray-300">{opt.label}</span>
                              </label>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <select
                        value={paramValues[param.name] || ''}
                        onChange={(e) => setParamValues({ ...paramValues, [param.name]: e.target.value })}
                        className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                      >
                        <option value="">-- Sélectionner --</option>
                        {(selectOptions[param.name] || []).map((opt, j) => (
                          <option key={j} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    )
                  ) : (
                    <input
                      type={param.type === 'date' ? 'date' : param.type === 'number' ? 'number' : 'text'}
                      value={paramValues[param.name] || ''}
                      onChange={(e) => setParamValues({ ...paramValues, [param.name]: e.target.value })}
                      placeholder={param.label || param.name}
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                    />
                  )}
                </div>
              ))}
            </div>

            <div className="flex justify-end gap-2">
              <button onClick={() => setShowParamsModal(false)} className="btn-secondary">
                Annuler
              </button>
              <button
                onClick={executePreviewWithParams}
                className="btn-primary flex items-center gap-1"
              >
                <Eye className="w-4 h-4" />
                Afficher le rapport
              </button>
            </div>
          </div>
        </div>
      )}

      {showAIGenerator && (
        <AIBuilderGenerator
          mode="gridview"
          onImport={handleAIImport}
          onClose={() => setShowAIGenerator(false)}
        />
      )}
    </div>
  )
}
