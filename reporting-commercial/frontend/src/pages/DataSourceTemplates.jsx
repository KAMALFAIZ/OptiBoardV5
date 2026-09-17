import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Database, Plus, Save, Trash2, Play, RefreshCw, X, Search,
  Code, FileText, Tag, CheckCircle, XCircle, AlertCircle,
  Eye, EyeOff, Copy, Settings2, Loader2, Filter, ChevronDown,
  Shield, Wand2, AlignLeft
} from 'lucide-react'
import { format as formatSql } from 'sql-formatter'
import api, { extractErrorMessage, getQueryBuilderTables, getDwhSchema } from '../services/api'
import { useAuth } from '../context/AuthContext'
import SqlEditor from '../components/SqlEditor'
import JsonEditor from '../components/JsonEditor'
import QueryBuilder from '../components/QueryBuilder'

// Categories de DataSources
const CATEGORIES = [
  { value: '', label: 'Toutes' },
  { value: 'ventes', label: 'Ventes' },
  { value: 'stocks', label: 'Stocks' },
  { value: 'recouvrement', label: 'Recouvrement' },
  { value: 'dashboard', label: 'Dashboard' },
  { value: 'rh', label: 'Ressources Humaines' },
  { value: 'finance', label: 'Finance' },
  { value: 'custom', label: 'Personnalise' }
]

// Types de DataSources
const TYPES = [
  { value: 'query', label: 'Requete SQL' },
  { value: 'view', label: 'Vue SQL' },
  { value: 'procedure', label: 'Procedure Stockee' },
  { value: 'api', label: 'API Externe' }
]

export default function DataSourceTemplates() {
  const { user } = useAuth()
  // Le role peut etre porte par role_global / role_dwh (nouveau format) ou role (ancien)
  const isSuperAdmin = (user?.role_global || user?.role_dwh || user?.role) === 'superadmin'
  const [searchParams] = useSearchParams()

  const [loading, setLoading] = useState(true)
  const [templates, setTemplates] = useState([])
  const [overrides, setOverrides] = useState([])
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [editMode, setEditMode] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [showQueryBuilder, setShowQueryBuilder] = useState(false)
  // Auto-completion SQL : schema { nomTable: [] } (noms de tables du DWH)
  const [sqlSchema, setSqlSchema] = useState(null)
  // Validite du JSON des parametres (bloque l'enregistrement si invalide)
  const [paramsValid, setParamsValid] = useState(true)

  // Filtres — pré-remplis depuis l'URL (?category=recouvrement)
  const [searchTerm, setSearchTerm] = useState(searchParams.get('search') || '')
  const [categoryFilter, setCategoryFilter] = useState(searchParams.get('category') || '')
  const [showSystemOnly, setShowSystemOnly] = useState(false)

  // Formulaire
  const [formData, setFormData] = useState({
    code: '',
    nom: '',
    type: 'query',
    category: 'custom',
    description: '',
    query_template: '',
    parameters: '[]',
    is_system: false,
    actif: true
  })

  // Collapse pour les categories
  const [expandedCategories, setExpandedCategories] = useState({})

  useEffect(() => {
    loadData()
  }, [])

  // Charger le schema du DWH pour l'auto-completion SQL (tables + colonnes).
  // Utilise l'endpoint bulk /schema ; repli sur la liste des tables seules si absent.
  useEffect(() => {
    getDwhSchema()
      .then((res) => {
        if (res.data?.success && res.data.schema && Object.keys(res.data.schema).length) {
          setSqlSchema(res.data.schema)
          return true
        }
        return false
      })
      .catch(() => false)
      .then((ok) => {
        if (ok) return
        // Repli : noms de tables seuls (endpoint /schema pas encore deploye)
        getQueryBuilderTables()
          .then((res) => {
            const list = res.data?.tables || []
            if (list.length) {
              const schema = {}
              list.forEach((t) => { schema[t.name] = [] })
              setSqlSchema(schema)
            }
          })
          .catch(() => {})
      })
  }, [])

  // Si une catégorie est passée en URL, s'assurer qu'elle est dépliée
  useEffect(() => {
    const cat = searchParams.get('category')
    if (cat) {
      setExpandedCategories(prev => ({ ...prev, [cat]: true }))
    }
  }, [searchParams])

  // Ouvrir directement le template visé par ?search=<code> (lien "Modifier le template")
  useEffect(() => {
    const q = searchParams.get('search')
    if (q && templates.length > 0 && !selectedTemplate) {
      const match = templates.find(t => t.code?.toLowerCase() === q.toLowerCase())
      if (match) {
        handleSelectTemplate(match)
        setExpandedCategories(prev => ({ ...prev, [match.category || 'custom']: true }))
      }
    }
  }, [templates, searchParams])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [templatesRes, overridesRes] = await Promise.all([
        api.get('/datasources/templates'),
        api.get('/datasources/overrides')
      ])

      setTemplates(templatesRes.data.data || [])
      setOverrides(overridesRes.data.data || [])

      // Expand toutes les categories par defaut
      const cats = {}
      CATEGORIES.forEach(c => { cats[c.value] = true })
      setExpandedCategories(cats)
    } catch (err) {
      console.error('Erreur chargement:', err)
      setError('Erreur lors du chargement des templates')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectTemplate = (template) => {
    setSelectedTemplate(template)
    setFormData({
      code: template.code || '',
      nom: template.nom || '',
      type: template.type || 'query',
      category: template.category || 'custom',
      description: template.description || '',
      query_template: template.query_template || '',
      parameters: typeof template.parameters === 'string'
        ? template.parameters
        : JSON.stringify(template.parameters || [], null, 2),
      is_system: template.is_system || false,
      actif: template.actif !== false
    })
    setEditMode(false)
    setTestResult(null)
  }

  const handleNewTemplate = () => {
    setSelectedTemplate(null)
    setFormData({
      code: '',
      nom: '',
      type: 'query',
      category: 'custom',
      description: '',
      query_template: '',
      parameters: '[]',
      is_system: false,
      actif: true
    })
    setEditMode(true)
    setTestResult(null)
  }

  const handleFormatSql = () => {
    if (!formData.query_template) return
    try {
      const pretty = formatSql(formData.query_template, {
        language: 'transactsql',
        keywordCase: 'upper',
        tabWidth: 2,
      })
      setFormData((fd) => ({ ...fd, query_template: pretty }))
    } catch (e) {
      setError('Impossible de formater : ' + (e?.message || 'requête invalide'))
    }
  }

  const handleSave = async () => {
    if (!formData.code || !formData.nom) {
      setError('Le code et le nom sont obligatoires')
      return
    }

    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      // Valider le JSON des parametres
      const paramsStr = formData.parameters || '[]'
      try {
        JSON.parse(paramsStr)
      } catch (e) {
        setError('Format JSON invalide pour les parametres')
        setSaving(false)
        return
      }

      const payload = {
        code: formData.code,
        nom: formData.nom,
        type: formData.type,
        category: formData.category,
        description: formData.description,
        query_template: formData.query_template,
        parameters: paramsStr,
        is_system: formData.is_system,
        actif: formData.actif
      }

      // Headers avec role utilisateur pour les templates systeme
      const headers = {
        'X-User-Role': user?.role || 'user',
        'X-User-Id': user?.id || 1
      }

      if (selectedTemplate) {
        // Mise a jour
        await api.put(`/datasources/templates/${selectedTemplate.id}`, payload, { headers })
        setSuccess('Template mis a jour avec succes')
      } else {
        // Creation
        await api.post('/datasources/templates', payload, { headers })
        setSuccess('Template cree avec succes')
      }

      await loadData()
      setEditMode(false)
    } catch (err) {
      console.error('Erreur sauvegarde:', err)
      setError(extractErrorMessage(err, 'Erreur lors de la sauvegarde'))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedTemplate) return
    if (!confirm(`Supprimer le template "${selectedTemplate.nom}" ?`)) return

    try {
      const headers = {
        'X-User-Role': user?.role || 'user'
      }
      await api.delete(`/datasources/templates/id/${selectedTemplate.id}`, { headers })
      setSuccess('Template supprime')
      setSelectedTemplate(null)
      setEditMode(false)
      await loadData()
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la suppression'))
    }
  }

  const handleTest = async () => {
    if (!formData.query_template) {
      setError('Aucune requete a tester')
      return
    }

    setTesting(true)
    setTestResult(null)

    try {
      const response = await api.post('/datasources/execute/test', {
        query: formData.query_template,
        parameters: {},
        limit: 10
      })

      setTestResult({
        success: true,
        data: response.data.data || [],
        rowCount: response.data.total || 0,
        columns: response.data.columns || []
      })
    } catch (err) {
      setTestResult({
        success: false,
        error: extractErrorMessage(err, 'Erreur lors du test')
      })
    } finally {
      setTesting(false)
    }
  }

  const handleDuplicate = () => {
    if (!selectedTemplate) return

    setFormData({
      ...formData,
      code: formData.code + '_COPY',
      nom: formData.nom + ' (Copie)',
      is_system: false
    })
    setSelectedTemplate(null)
    setEditMode(true)
  }

  // Filtrer les templates
  const filteredTemplates = templates.filter(t => {
    if (searchTerm && !t.nom.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !t.code.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false
    }
    if (categoryFilter && t.category !== categoryFilter) {
      return false
    }
    if (showSystemOnly && !t.is_system) {
      return false
    }
    return true
  })

  // Grouper par categorie
  const groupedTemplates = filteredTemplates.reduce((acc, t) => {
    const cat = t.category || 'custom'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(t)
    return acc
  }, {})

  const toggleCategory = (cat) => {
    setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col -m-3 lg:-m-4">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
            <Database className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <h1 className="text-[15px] font-semibold text-gray-900 dark:text-white leading-tight">DataSources Templates</h1>
            <p className="text-[11px] text-gray-400 leading-tight">Sources de données réutilisables par tous les builders</p>
          </div>
          {categoryFilter && (
            <span className="px-2 py-0.5 text-[11px] font-semibold rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 capitalize">
              {CATEGORIES.find(c => c.value === categoryFilter)?.label || categoryFilter}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadData}
            className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-300 hover:border-primary-400 hover:text-primary-600 transition-colors" title="Actualiser">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button onClick={handleNewTemplate}
            className="flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-semibold bg-primary-600 text-white hover:bg-primary-700 shadow-sm transition-colors">
            <Plus className="w-3.5 h-3.5" />
            Nouveau Template
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="mx-4 mt-3 px-3 py-2.5 text-sm bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-300">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {success && (
        <div className="mx-4 mt-3 px-3 py-2.5 text-sm bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} className="ml-auto text-green-400 hover:text-green-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Liste des templates */}
        <div className="w-72 bg-gray-50/60 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col">
          {/* Filtres */}
          <div className="px-4 pt-4 pb-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
            <div className="flex items-center justify-between mb-3">
              <h2 className="flex items-center gap-2 text-[13px] font-semibold text-gray-800 dark:text-gray-100">
                Templates
                <span className="px-2 py-0.5 rounded-full bg-primary-50 dark:bg-primary-900/30 text-[11px] font-semibold text-primary-600 dark:text-primary-300">{templates.length}</span>
              </h2>
              <button
                onClick={() => setShowSystemOnly(!showSystemOnly)}
                className={`p-1.5 rounded-lg transition-colors ${showSystemOnly ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200'}`}
                title="Templates système uniquement"
              >
                <Settings2 className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="relative mb-2">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Rechercher..."
                className="w-full pl-8 pr-7 py-2 text-xs h-8 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-md focus:bg-white dark:focus:bg-gray-800 focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 dark:text-white placeholder-gray-400 outline-none transition-all"
              />
              {searchTerm && (
                <button onClick={() => setSearchTerm('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-2.5 py-2 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md dark:text-white focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 outline-none transition-all"
            >
              {CATEGORIES.map(c => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          {/* Liste groupee */}
          <div className="flex-1 overflow-y-auto">
            {Object.keys(groupedTemplates).length === 0 ? (
              <div className="m-3 px-4 py-8 flex flex-col items-center text-center rounded-lg border border-dashed border-gray-200 dark:border-gray-700 text-xs text-gray-400">
                <Database className="w-6 h-6 mb-2 text-gray-300 dark:text-gray-600" />
                Aucun template trouvé
              </div>
            ) : (
              Object.entries(groupedTemplates).map(([category, items]) => (
                <div key={category}>
                  <button
                    onClick={() => toggleCategory(category)}
                    className="w-full px-3 py-2 flex items-center justify-between text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <ChevronDown className={`w-3.5 h-3.5 transition-transform ${expandedCategories[category] ? '' : '-rotate-90'}`} />
                      {CATEGORIES.find(c => c.value === category)?.label || category}
                    </span>
                    <span className="min-w-[20px] text-center text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-300 px-1.5 py-0.5 rounded-full font-semibold">
                      {items.length}
                    </span>
                  </button>

                  {expandedCategories[category] && (
                    <div className="px-2 pb-2 space-y-1">
                      {items.map(template => (
                        <div
                          key={template.id}
                          onClick={() => handleSelectTemplate(template)}
                          className={`
                            relative overflow-hidden pl-3.5 pr-3 py-2 rounded-lg cursor-pointer text-xs transition-all border bg-white dark:bg-gray-800
                            ${selectedTemplate?.id === template.id
                              ? 'border-primary-300 dark:border-primary-600 shadow-sm'
                              : 'border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600'
                            }
                            ${template.actif ? '' : 'opacity-60'}
                          `}
                        >
                          <span className={`absolute left-0 top-0 bottom-0 w-[3px] ${selectedTemplate?.id === template.id ? 'bg-primary-500' : template.is_system ? 'bg-amber-400' : 'bg-transparent'}`} />
                          <div className="flex items-center justify-between">
                            <span className={`font-semibold truncate ${selectedTemplate?.id === template.id ? 'text-primary-700 dark:text-primary-400' : 'text-gray-800 dark:text-gray-200'}`}>{template.nom}</span>
                            {template.is_system && (
                              <Settings2 className="w-3 h-3 text-amber-500 flex-shrink-0 ml-1" title="Template système" />
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <code className="text-[10px] text-gray-400 dark:text-gray-500 truncate font-mono">
                              {template.code}
                            </code>
                            {!template.actif && (
                              <span className="flex-shrink-0 px-1.5 py-px rounded text-[10px] font-semibold uppercase tracking-wide bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-300">
                                Inactif
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Stats */}
          <div className="px-4 py-2.5 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-[11px] text-gray-400 dark:text-gray-500">
            <div className="flex justify-between">
              <span>{templates.length} templates</span>
              <span>{overrides.length} overrides</span>
            </div>
          </div>
        </div>

        {/* Zone principale */}
        <div className="flex-1 flex flex-col overflow-hidden bg-slate-50 dark:bg-gray-950">
          {selectedTemplate || editMode ? (
            <>
              {/* Toolbar */}
              <div className="flex items-center justify-between px-4 py-2.5 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800">
                <div className="flex items-center gap-3">
                  <div className="min-w-0">
                    <h2 className="text-[13px] font-semibold text-gray-900 dark:text-white leading-tight truncate">
                      {editMode ? (selectedTemplate ? 'Modifier le template' : 'Nouveau template') : (selectedTemplate?.nom || 'Détails')}
                    </h2>
                    {selectedTemplate?.code && <code className="text-[11px] text-gray-400 font-mono leading-tight">{selectedTemplate.code}</code>}
                  </div>
                  {selectedTemplate?.is_system && !editMode && (
                    <span className="text-[11px] font-semibold bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Shield className="w-3 h-3" />
                      Template Systeme
                      {isSuperAdmin && <span className="text-green-600">(modifiable)</span>}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {!editMode ? (
                    <>
                      <button
                        onClick={handleDuplicate}
                        className="flex items-center gap-1.5 h-8 px-3 text-xs font-semibold border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:border-primary-400 hover:text-primary-600 rounded-lg transition-colors disabled:opacity-50 disabled:hover:border-gray-200 disabled:hover:text-gray-600"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        Dupliquer
                      </button>
                      <button
                        onClick={() => setEditMode(true)}
                        className="flex items-center gap-1.5 h-8 px-3 text-xs font-semibold border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:border-primary-400 hover:text-primary-600 rounded-lg transition-colors disabled:opacity-50 disabled:hover:border-gray-200 disabled:hover:text-gray-600"
                        disabled={selectedTemplate?.is_system && !isSuperAdmin}
                        title={selectedTemplate?.is_system && !isSuperAdmin ? "Seuls les superadmin peuvent modifier les templates systeme" : ""}
                      >
                        {selectedTemplate?.is_system && isSuperAdmin && <Shield className="w-3.5 h-3.5 text-amber-500" />}
                        <Settings2 className="w-3.5 h-3.5" />
                        Modifier
                      </button>
                      <button
                        onClick={handleDelete}
                        className="flex items-center gap-1.5 h-8 px-3 text-xs font-semibold border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-red-600 dark:text-red-400 hover:border-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
                        disabled={selectedTemplate?.is_system && !isSuperAdmin}
                        title={selectedTemplate?.is_system && !isSuperAdmin ? "Seuls les superadmin peuvent supprimer les templates systeme" : ""}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Supprimer
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={handleTest}
                        disabled={testing || !formData.query_template}
                        className="flex items-center gap-1.5 h-8 px-3 text-xs font-semibold border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:border-primary-400 hover:text-primary-600 rounded-lg transition-colors disabled:opacity-50 disabled:hover:border-gray-200 disabled:hover:text-gray-600"
                      >
                        {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                        Tester
                      </button>
                      <button
                        onClick={() => {
                          setEditMode(false)
                          if (!selectedTemplate) {
                            setFormData({
                              code: '', nom: '', type: 'query', category: 'custom',
                              description: '', query_template: '', parameters: '[]',
                              is_system: false, actif: true
                            })
                          }
                        }}
                        className="flex items-center gap-1.5 h-8 px-3 text-xs font-semibold border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:border-primary-400 hover:text-primary-600 rounded-lg transition-colors disabled:opacity-50 disabled:hover:border-gray-200 disabled:hover:text-gray-600"
                      >
                        Annuler
                      </button>
                      <button
                        onClick={handleSave}
                        disabled={saving || !paramsValid}
                        title={!paramsValid ? "Corrigez le JSON des paramètres avant d'enregistrer" : ''}
                        className="flex items-center gap-1.5 h-8 px-4 text-xs font-semibold bg-primary-600 text-white hover:bg-primary-700 rounded-lg transition-colors shadow-sm disabled:opacity-50"
                      >
                        {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                        Sauvegarder
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Formulaire */}
              <div className="flex-1 overflow-auto p-4">
                <div className="max-w-4xl mx-auto space-y-4">
                  {/* Infos de base */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5">
                    <div className="mb-5"><div className="flex items-center gap-2.5">
                      <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-300">
                        <FileText className="w-4 h-4" />
                      </span>
                      <div>
                        <h3 className="text-[13px] font-semibold text-gray-900 dark:text-white leading-tight">Informations</h3>
                        <p className="text-[11px] text-gray-400 leading-tight">Identification, type et catégorie</p>
                      </div>
                    </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Code <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={formData.code}
                          onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, '') })}
                          disabled={!editMode || (selectedTemplate && selectedTemplate.is_system)}
                          placeholder="DS_VENTES_GLOBAL"
                          className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 outline-none transition-colors disabled:bg-gray-50 dark:disabled:bg-gray-900/40 disabled:text-gray-500"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Nom <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={formData.nom}
                          onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                          disabled={!editMode}
                          placeholder="Ventes Globales"
                          className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 outline-none transition-colors disabled:bg-gray-50 dark:disabled:bg-gray-900/40 disabled:text-gray-500"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Type
                        </label>
                        <select
                          value={formData.type}
                          onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                          disabled={!editMode}
                          className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 outline-none transition-colors disabled:bg-gray-50 dark:disabled:bg-gray-900/40 disabled:text-gray-500"
                        >
                          {TYPES.map(t => (
                            <option key={t.value} value={t.value}>{t.label}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Categorie
                        </label>
                        <select
                          value={formData.category}
                          onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                          disabled={!editMode}
                          className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 outline-none transition-colors disabled:bg-gray-50 dark:disabled:bg-gray-900/40 disabled:text-gray-500"
                        >
                          {CATEGORIES.filter(c => c.value).map(c => (
                            <option key={c.value} value={c.value}>{c.label}</option>
                          ))}
                        </select>
                      </div>

                      <div className="col-span-2">
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Description
                        </label>
                        <textarea
                          value={formData.description}
                          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                          disabled={!editMode}
                          rows={2}
                          placeholder="Description du template..."
                          className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-white focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 outline-none transition-colors disabled:bg-gray-50 dark:disabled:bg-gray-900/40 disabled:text-gray-500"
                        />
                      </div>

                      <div className="col-span-2 grid grid-cols-2 gap-3 pt-1">
                        {[
                          { key: 'actif', label: 'Actif', hint: 'Disponible dans les builders', disabled: !editMode, on: 'bg-primary-500' },
                          { key: 'is_system', label: 'Template système', hint: 'Protégé contre la modification', disabled: !editMode || (selectedTemplate && selectedTemplate.is_system), on: 'bg-amber-500' },
                        ].map(opt => {
                          const checked = !!formData[opt.key]
                          return (
                            <label key={opt.key} className={`flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 ${opt.disabled ? 'cursor-not-allowed opacity-70' : 'cursor-pointer hover:border-primary-300'}`}>
                              <span>
                                <span className="block text-[13px] text-gray-700 dark:text-gray-300 leading-tight">{opt.label}</span>
                                <span className="block text-[11px] text-gray-400 leading-tight">{opt.hint}</span>
                              </span>
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => setFormData({ ...formData, [opt.key]: e.target.checked })}
                                disabled={opt.disabled}
                                className="sr-only peer"
                              />
                              <span className={`relative inline-flex h-5 w-9 flex-shrink-0 rounded-full transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-primary-500/40 ${checked ? opt.on : 'bg-gray-200 dark:bg-gray-600'}`}>
                                <span className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-4' : ''}`} />
                              </span>
                            </label>
                          )
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Requete SQL */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5">
                    <div className="flex items-center justify-between mb-4">
<div className="flex items-center gap-2.5">
                      <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-sky-50 text-sky-600 dark:bg-sky-900/30 dark:text-sky-300">
                        <Code className="w-4 h-4" />
                      </span>
                      <div>
                        <h3 className="text-[13px] font-semibold text-gray-900 dark:text-white leading-tight">Requête SQL</h3>
                        <p className="text-[11px] text-gray-400 leading-tight">Utilisez @parametre pour les valeurs dynamiques</p>
                      </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {editMode && (
                          <button
                            type="button"
                            onClick={handleFormatSql}
                            disabled={!formData.query_template}
                            className="flex items-center gap-1.5 h-8 px-3 text-xs font-semibold border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:border-primary-400 hover:text-primary-600 rounded-lg transition-colors disabled:opacity-50 disabled:hover:border-gray-200 disabled:hover:text-gray-600"
                            title="Formater / indenter la requête SQL"
                          >
                            <AlignLeft className="w-3.5 h-3.5" />
                            Formater
                          </button>
                        )}
                        {(editMode || isSuperAdmin) && (
                          <button
                            type="button"
                            onClick={() => setShowQueryBuilder(true)}
                            className="flex items-center gap-1.5 h-8 px-3 text-xs font-semibold rounded-lg bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors"
                            title="Construire la requête visuellement (tables, colonnes, jointures, filtres)"
                          >
                            <Wand2 className="w-3.5 h-3.5" />
                            Assistant visuel
                          </button>
                        )}
                      </div>
                    </div>

                    <SqlEditor
                      value={formData.query_template}
                      onChange={(val) => setFormData({ ...formData, query_template: val })}
                      disabled={!editMode}
                      minHeight="300px"
                      schema={sqlSchema}
                      placeholder="SELECT * FROM ma_table WHERE @dateDebut <= date AND date <= @dateFin"
                    />

                    <p className="text-xs text-gray-500 mt-2">
                      Utilisez @parametre pour les parametres dynamiques (ex: @dateDebut, @dateFin, @societe, @societe_filter)
                    </p>
                  </div>

                  {/* Parametres */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5">
                    <div className="flex items-center justify-between mb-4"><div className="flex items-center gap-2.5">
                      <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-violet-50 text-violet-600 dark:bg-violet-900/30 dark:text-violet-300">
                        <Tag className="w-4 h-4" />
                      </span>
                      <div>
                        <h3 className="text-[13px] font-semibold text-gray-900 dark:text-white leading-tight">Paramètres (JSON)</h3>
                        <p className="text-[11px] text-gray-400 leading-tight">Définition des filtres exposés aux utilisateurs</p>
                      </div>
                      </div>
                      {!paramsValid && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-50 dark:bg-red-900/30 text-[11px] font-semibold text-red-600 dark:text-red-400">
                          <XCircle className="w-3.5 h-3.5" /> JSON invalide
                        </span>
                      )}
                    </div>

                    <JsonEditor
                      value={formData.parameters}
                      onChange={(val) => setFormData({ ...formData, parameters: val })}
                      disabled={!editMode}
                      minHeight="200px"
                      onValidityChange={setParamsValid}
                      placeholder='[{"name": "@dateDebut", "type": "date", "label": "Date Debut", "required": true}]'
                    />

                    <div className="text-xs text-gray-500 mt-2 space-y-1">
                      <p>Format: Liste de parametres avec les proprietes:</p>
                      <code className="block bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-2 rounded-md font-mono text-[11px]">
                        {`{"name": "@param", "type": "date|text|number|select", "label": "Label", "required": true, "default": "valeur"}`}
                      </code>
                    </div>
                  </div>

                  {/* Resultat du test */}
                  {testResult && (
                    <div className={`relative overflow-hidden bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5`}>
                      <span className={`absolute left-0 top-0 bottom-0 w-[3px] ${testResult.success ? 'bg-emerald-500' : 'bg-red-500'}`} />
                      <h3 className={`text-[13px] font-semibold mb-4 flex items-center gap-2 ${
                        testResult.success
                          ? 'text-green-700 dark:text-green-400'
                          : 'text-red-700 dark:text-red-400'
                      }`}>
                        {testResult.success ? (
                          <>
                            <CheckCircle className="w-5 h-5" />
                            Test Reussi - {testResult.rowCount} lignes
                          </>
                        ) : (
                          <>
                            <XCircle className="w-5 h-5" />
                            Erreur
                          </>
                        )}
                      </h3>

                      {testResult.success ? (
                        <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
                          <table className="w-full text-xs">
                            <thead className="bg-gray-50 dark:bg-gray-900/40 border-b border-gray-200 dark:border-gray-700">
                              <tr>
                                {testResult.data[0] && Object.keys(testResult.data[0]).map(col => (
                                  <th key={col} className="px-3 py-2 text-left text-[11px] font-semibold text-gray-500 whitespace-nowrap">
                                    {col}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {testResult.data.slice(0, 5).map((row, i) => (
                                <tr key={i} className={i % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-750'}>
                                  {Object.values(row).map((val, j) => (
                                    <td key={j} className="px-3 py-2 text-gray-700 dark:text-gray-300">
                                      {val?.toString() || '-'}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {testResult.data.length > 5 && (
                            <p className="text-sm text-gray-500 mt-2 text-center">
                              ... et {testResult.data.length - 5} autres lignes
                            </p>
                          )}
                        </div>
                      ) : (
                        <p className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 font-mono text-xs whitespace-pre-wrap">
                          {testResult.error}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            /* Aucun template selectionne */
            <div className="flex-1 flex items-center justify-center">
              <div className="flex flex-col items-center text-center px-12 py-10 rounded-xl border border-dashed border-gray-200 dark:border-gray-700 bg-white/70 dark:bg-gray-900/30">
                <span className="flex items-center justify-center w-14 h-14 rounded-xl bg-primary-50 text-primary-500 dark:bg-primary-900/30 mb-4">
                  <Database className="w-7 h-7" />
                </span>
                <p className="text-base font-semibold text-gray-700 dark:text-gray-200 mb-1">Gestion des templates DataSource</p>
                <p className="text-sm text-gray-400 mb-6">Sélectionnez un template ou créez-en un nouveau</p>
                <button onClick={handleNewTemplate} className="btn-primary">
                  <Plus className="w-4 h-4 mr-2" />
                  Creer un Template
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Assistant visuel de requête */}
      <QueryBuilder
        isOpen={showQueryBuilder}
        onClose={() => setShowQueryBuilder(false)}
        targetType="template"
        initialSql={formData.query_template}
        onUseQuery={(sql, params) => {
          setFormData((fd) => {
            const next = { ...fd, query_template: sql }
            // Renseigner aussi le bloc Parametres (JSON) a partir des @param detectes
            if (params && params.length > 0) {
              next.parameters = JSON.stringify(
                params.map((p) => ({
                  name: p.name,
                  type: p.type,
                  label: p.label,
                  required: p.required !== false,
                  ...(p.defaultValue ? { default: p.defaultValue } : {}),
                  ...(p.source && p.source !== 'manual' ? { source: p.source } : {}),
                })),
                null,
                2
              )
            }
            return next
          })
          setEditMode(true)
        }}
      />
    </div>
  )
}
