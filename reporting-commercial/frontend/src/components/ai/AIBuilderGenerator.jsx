import { useState } from 'react'
import { X, Sparkles, RefreshCw, AlertCircle, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { generatePivotFromAI, generateGridViewFromAI } from '../../services/api'

const CONFIGS = {
  pivot: {
    title: 'Générer un Pivot par IA',
    subtitle: "Décrivez votre analyse, l'IA configure le tableau croisé",
    generateFn: generatePivotFromAI,
    resultKey: 'pivot',
    suggestions: [
      "CA mensuel par client avec marge et taux de marge",
      "Analyse des ventes par article et catalogue, comparaison N vs N-1",
      "Recouvrement : créances par client avec balance âgée (0-30, 31-60, +90j)",
      "Stock dormant par famille et dépôt avec valeur",
      "Top collaborateurs : CA, marge et nombre de factures par commercial",
    ],
    previewFields: (data) => [
      { label: 'Lignes', value: (data.rows_config || []).map(r => r.label || r.field).join(', ') || '—' },
      { label: 'Colonnes', value: (data.columns_config || []).map(c => c.label || c.field).join(', ') || 'Aucune' },
      { label: 'Valeurs', value: (data.values_config || []).map(v => `${v.label || v.field} (${v.aggregate || 'SUM'})`).join(', ') || '—' },
      { label: 'Comparaison', value: data.comparison_mode || 'Aucune' },
    ],
  },
  gridview: {
    title: 'Générer une Grille par IA',
    subtitle: "Décrivez votre besoin, l'IA crée la grille de données",
    generateFn: generateGridViewFromAI,
    resultKey: 'gridview',
    suggestions: [
      "Liste des ventes avec client, article, montant HT et marge",
      "État du stock par article avec quantité, valeur et alertes rupture",
      "Créances non réglées avec client, échéance et jours de retard",
      "Top 100 articles vendus cette année avec CA et taux de marge",
      "Mouvements de stock récents avec date, type et quantité",
    ],
    previewFields: (data) => [
      { label: 'Colonnes', value: `${(data.columns || []).length} colonne(s)` },
      { label: 'Page', value: `${data.page_size || 25} lignes / page` },
      { label: 'Totaux', value: data.show_totals ? 'Activés' : 'Désactivés' },
    ],
  },
}

export default function AIBuilderGenerator({ mode, onImport, onClose }) {
  const cfg = CONFIGS[mode]
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [showSql, setShowSql] = useState(false)

  const handleGenerate = async () => {
    if (!description.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await cfg.generateFn(description.trim())
      if (res.data.success) {
        setResult(res.data)
      } else {
        setError('Erreur lors de la génération. Réessayez.')
      }
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur inconnue')
    } finally {
      setLoading(false)
    }
  }

  const data = result?.[cfg.resultKey]
  const previewFields = data ? cfg.previewFields(data) : []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-xl flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900 dark:text-white">{cfg.title}</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">{cfg.subtitle}</p>
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
              Décrivez votre analyse
            </label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleGenerate() }}
              placeholder="Ex: Analyse CA mensuel par client avec marge et comparaison N vs N-1..."
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
                {cfg.suggestions.map((s, i) => (
                  <button key={i} onClick={() => setDescription(s)} disabled={loading}
                    className="px-3 py-1.5 text-xs rounded-lg bg-violet-50 dark:bg-violet-900/20 text-violet-700 dark:text-violet-300 hover:bg-violet-100 dark:hover:bg-violet-900/40 border border-violet-200 dark:border-violet-700 transition-colors disabled:opacity-50">
                    {s.length > 55 ? s.slice(0, 55) + '…' : s}
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
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Génération en cours...</p>
              <p className="text-xs text-gray-400">L'IA analyse votre besoin et configure la structure</p>
            </div>
          )}

          {/* Résultat */}
          {result && !loading && data && (
            <div className="space-y-4">
              {/* Résumé */}
              <div className="flex items-start gap-3 p-4 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-green-700 dark:text-green-300">{data.nom}</p>
                  {data.description && (
                    <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">{data.description}</p>
                  )}
                  {result.provider && (
                    <p className="text-xs text-green-500 mt-0.5">via {result.provider}</p>
                  )}
                </div>
              </div>

              {/* Warnings */}
              {result.warnings?.length > 0 && (
                <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                  {result.warnings.map((w, i) => (
                    <p key={i} className="text-xs text-amber-600 dark:text-amber-400">⚠ {w}</p>
                  ))}
                </div>
              )}

              {/* Champs de config */}
              <div className="grid grid-cols-2 gap-3">
                {previewFields.map((f, i) => (
                  <div key={i} className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{f.label}</p>
                    <p className="text-xs text-gray-800 dark:text-gray-200 font-medium truncate" title={f.value}>{f.value}</p>
                  </div>
                ))}
              </div>

              {/* SQL généré */}
              {data.sql && (
                <div>
                  <button onClick={() => setShowSql(!showSql)}
                    className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
                    {showSql ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    {showSql ? 'Masquer' : 'Voir'} le SQL généré
                  </button>
                  {showSql && (
                    <pre className="mt-2 text-xs bg-gray-900 text-green-300 p-3 rounded-xl overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
                      {data.sql}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex-shrink-0 bg-gray-50 dark:bg-gray-800/50 rounded-b-2xl">
          <div>
            {result && (
              <button onClick={() => { setResult(null); setError(null) }}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors">
                Regénérer
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors">
              Annuler
            </button>
            {!result ? (
              <button onClick={handleGenerate} disabled={!description.trim() || loading}
                className="flex items-center gap-2 px-5 py-2 text-sm font-semibold bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-lg hover:from-violet-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm">
                {loading
                  ? <><RefreshCw className="w-4 h-4 animate-spin" />Génération...</>
                  : <><Sparkles className="w-4 h-4" />Générer</>
                }
              </button>
            ) : (
              <button onClick={() => onImport(data)}
                className="flex items-center gap-2 px-5 py-2 text-sm font-semibold bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all shadow-sm">
                <CheckCircle className="w-4 h-4" />
                Importer
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
