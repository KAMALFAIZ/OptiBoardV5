import { useState, useCallback } from 'react'
import { Sparkles, X, RefreshCw, TrendingUp, AlertTriangle, Lightbulb, BarChart2, AlertCircle, ArrowUpDown, ChevronDown, ChevronUp } from 'lucide-react'
import api from '../../services/api'

// Icônes et couleurs par type d'insight
const INSIGHT_CONFIG = {
  tendance:    { icon: TrendingUp,   color: 'text-blue-600 dark:text-blue-400',   bg: 'bg-blue-50 dark:bg-blue-900/20',   border: 'border-blue-100 dark:border-blue-800/30',   label: 'Tendance' },
  alerte:      { icon: AlertTriangle, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-100 dark:border-amber-800/30', label: 'Alerte' },
  performance: { icon: BarChart2,    color: 'text-green-600 dark:text-green-400',  bg: 'bg-green-50 dark:bg-green-900/20',  border: 'border-green-100 dark:border-green-800/30',  label: 'Performance' },
  conseil:     { icon: Lightbulb,    color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-100 dark:border-purple-800/30', label: 'Conseil' },
  anomalie:    { icon: AlertCircle,  color: 'text-red-600 dark:text-red-400',     bg: 'bg-red-50 dark:bg-red-900/20',     border: 'border-red-100 dark:border-red-800/30',     label: 'Anomalie' },
  comparaison: { icon: ArrowUpDown,  color: 'text-indigo-600 dark:text-indigo-400', bg: 'bg-indigo-50 dark:bg-indigo-900/20', border: 'border-indigo-100 dark:border-indigo-800/30', label: 'Comparaison' },
}

const DEFAULT_CONFIG = INSIGHT_CONFIG.conseil

function InsightCard({ insight }) {
  const cfg = INSIGHT_CONFIG[insight.type] || DEFAULT_CONFIG
  const Icon = cfg.icon
  return (
    <div className={`flex items-start gap-2.5 p-2.5 rounded-lg border ${cfg.bg} ${cfg.border}`}>
      <Icon className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${cfg.color}`} />
      <div className="flex-1 min-w-0">
        <span className={`text-[10px] font-semibold uppercase tracking-wide ${cfg.color}`}>{cfg.label}</span>
        <p className="text-xs text-gray-700 dark:text-gray-300 mt-0.5 leading-snug">{insight.texte}</p>
      </div>
    </div>
  )
}

/**
 * Panneau d'insights IA flottant/collapsible.
 * Props:
 *   reportType: "gridview" | "dashboard" | "pivot"
 *   reportId: number
 *   reportNom: string
 *   data: Array<Object>        — données brutes du rapport
 *   columnsInfo: Array<Object> — config des colonnes (field, header)
 *   context: string            — contexte métier optionnel
 */
export default function InsightsPanel({ reportType, reportId, reportNom, data, columnsInfo, context }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [insights, setInsights] = useState([])
  const [error, setError] = useState(null)
  const [meta, setMeta] = useState(null)
  const [generated, setGenerated] = useState(false)

  const generate = useCallback(async (forceRefresh = false) => {
    if (!data || data.length === 0) {
      setError('Aucune donnée disponible à analyser')
      return
    }
    setLoading(true)
    setError(null)

    try {
      const res = await api.post('/ai-insights/generate', {
        report_type: reportType,
        report_id: reportId,
        report_nom: reportNom,
        data: data.slice(0, 500),   // max 500 lignes envoyées
        columns_info: columnsInfo || [],
        context: context || null,
        force_refresh: forceRefresh
      })

      if (res.data.success) {
        setInsights(res.data.insights || [])
        setMeta({
          provider: res.data.provider,
          fromCache: res.data.from_cache,
          cacheAge: res.data.cache_age_minutes,
          nbLignes: res.data.nb_lignes_analysees
        })
        setGenerated(true)
      } else {
        setError(res.data.error || 'Erreur de génération')
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }, [reportType, reportId, reportNom, data, columnsInfo, context])

  const handleToggle = () => {
    if (!open && !generated && !loading) {
      generate()
    }
    setOpen(prev => !prev)
  }

  return (
    <div className="relative">
      {/* Bouton déclencheur */}
      <button
        onClick={handleToggle}
        disabled={loading && !open}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
          open || generated
            ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-700'
            : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-purple-50 dark:hover:bg-purple-900/20 hover:text-purple-600 dark:hover:text-purple-400'
        }`}
        title="Insights IA automatiques"
      >
        <Sparkles className={`w-3.5 h-3.5 ${loading ? 'animate-pulse' : ''}`} />
        <span className="hidden sm:inline">Insights IA</span>
        {insights.length > 0 && (
          <span className="px-1.5 py-0.5 rounded-full bg-purple-500 text-white text-[10px] font-bold">{insights.length}</span>
        )}
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>

      {/* Panneau déroulant */}
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1.5 w-80 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 z-40 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2.5 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 border-b border-purple-100 dark:border-purple-800/30">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-500" />
                <span className="text-sm font-semibold text-gray-800 dark:text-white">Insights IA</span>
              </div>
              <div className="flex items-center gap-1">
                {generated && (
                  <button
                    onClick={() => generate(true)}
                    disabled={loading}
                    className="p-1 rounded text-gray-400 hover:text-purple-500 transition-colors disabled:opacity-40"
                    title="Regénérer"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                  </button>
                )}
                <button onClick={() => setOpen(false)} className="p-1 rounded text-gray-400 hover:text-gray-600 transition-colors">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Contenu */}
            <div className="p-3 max-h-96 overflow-y-auto">
              {loading ? (
                <div className="text-center py-8">
                  <Sparkles className="w-8 h-8 text-purple-400 mx-auto mb-2 animate-pulse" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">Analyse en cours...</p>
                  <p className="text-xs text-gray-400 mt-1">L'IA analyse vos données</p>
                </div>
              ) : error ? (
                <div className="text-center py-6">
                  <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
                  <p className="text-xs text-red-500">{error}</p>
                  <button onClick={() => generate()} className="mt-3 text-xs text-purple-600 hover:text-purple-800 underline">
                    Réessayer
                  </button>
                </div>
              ) : insights.length === 0 ? (
                <div className="text-center py-6">
                  <p className="text-xs text-gray-400">Aucun insight généré</p>
                  <button onClick={() => generate()} className="mt-2 text-xs text-purple-600 hover:text-purple-800 underline">
                    Générer
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {insights.map((insight, i) => (
                    <InsightCard key={i} insight={insight} />
                  ))}
                </div>
              )}
            </div>

            {/* Footer méta */}
            {meta && !loading && (
              <div className="px-3 py-2 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                <p className="text-[10px] text-gray-400 dark:text-gray-500">
                  {meta.fromCache
                    ? `Depuis le cache (${meta.cacheAge} min) — ${meta.provider}`
                    : `Généré par ${meta.provider}`
                  }
                  {meta.nbLignes && ` · ${meta.nbLignes} lignes analysées`}
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
