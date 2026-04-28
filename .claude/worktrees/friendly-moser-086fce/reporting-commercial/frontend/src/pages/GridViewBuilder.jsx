import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { AgGridReact } from 'ag-grid-react'
import {
  Plus, Save, Trash2, Play, RefreshCw, X, GripVertical, Search,
  Table, Columns, Settings, Eye, EyeOff, ArrowUpDown, Pin, Layers,
  AlignLeft, AlignCenter, AlignRight, ChevronLeft, ChevronRight, Database, Settings2, Pencil, Sparkles,
  TrendingUp, BookOpen, Users, Landmark, LayoutGrid
} from 'lucide-react'
import AIBuilderGenerator from '../components/ai/AIBuilderGenerator'
import Loading from '../components/common/Loading'
import QueryBuilder from '../components/QueryBuilder'
import DataSourceSelector from '../components/DataSourceSelector'
import {
  getGridViews, getGridView, createGridView, updateGridView, deleteGridView,
  getGridData, getDataSources, getDataSource, executeQuery, deleteDataSource,
  getUnifiedDataSourceFields, previewUnifiedDataSource, getUnifiedDataSource,
  getUserGridPrefs, saveUserGridPrefs, getSocietes
} from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { mapColumnsToColDefs, buildTotalsRow } from '../utils/agGridColumnMapper'
import { AG_GRID_LOCALE_FR } from '../utils/agGridLocaleFr'

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

export default function GridViewBuilder() {
  const { user } = useAuth()
  const { darkMode } = useTheme()
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
    try {
      const [gridsRes, sourcesRes] = await Promise.all([
        getGridViews(),
        getDataSources()
      ])
      setGrids(gridsRes.data.data || [])
      setDataSources(sourcesRes.data.data || [])
    } catch (error) {
      console.error('Erreur chargement:', error)
    } finally {
      setLoading(false)
    }
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
        }
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
        features: cleanFeatures
      })

      // Sauvegarder prefs utilisateur avec colonnes nettoyees
      if (user?.id) {
        await saveUserGridPrefs(currentGrid.id, user.id, sanitizedColumns)
      }
      alert('Grille sauvegardée !')
    } catch (error) {
      console.error('Erreur sauvegarde:', error)
      const detail = error.response?.data?.detail
      const msg = Array.isArray(detail)
        ? detail.map(d => d.msg || JSON.stringify(d)).join('\n')
        : (typeof detail === 'string' ? detail : error.message)
      alert('Erreur sauvegarde:\n' + msg)
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
      alert('Erreur lors de la suppression de la source de données')
    }
  }

  // Modifier une datasource (ouvrir Query Builder avec la source)
  const editDataSource = (sourceId) => {
    setShowQueryBuilder(true)
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
        features: cleanFeatures
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

      // DEBUG: Afficher les paramètres envoyés
      console.log('=== DEBUG APERCU ===')
      console.log('Source params:', sourceParams)
      console.log('Param values:', paramValues)
      console.log('Context envoyé:', context)
      console.log('DataSource code:', config.data_source_code)

      // Utiliser l'API unifiée si on a un code de template
      let response
      if (config.data_source_code) {
        // Utiliser previewUnifiedDataSource pour les templates
        console.log('Appel API: previewUnifiedDataSource(' + config.data_source_code + ', ', context, ')')
        response = await previewUnifiedDataSource(config.data_source_code, context)
        console.log('Réponse API:', response.data)
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
        <div className="bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 flex flex-col flex-shrink-0 relative" style={{ width: sidebarWidth }}>
          <div className="px-4 pt-4 pb-3 border-b border-gray-100 dark:border-gray-800">
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
          <div className="flex-1 overflow-y-auto py-2 px-2">
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
          <div onMouseDown={handleSidebarResizeStart}
            className="absolute top-0 right-0 w-1.5 h-full cursor-col-resize hover:bg-primary-400/40 active:bg-primary-500/50 transition-colors z-10" />
        </div>

        {/* Zone principale */}
        {currentGrid ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Configuration — max 45vh, scrollable intérieurement */}
            <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 overflow-y-auto" style={{ maxHeight: '45vh', flexShrink: 0 }}>
              <div className="p-4 pb-2 space-y-4">
              <div className="grid grid-cols-4 gap-4">
                {/* Source de données - Nouveau composant */}
                <div className="col-span-2">
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-medium text-gray-700 dark:text-gray-300">
                      Source de données (Templates + Sources locales)
                    </label>
                    <button
                      onClick={() => {
                        setEditingSourceId(null) // Nouvelle source = vide
                        setShowQueryBuilder(true)
                      }}
                      className="flex items-center gap-1 px-2 py-0.5 text-xs bg-primary-100 hover:bg-primary-200 dark:bg-primary-900/30 dark:hover:bg-primary-900/50 text-primary-700 dark:text-primary-300 rounded"
                    >
                      <Plus className="w-3 h-3" />
                      Créer Source
                    </button>
                  </div>
                  <DataSourceSelector
                    value={config.data_source_code || config.data_source_id}
                    onChange={handleDataSourceChange}
                    showPreview={true}
                    onPreview={(ds) => {
                      // Preview de la datasource
                      console.log('Preview datasource:', ds)
                    }}
                    placeholder="Sélectionner un template ou une source..."
                  />
                  {selectedDataSource && (
                    <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                      {selectedDataSource.origin === 'template' ? (
                        <span className="flex items-center gap-1 text-primary-600">
                          <Settings2 className="w-3 h-3" />
                          Template: {selectedDataSource.code}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1">
                          <Database className="w-3 h-3" />
                          Source locale ID: {selectedDataSource.id}
                        </span>
                      )}
                      {selectedDataSource.origin === 'local' && (
                        <>
                          <button
                            onClick={() => {
                              setEditingSourceId(selectedDataSource.id)
                              setShowQueryBuilder(true)
                            }}
                            className="text-blue-600 hover:underline"
                          >
                            Modifier
                          </button>
                          <button
                            onClick={() => deleteDataSourceHandler(selectedDataSource.id)}
                            className="text-red-500 hover:underline"
                          >
                            Supprimer
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Paramètres de la source de données (inline, style modal) */}
                {sourceParams.length > 0 && (() => {
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
                    <div className="col-span-4 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 shadow-sm">
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
                          onClick={() => { loadSelectOptions(); loadPreview(1) }}
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
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Application
                  </label>
                  <select
                    value={config.application}
                    onChange={(e) => setConfig({ ...config, application: e.target.value })}
                    className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded focus:ring-1 focus:ring-primary-500 dark:bg-gray-700"
                  >
                    {APPLICATION_OPTIONS.map(a => (
                      <option key={a.value} value={a.value}>{a.label}</option>
                    ))}
                  </select>
                </div>

                {/* Lignes par page */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Lignes par page
                  </label>
                  <select
                    value={config.page_size}
                    onChange={(e) => setConfig({ ...config, page_size: parseInt(e.target.value) })}
                    className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded focus:ring-1 focus:ring-primary-500 dark:bg-gray-700"
                  >
                    <option value="10">10</option>
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                    <option value="200">200</option>
                    <option value="500">500</option>
                  </select>
                </div>

                {/* Afficher les totaux */}
                <div className="flex items-center gap-2 pt-5">
                  <input
                    type="checkbox"
                    id="showTotals"
                    checked={config.show_totals}
                    onChange={(e) => setConfig({ ...config, show_totals: e.target.checked })}
                    className="rounded border-primary-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="showTotals" className="text-sm text-gray-700 dark:text-gray-300">
                    Afficher les totaux
                  </label>
                </div>

                {/* Colonnes 100% largeur */}
                <div className="flex items-center gap-2 pt-2">
                  <input
                    type="checkbox"
                    id="displayFullHeight"
                    checked={config.features.display_full_height || false}
                    onChange={(e) => setConfig({
                      ...config,
                      features: { ...config.features, display_full_height: e.target.checked }
                    })}
                    className="rounded border-primary-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="displayFullHeight" className="text-sm text-gray-700 dark:text-gray-300">
                    Colonnes 100% (ajuster les colonnes à la largeur du tableau)
                  </label>
                </div>
              </div>

              {/* Configuration des colonnes */}
              {config.columns.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Configuration des colonnes
                  </label>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-100 dark:bg-gray-700 sticky top-0 z-10 text-xs">
                        <tr>
                          <th className="px-2 py-1 text-left bg-gray-100 dark:bg-gray-700 w-8">Visible</th>
                          <th className="px-2 py-1 text-left bg-gray-100 dark:bg-gray-700">Champ</th>
                          <th className="px-2 py-1 text-left bg-gray-100 dark:bg-gray-700">En-tête</th>
                          <th className="px-2 py-1 text-left bg-gray-100 dark:bg-gray-700 w-32">Format</th>
                          <th className="px-2 py-1 text-left bg-gray-100 dark:bg-gray-700 w-20">Align.</th>
                          <th className="px-2 py-1 text-center bg-gray-100 dark:bg-gray-700 w-6" title="Figer la colonne à gauche"><Pin className="w-3 h-3 inline" /></th>
                          <th className="px-2 py-1 text-center bg-gray-100 dark:bg-gray-700 w-6" title="Grouper par cette colonne"><Layers className="w-3 h-3 inline" /></th>
                          <th className="px-2 py-1 text-left bg-gray-100 dark:bg-gray-700 w-6">Tri</th>
                          {config.show_totals && <th className="px-2 py-1 text-left bg-gray-100 dark:bg-gray-700 w-6">Total</th>}
                        </tr>
                      </thead>
                      <tbody>
                        {config.columns.map((col, i) => (
                          <tr key={col.field} className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750">
                            <td className="px-2 py-1">
                              <button
                                onClick={() => toggleColumnVisibility(i)}
                                className={col.visible ? 'text-green-500' : 'text-gray-400'}
                              >
                                {col.visible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                              </button>
                            </td>
                            <td className="px-2 py-1 text-gray-600 dark:text-gray-400 text-xs max-w-[140px] truncate">{col.field}</td>
                            <td className="px-2 py-1">
                              <input
                                type="text"
                                value={col.header}
                                onChange={(e) => updateColumn(i, { header: e.target.value })}
                                className="w-full px-1 py-0.5 border border-primary-300 dark:border-primary-600 rounded text-xs dark:bg-gray-700"
                              />
                            </td>
                            <td className="px-2 py-1">
                              <select
                                value={col.format || ''}
                                onChange={(e) => updateColumn(i, { format: e.target.value })}
                                className="w-full px-1 py-0.5 border border-primary-300 dark:border-primary-600 rounded text-xs dark:bg-gray-700"
                              >
                                {FORMATS.map(f => (
                                  <option key={f.value} value={f.value}>{f.label}</option>
                                ))}
                              </select>
                            </td>
                            <td className="px-2 py-1">
                              <div className="flex gap-0.5">
                                {ALIGNS.map(a => (
                                  <button
                                    key={a.value}
                                    onClick={() => updateColumn(i, { align: a.value })}
                                    className={`p-0.5 rounded ${col.align === a.value ? 'bg-primary-100 text-primary-600' : 'text-gray-400 hover:text-gray-600'}`}
                                  >
                                    <a.icon className="w-3 h-3" />
                                  </button>
                                ))}
                              </div>
                            </td>
                            <td className="px-2 py-1 text-center">
                              <input
                                type="checkbox"
                                checked={col.pinned === 'left'}
                                onChange={(e) => updateColumn(i, { pinned: e.target.checked ? 'left' : null })}
                                className="rounded border-primary-300 text-blue-600 focus:ring-blue-500"
                                title="Figer à gauche"
                              />
                            </td>
                            <td className="px-2 py-1 text-center">
                              <input
                                type="checkbox"
                                checked={!!col.groupBy}
                                onChange={(e) => updateColumn(i, { groupBy: e.target.checked })}
                                className="rounded border-primary-300 text-amber-600 focus:ring-amber-500"
                                title="Grouper par cette colonne"
                              />
                            </td>
                            <td className="px-2 py-1 text-center">
                              <input
                                type="checkbox"
                                checked={col.sortable}
                                onChange={(e) => updateColumn(i, { sortable: e.target.checked })}
                                className="rounded border-primary-300"
                              />
                            </td>
                            {config.show_totals && (
                              <td className="px-2 py-1 text-center">
                                <input
                                  type="checkbox"
                                  checked={config.total_columns.includes(col.field)}
                                  onChange={() => toggleTotalColumn(col.field)}
                                  className="rounded border-primary-300"
                                  disabled={col.format !== 'number' && col.format !== 'currency'}
                                />
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              </div>{/* fin p-4 content */}
            </div>{/* fin config panel scrollable */}

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
          <div className="flex-1 flex items-center justify-center bg-slate-50 dark:bg-gray-950">
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
