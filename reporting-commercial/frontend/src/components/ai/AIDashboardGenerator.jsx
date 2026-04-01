import { useState } from 'react'
import { X, Sparkles, RefreshCw, AlertCircle, CheckCircle, ChevronDown, ChevronUp, Import } from 'lucide-react'
import { generateDashboardFromAI } from '../../services/api'

const SUGGESTION_PROMPTS = [
  "Dashboard CA mensuel avec Top 10 clients et évolution sur 6 mois",
  "Tableau de bord stock : ruptures, surstock et articles dormants",
  "Dashboard recouvrement : créances échues, balance âgée et top débiteurs",
  "Vue commerciale : CA par article, marge par catalogue et Top vendeurs",
  "Dashboard KPI directeur : CA, marge, nb clients actifs et taux recouvrement",
]

export default function AIDashboardGenerator({ onImport, onClose }) {
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [expandedWidgets, setExpandedWidgets] = useState({})

  const handleGenerate = async () => {
    if (!description.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await generateDashboardFromAI(description.trim())
      if (res.data.success) {
        setResult(res.data)
      } else {
        setError("Erreur lors de la génération. Réessayez.")
      }
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || "Erreur inconnue"
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const toggleWidget = (id) => {
    setExpandedWidgets(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const handleImport = () => {
    if (result?.dashboard) {
      onImport(result.dashboard)
    }
  }

  const widgetCount = result?.dashboard?.widgets?.length || 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900 dark:text-white">Générer un Dashboard par IA</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">Décrivez votre besoin, l'IA crée le dashboard</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

          {/* Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Décrivez votre dashboard
            </label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleGenerate() }}
              placeholder="Ex: Dashboard CA mensuel avec top clients, évolution de la marge et état du stock..."
              rows={3}
              disabled={loading}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent resize-none disabled:opacity-60"
            />
            <p className="text-xs text-gray-400 mt-1">Ctrl+Entrée pour générer</p>
          </div>

          {/* Suggestions */}
          {!result && (
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Suggestions :</p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTION_PROMPTS.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setDescription(s)}
                    disabled={loading}
                    className="px-3 py-1.5 text-xs rounded-lg bg-violet-50 dark:bg-violet-900/20 text-violet-700 dark:text-violet-300 hover:bg-violet-100 dark:hover:bg-violet-900/40 border border-violet-200 dark:border-violet-700 transition-colors disabled:opacity-50"
                  >
                    {s.length > 50 ? s.slice(0, 50) + '…' : s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Erreur */}
          {error && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="w-12 h-12 rounded-full bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
                <RefreshCw className="w-6 h-6 text-violet-600 animate-spin" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Génération en cours...</p>
                <p className="text-xs text-gray-400 mt-1">L'IA analyse votre besoin et construit le dashboard</p>
              </div>
            </div>
          )}

          {/* Résultat */}
          {result && !loading && (
            <div className="space-y-4">
              {/* Résumé */}
              <div className="flex items-start gap-3 p-4 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-green-700 dark:text-green-300">
                    {result.dashboard.nom}
                  </p>
                  <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
                    {result.dashboard.description} — {widgetCount} widget{widgetCount > 1 ? 's' : ''} générés
                  </p>
                  {result.provider && (
                    <p className="text-xs text-green-500 dark:text-green-500 mt-0.5">via {result.provider}</p>
                  )}
                </div>
              </div>

              {/* Warnings */}
              {result.warnings?.length > 0 && (
                <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                  <p className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">Avertissements :</p>
                  {result.warnings.map((w, i) => (
                    <p key={i} className="text-xs text-amber-600 dark:text-amber-400">• {w}</p>
                  ))}
                </div>
              )}

              {/* Liste des widgets */}
              <div>
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                  Widgets générés
                </p>
                <div className="space-y-2">
                  {result.dashboard.widgets.map((widget, i) => (
                    <div key={widget.id || i} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 overflow-hidden">
                      <button
                        onClick={() => toggleWidget(widget.id || i)}
                        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span className="px-2 py-0.5 text-xs rounded-md bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300 font-mono">
                            {widget.type}
                          </span>
                          <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{widget.title}</span>
                          <span className="text-xs text-gray-400">{widget.w}×{widget.h}</span>
                        </div>
                        {expandedWidgets[widget.id || i]
                          ? <ChevronUp className="w-4 h-4 text-gray-400" />
                          : <ChevronDown className="w-4 h-4 text-gray-400" />
                        }
                      </button>
                      {expandedWidgets[widget.id || i] && widget.config?.sql && (
                        <div className="px-4 pb-3">
                          <p className="text-xs font-medium text-gray-500 mb-1">SQL :</p>
                          <pre className="text-xs bg-gray-900 text-green-300 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
                            {widget.config.sql}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex-shrink-0 bg-gray-50 dark:bg-gray-800/50 rounded-b-2xl">
          <div className="flex items-center gap-2">
            {result && (
              <button
                onClick={() => { setResult(null); setError(null) }}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                Regénérer
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              Annuler
            </button>
            {!result ? (
              <button
                onClick={handleGenerate}
                disabled={!description.trim() || loading}
                className="flex items-center gap-2 px-5 py-2 text-sm font-semibold bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-lg hover:from-violet-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
              >
                {loading
                  ? <><RefreshCw className="w-4 h-4 animate-spin" />Génération...</>
                  : <><Sparkles className="w-4 h-4" />Générer</>
                }
              </button>
            ) : (
              <button
                onClick={handleImport}
                className="flex items-center gap-2 px-5 py-2 text-sm font-semibold bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all shadow-sm"
              >
                <CheckCircle className="w-4 h-4" />
                Importer dans le Builder
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
