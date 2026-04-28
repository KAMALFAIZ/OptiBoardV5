import { useState, useEffect } from 'react'
import {
  Database, Plus, Save, Trash2, Play, RefreshCw, X, Search,
  Code, FileText, Tag, CheckCircle, XCircle, AlertCircle,
  Eye, EyeOff, Copy, Settings2, Loader2, Filter, ChevronDown, ChevronRight,
  Shield
} from 'lucide-react'
import api, { extractErrorMessage } from '../services/api'
import { useAuth } from '../context/AuthContext'

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
  const isSuperAdmin = user?.role === 'superadmin'

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

  // Filtres
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
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
          <div className="w-8 h-8 rounded-xl bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
            <Database className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          </div>
          <h1 className="text-sm font-bold text-gray-900 dark:text-white">DataSources Templates</h1>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadData}
            className="p-1.5 rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors" title="Actualiser">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button onClick={handleNewTemplate}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-primary-600 text-white hover:bg-primary-700 transition-colors">
            <Plus className="w-3.5 h-3.5" />
            Nouveau Template
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="mx-4 mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {success && (
        <div className="mx-4 mt-3 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-2 text-green-600 dark:text-green-400">
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} className="ml-auto text-green-400 hover:text-green-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Liste des templates */}
        <div className="w-72 bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 flex flex-col">
          {/* Filtres */}
          <div className="px-4 pt-4 pb-3 border-b border-gray-100 dark:border-gray-800">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[11px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">Templates</h2>
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
                className="w-full pl-8 pr-7 py-2 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-transparent dark:text-white placeholder-gray-400 outline-none transition-all"
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
              className="w-full px-2.5 py-2 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl dark:text-white focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none transition-all"
            >
              {CATEGORIES.map(c => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          {/* Liste groupee */}
          <div className="flex-1 overflow-y-auto">
            {Object.keys(groupedTemplates).length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                <Database className="w-12 h-12 mx-auto mb-2 opacity-30" />
                <p className="text-sm">Aucun template trouve</p>
              </div>
            ) : (
              Object.entries(groupedTemplates).map(([category, items]) => (
                <div key={category}>
                  <button
                    onClick={() => toggleCategory(category)}
                    className="w-full px-3 py-2 flex items-center justify-between text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      {expandedCategories[category] ? (
                        <ChevronDown className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5" />
                      )}
                      {CATEGORIES.find(c => c.value === category)?.label || category}
                    </span>
                    <span className="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full font-medium">
                      {items.length}
                    </span>
                  </button>

                  {expandedCategories[category] && (
                    <div className="pb-1">
                      {items.map(template => (
                        <div
                          key={template.id}
                          onClick={() => handleSelectTemplate(template)}
                          className={`
                            mx-1 px-3 py-2.5 rounded-xl cursor-pointer text-xs transition-all mb-0.5
                            ${selectedTemplate?.id === template.id
                              ? 'bg-primary-50 dark:bg-primary-900/20 shadow-sm ring-1 ring-primary-200 dark:ring-primary-800'
                              : 'hover:bg-gray-50 dark:hover:bg-gray-800/60'
                            }
                          `}
                        >
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
                              <span className="text-[10px] bg-red-100 dark:bg-red-900/30 text-red-600 px-1 rounded">
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
          <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-800 text-[11px] text-gray-400 dark:text-gray-500">
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
                  <h2 className="font-semibold text-gray-900 dark:text-white">
                    {editMode ? (selectedTemplate ? 'Modifier Template' : 'Nouveau Template') : 'Details'}
                  </h2>
                  {selectedTemplate?.is_system && !editMode && (
                    <span className="text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded-full flex items-center gap-1">
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
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition-colors"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        Dupliquer
                      </button>
                      <button
                        onClick={() => setEditMode(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition-colors disabled:opacity-50"
                        disabled={selectedTemplate?.is_system && !isSuperAdmin}
                        title={selectedTemplate?.is_system && !isSuperAdmin ? "Seuls les superadmin peuvent modifier les templates systeme" : ""}
                      >
                        {selectedTemplate?.is_system && isSuperAdmin && <Shield className="w-3.5 h-3.5 text-amber-500" />}
                        <Settings2 className="w-3.5 h-3.5" />
                        Modifier
                      </button>
                      <button
                        onClick={handleDelete}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 hover:bg-red-100 rounded-xl transition-colors disabled:opacity-50"
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
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition-colors disabled:opacity-50"
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
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition-colors"
                      >
                        Annuler
                      </button>
                      <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-primary-600 text-white hover:bg-primary-700 rounded-xl transition-colors shadow-sm disabled:opacity-50"
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
                <div className="max-w-4xl mx-auto space-y-6">
                  {/* Infos de base */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                      <FileText className="w-5 h-5" />
                      Informations
                    </h3>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Code <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={formData.code}
                          onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, '') })}
                          disabled={!editMode || (selectedTemplate && selectedTemplate.is_system)}
                          placeholder="DS_VENTES_GLOBAL"
                          className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 disabled:opacity-50"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Nom <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={formData.nom}
                          onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                          disabled={!editMode}
                          placeholder="Ventes Globales"
                          className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 disabled:opacity-50"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Type
                        </label>
                        <select
                          value={formData.type}
                          onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                          disabled={!editMode}
                          className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 disabled:opacity-50"
                        >
                          {TYPES.map(t => (
                            <option key={t.value} value={t.value}>{t.label}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Categorie
                        </label>
                        <select
                          value={formData.category}
                          onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                          disabled={!editMode}
                          className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 disabled:opacity-50"
                        >
                          {CATEGORIES.filter(c => c.value).map(c => (
                            <option key={c.value} value={c.value}>{c.label}</option>
                          ))}
                        </select>
                      </div>

                      <div className="col-span-2">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Description
                        </label>
                        <textarea
                          value={formData.description}
                          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                          disabled={!editMode}
                          rows={2}
                          placeholder="Description du template..."
                          className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 disabled:opacity-50"
                        />
                      </div>

                      <div className="col-span-2 flex items-center gap-6">
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={formData.actif}
                            onChange={(e) => setFormData({ ...formData, actif: e.target.checked })}
                            disabled={!editMode}
                            className="rounded border-primary-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span className="text-sm text-gray-700 dark:text-gray-300">Actif</span>
                        </label>

                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={formData.is_system}
                            onChange={(e) => setFormData({ ...formData, is_system: e.target.checked })}
                            disabled={!editMode || (selectedTemplate && selectedTemplate.is_system)}
                            className="rounded border-primary-300 text-amber-600 focus:ring-amber-500"
                          />
                          <span className="text-sm text-gray-700 dark:text-gray-300">Template Systeme (protege)</span>
                        </label>
                      </div>
                    </div>
                  </div>

                  {/* Requete SQL */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                      <Code className="w-5 h-5" />
                      Requete SQL
                    </h3>

                    <textarea
                      value={formData.query_template}
                      onChange={(e) => setFormData({ ...formData, query_template: e.target.value })}
                      disabled={!editMode}
                      rows={12}
                      placeholder="SELECT * FROM ma_table WHERE @dateDebut <= date AND date <= @dateFin"
                      className="w-full px-3 py-2 font-mono text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-900 disabled:opacity-50"
                      style={{ tabSize: 2 }}
                    />

                    <p className="text-xs text-gray-500 mt-2">
                      Utilisez @parametre pour les parametres dynamiques (ex: @dateDebut, @dateFin, @societe, @societe_filter)
                    </p>
                  </div>

                  {/* Parametres */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                      <Tag className="w-5 h-5" />
                      Parametres (JSON)
                    </h3>

                    <textarea
                      value={formData.parameters}
                      onChange={(e) => setFormData({ ...formData, parameters: e.target.value })}
                      disabled={!editMode}
                      rows={8}
                      placeholder='[{"name": "@dateDebut", "type": "date", "label": "Date Debut", "required": true}]'
                      className="w-full px-3 py-2 font-mono text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-900 disabled:opacity-50"
                    />

                    <div className="text-xs text-gray-500 mt-2 space-y-1">
                      <p>Format: Liste de parametres avec les proprietes:</p>
                      <code className="block bg-gray-100 dark:bg-gray-900 p-2 rounded">
                        {`{"name": "@param", "type": "date|text|number|select", "label": "Label", "required": true, "default": "valeur"}`}
                      </code>
                    </div>
                  </div>

                  {/* Resultat du test */}
                  {testResult && (
                    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border ${
                      testResult.success
                        ? 'border-green-200 dark:border-green-800'
                        : 'border-red-200 dark:border-red-800'
                    } p-6`}>
                      <h3 className={`text-lg font-semibold mb-4 flex items-center gap-2 ${
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
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-50 dark:bg-gray-700">
                              <tr>
                                {testResult.data[0] && Object.keys(testResult.data[0]).map(col => (
                                  <th key={col} className="px-3 py-2 text-left font-medium text-gray-600 dark:text-gray-300">
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
                        <p className="text-red-600 dark:text-red-400 font-mono text-sm">
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
              <div className="text-center text-gray-500">
                <Database className="w-16 h-16 mx-auto mb-4 opacity-30" />
                <p className="text-lg font-medium mb-2">Gestion des Templates DataSource</p>
                <p className="text-sm mb-4">Selectionnez un template ou creez-en un nouveau</p>
                <button onClick={handleNewTemplate} className="btn-primary">
                  <Plus className="w-4 h-4 mr-2" />
                  Creer un Template
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
