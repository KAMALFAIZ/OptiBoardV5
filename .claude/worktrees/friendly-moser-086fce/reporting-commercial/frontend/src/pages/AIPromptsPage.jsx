import { useState, useEffect, useCallback } from 'react'
import { MessageSquare, Save, RotateCcw, Eye, EyeOff, CheckCircle, AlertCircle, Pencil, ChevronDown, ChevronUp, Sparkles } from 'lucide-react'
import api from '../services/api'

const getUserHeader = () => {
  try {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    return user.id ? { 'X-User-Id': String(user.id) } : {}
  } catch { return {} }
}

const SECTION_ICONS = {
  business_context: '🏢',
  sql_rules: '⚙️',
  mode_chat: '💬',
  mode_sql: '🗄️',
  mode_help: '❓',
  custom_instructions: '✨',
}

export default function AIPromptsPage() {
  const [prompts, setPrompts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editingCode, setEditingCode] = useState(null)
  const [editContent, setEditContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState({}) // { code: 'ok' | 'error' }
  const [expandedCode, setExpandedCode] = useState(null)
  const [showPreview, setShowPreview] = useState(false)
  const [preview, setPreview] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewMeta, setPreviewMeta] = useState({})
  const [showDiff, setShowDiff] = useState({}) // { code: bool }

  const headers = getUserHeader()

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.get('/ai/prompts/', { headers })
      setPrompts(res.data.prompts || [])
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const startEdit = (prompt) => {
    setEditingCode(prompt.code)
    setEditContent(prompt.contenu)
    setExpandedCode(prompt.code)
  }

  const cancelEdit = () => {
    setEditingCode(null)
    setEditContent('')
  }

  const handleSave = async (code) => {
    setSaving(true)
    try {
      await api.put(`/ai/prompts/${code}`, { contenu: editContent }, { headers })
      setSaveStatus(p => ({ ...p, [code]: 'ok' }))
      setEditingCode(null)
      setPrompts(prev => prev.map(p => p.code === code
        ? { ...p, contenu: editContent, is_customized: true }
        : p
      ))
      setTimeout(() => setSaveStatus(p => { const n = { ...p }; delete n[code]; return n }), 3000)
    } catch (e) {
      setSaveStatus(p => ({ ...p, [code]: 'error' }))
      setTimeout(() => setSaveStatus(p => { const n = { ...p }; delete n[code]; return n }), 4000)
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async (code) => {
    if (!confirm('Remettre ce prompt à sa valeur par défaut ?')) return
    try {
      await api.delete(`/ai/prompts/${code}/reset`, { headers })
      const prompt = prompts.find(p => p.code === code)
      setPrompts(prev => prev.map(p => p.code === code
        ? { ...p, contenu: p.default_contenu, is_customized: false }
        : p
      ))
      if (editingCode === code) {
        setEditContent(prompt?.default_contenu || '')
      }
    } catch (e) {
      alert('Erreur: ' + (e.response?.data?.detail || e.message))
    }
  }

  const loadPreview = async () => {
    setPreviewLoading(true)
    try {
      const dwhHeaders = { ...headers }
      try {
        const dwh = JSON.parse(localStorage.getItem('currentDWH') || '{}')
        if (dwh?.code) dwhHeaders['X-DWH-Code'] = dwh.code
      } catch { /* ignore */ }
      const res = await api.get('/ai/prompts/preview', { headers: dwhHeaders })
      setPreview(res.data.preview || '')
      setPreviewMeta({
        chars: res.data.char_count || 0,
        tokens: res.data.token_estimate || 0,
        dwh: res.data.dwh_code || '—',
        libraryEntries: res.data.sections?.library_entries || 0,
      })
      setShowPreview(true)
    } catch (e) {
      alert('Erreur: ' + (e.response?.data?.detail || e.message))
    } finally {
      setPreviewLoading(false)
    }
  }

  const charCount = editContent.length
  const wordCount = editContent.trim() ? editContent.trim().split(/\s+/).length : 0

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
            <MessageSquare className="w-5 h-5 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Gestion des Prompts IA</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Personnalisez le comportement de l'assistant IA</p>
          </div>
        </div>
        <button
          onClick={loadPreview}
          disabled={previewLoading}
          className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium border border-violet-300 dark:border-violet-700 text-violet-600 dark:text-violet-400 hover:bg-violet-50 dark:hover:bg-violet-900/20 rounded-lg transition-colors disabled:opacity-50"
        >
          {showPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          {previewLoading ? 'Chargement...' : showPreview ? 'Masquer aperçu' : 'Aperçu complet'}
        </button>
      </div>

      {/* Info banner */}
      <div className="mb-5 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 text-sm text-blue-700 dark:text-blue-300">
        <strong>💡 Comment ça marche :</strong> Chaque section est injectée dans le prompt système envoyé au LLM.
        Les modifications sont actives immédiatement (cache 60s). Les sections non modifiées utilisent les valeurs par défaut.
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Aperçu complet */}
      {showPreview && preview && (
        <div className="mb-5 rounded-xl border border-violet-200 dark:border-violet-800 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 bg-violet-50 dark:bg-violet-900/20">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-sm font-medium text-violet-700 dark:text-violet-300">
                Aperçu du Prompt Complet
              </span>
              {previewMeta.chars > 0 && (
                <div className="flex items-center gap-2 text-[11px] text-violet-500 dark:text-violet-400">
                  <span className="px-1.5 py-0.5 bg-violet-100 dark:bg-violet-900/40 rounded-full">{previewMeta.chars.toLocaleString()} car.</span>
                  <span className="px-1.5 py-0.5 bg-violet-100 dark:bg-violet-900/40 rounded-full">~{previewMeta.tokens.toLocaleString()} tokens</span>
                  <span className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded-full">DWH: {previewMeta.dwh}</span>
                  <span className="px-1.5 py-0.5 bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400 rounded-full">{previewMeta.libraryEntries} ex. library</span>
                </div>
              )}
            </div>
            <button onClick={() => setShowPreview(false)} className="text-xs text-violet-500 hover:text-violet-700">Fermer</button>
          </div>
          <pre className="p-4 text-xs font-mono bg-gray-950 text-gray-300 overflow-auto max-h-80 whitespace-pre-wrap">
            {preview}
          </pre>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12 text-gray-400">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-violet-500 mr-3" />
          Chargement...
        </div>
      )}

      {/* Sections */}
      {!loading && (
        <div className="space-y-3">
          {prompts.map(prompt => {
            const isEditing = editingCode === prompt.code
            const isExpanded = expandedCode === prompt.code
            const status = saveStatus[prompt.code]

            return (
              <div key={prompt.code}
                className={`bg-white dark:bg-gray-800 rounded-xl border transition-all
                  ${isEditing ? 'border-violet-400 dark:border-violet-600 shadow-md shadow-violet-100 dark:shadow-violet-900/20' : 'border-gray-200 dark:border-gray-700'}`}>

                {/* Header section */}
                <div className="flex items-center gap-3 p-4">
                  <span className="text-xl">{SECTION_ICONS[prompt.code] || '📝'}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">{prompt.nom}</span>
                      {prompt.is_customized && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 rounded-full">
                          Personnalisé
                        </span>
                      )}
                      {status === 'ok' && <CheckCircle className="w-4 h-4 text-green-500" />}
                      {status === 'error' && <AlertCircle className="w-4 h-4 text-red-500" />}
                    </div>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{prompt.description}</p>
                    {prompt.updated_at && prompt.is_customized && (
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        Modifié {prompt.updated_at ? new Date(prompt.updated_at).toLocaleString('fr-FR') : ''}
                        {prompt.updated_by ? ` par ${prompt.updated_by}` : ''}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {!isEditing && (
                      <>
                        {prompt.is_customized && (
                          <button onClick={() => handleReset(prompt.code)} title="Remettre par défaut"
                            className="p-1.5 text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors">
                            <RotateCcw className="w-4 h-4" />
                          </button>
                        )}
                        <button onClick={() => startEdit(prompt)} title="Modifier"
                          className="p-1.5 text-violet-500 hover:bg-violet-50 dark:hover:bg-violet-900/20 rounded-lg transition-colors">
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button onClick={() => setExpandedCode(isExpanded ? null : prompt.code)} title="Aperçu"
                          className="p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Contenu — aperçu ou éditeur */}
                {(isExpanded || isEditing) && (
                  <div className="border-t border-gray-100 dark:border-gray-700 px-4 pb-4 pt-3">
                    {isEditing ? (
                      <>
                        <textarea
                          value={editContent}
                          onChange={e => setEditContent(e.target.value)}
                          rows={prompt.code === 'sql_rules' ? 14 : 8}
                          className="w-full px-3 py-2.5 text-sm font-mono bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 resize-y"
                          placeholder={prompt.code === 'custom_instructions' ? 'Laissez vide pour désactiver...' : ''}
                        />
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-[11px] text-gray-400">
                            {charCount.toLocaleString()} caractères · {wordCount} mots
                          </span>
                          <div className="flex gap-2">
                            <button onClick={cancelEdit}
                              className="px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                              Annuler
                            </button>
                            {prompt.is_customized && (
                              <button onClick={() => handleReset(prompt.code)}
                                className="px-3 py-1.5 text-xs text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors flex items-center gap-1">
                                <RotateCcw className="w-3 h-3" /> Défaut
                              </button>
                            )}
                            <button onClick={() => handleSave(prompt.code)} disabled={saving}
                              className="px-3 py-1.5 text-xs font-medium bg-violet-600 hover:bg-violet-700 text-white rounded-lg disabled:opacity-50 transition-colors flex items-center gap-1">
                              <Save className="w-3 h-3" /> {saving ? 'Sauvegarde...' : 'Sauvegarder'}
                            </button>
                          </div>
                        </div>
                      </>
                    ) : (
                      <pre className="text-xs font-mono bg-gray-50 dark:bg-gray-900 text-gray-600 dark:text-gray-400 p-3 rounded-lg overflow-auto max-h-48 whitespace-pre-wrap">
                        {prompt.contenu || <span className="italic text-gray-400">Vide (désactivé)</span>}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Legend */}
      {!loading && (
        <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">Ordre d'assemblage du prompt système :</p>
          <div className="flex flex-wrap gap-2 text-[11px]">
            {['🏢 Contexte Métier', '📊 Schéma DWH (auto)', '🔍 Exemples RAG (library)', '📚 Exemples statiques', '⚙️ Règles SQL', '✨ Instructions custom', '💬/🗄️/❓ Mode actif'].map(s => (
              <span key={s} className="px-2 py-1 bg-white dark:bg-gray-800 rounded-full border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
