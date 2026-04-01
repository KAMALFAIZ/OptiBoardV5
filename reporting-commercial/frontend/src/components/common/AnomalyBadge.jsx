import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, X, ChevronDown, ChevronUp, Zap, Settings2 } from 'lucide-react'
import api from '../../services/api'

// Presets de sensibilité
const SENSITIVITY_PRESETS = {
  high: {
    label: 'Élevée',
    zscore_critical: 2.0,
    zscore_warning: 1.5,
    iqr_multiplier: 1.2,
    min_rows: 3,
    description: 'Détecte plus d\'anomalies (seuils bas)',
  },
  normal: {
    label: 'Normale',
    zscore_critical: 3.0,
    zscore_warning: 2.5,
    iqr_multiplier: 2.0,
    min_rows: 5,
    description: 'Équilibre précision / rappel',
  },
  low: {
    label: 'Faible',
    zscore_critical: 4.0,
    zscore_warning: 3.5,
    iqr_multiplier: 3.0,
    min_rows: 8,
    description: 'Uniquement les anomalies extrêmes',
  },
  custom: {
    label: 'Personnalisé',
    zscore_critical: 3.0,
    zscore_warning: 2.5,
    iqr_multiplier: 2.0,
    min_rows: 5,
    description: 'Réglage manuel des seuils',
  },
}

/**
 * Badge + panneau de détection d'anomalies statistiques.
 * Props:
 *   data         — données brutes du rapport (array)
 *   columnsInfo  — config colonnes [{field, header}]
 *   onAnomaliesLoaded — callback(anomalyRowIndexSet) pour highlight AG Grid
 */
export default function AnomalyBadge({ data, columnsInfo, onAnomaliesLoaded }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [expandedRows, setExpandedRows] = useState({})

  // Paramétrage
  const [sensitivity, setSensitivity] = useState('normal')
  const [showSettings, setShowSettings] = useState(false)
  const [customParams, setCustomParams] = useState({
    zscore_critical: 3.0,
    zscore_warning: 2.5,
    iqr_multiplier: 2.0,
    min_rows: 5,
  })

  const getParams = useCallback(() => {
    if (sensitivity === 'custom') return customParams
    return SENSITIVITY_PRESETS[sensitivity]
  }, [sensitivity, customParams])

  const runDetection = useCallback(async (params) => {
    if (!data || data.length === 0) return
    setLoading(true)
    try {
      const p = params || getParams()
      const res = await api.post('/anomalies/detect', {
        data: data.slice(0, 2000),
        columns_info: columnsInfo || [],
        max_anomalies: 50,
        zscore_critical: p.zscore_critical,
        zscore_warning: p.zscore_warning,
        iqr_multiplier: p.iqr_multiplier,
        min_rows: p.min_rows,
      })
      setResult(res.data)
      if (onAnomaliesLoaded && res.data?.anomalies) {
        const indices = new Set(res.data.anomalies.map(a => a.row_index))
        onAnomaliesLoaded(indices)
      }
    } catch (e) {
      console.error('[AnomalyBadge]', e)
    } finally {
      setLoading(false)
    }
  }, [data, columnsInfo, onAnomaliesLoaded, getParams])

  // Lancer la détection automatiquement au chargement des données
  useEffect(() => {
    if (data && data.length >= 3) {
      runDetection()
    }
  }, [data?.length])

  // Relancer quand la sensibilité change
  const handleSensitivityChange = (val) => {
    setSensitivity(val)
    if (val !== 'custom') {
      runDetection(SENSITIVITY_PRESETS[val])
    }
  }

  const handleCustomApply = () => {
    setShowSettings(false)
    runDetection(customParams)
  }

  const summary = result?.summary
  const anomalies = result?.anomalies || []
  const hasCritical = summary?.critical > 0
  const hasAnomalies = summary?.total > 0

  const badgeColor = hasCritical
    ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-700'
    : hasAnomalies
      ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-700'
      : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-700'

  if (!result && !loading) return null

  const currentPreset = SENSITIVITY_PRESETS[sensitivity]

  return (
    <div className="relative">
      <button
        onClick={() => { setOpen(o => !o); setShowSettings(false) }}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${badgeColor} ${loading ? 'opacity-60' : ''}`}
        title="Détection d'anomalies statistiques"
      >
        {loading ? (
          <Zap className="w-3.5 h-3.5 animate-pulse" />
        ) : (
          <AlertTriangle className="w-3.5 h-3.5" />
        )}
        {loading ? 'Analyse...' : hasAnomalies ? `${summary.total} anomalie${summary.total > 1 ? 's' : ''}` : 'OK'}
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>

      {open && result && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => { setOpen(false); setShowSettings(false) }} />
          <div className="absolute right-0 mt-1.5 w-[420px] bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 z-40 overflow-hidden">

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-amber-50 to-red-50 dark:from-amber-900/10 dark:to-red-900/10">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <span className="font-semibold text-gray-800 dark:text-white text-sm">Anomalies détectées</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={(e) => { e.stopPropagation(); setShowSettings(s => !s) }}
                  className={`p-1.5 rounded-lg transition-colors ${showSettings ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
                  title="Paramétrage des seuils"
                >
                  <Settings2 className="w-3.5 h-3.5" />
                </button>
                <button onClick={() => setOpen(false)} className="p-1 rounded text-gray-400 hover:text-gray-600">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Panel paramétrage */}
            {showSettings && (
              <div className="border-b border-gray-200 dark:border-gray-700 bg-indigo-50/50 dark:bg-indigo-900/10 p-4 space-y-3">
                {/* Sélecteur sensibilité */}
                <div>
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">Sensibilité</label>
                  <div className="flex gap-1.5">
                    {Object.entries(SENSITIVITY_PRESETS).map(([key, preset]) => (
                      <button
                        key={key}
                        onClick={() => handleSensitivityChange(key)}
                        className={`flex-1 py-1 px-1.5 rounded-lg text-xs font-medium border transition-colors ${
                          sensitivity === key
                            ? 'bg-indigo-600 text-white border-indigo-600'
                            : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:border-indigo-300'
                        }`}
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>
                  {sensitivity !== 'custom' && (
                    <p className="text-[10px] text-gray-400 mt-1">{currentPreset.description}</p>
                  )}
                </div>

                {/* Seuils personnalisés */}
                {sensitivity === 'custom' && (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-gray-500 dark:text-gray-400 block mb-0.5">Z-score Critique (σ)</label>
                        <input
                          type="number" step="0.1" min="1" max="6"
                          value={customParams.zscore_critical}
                          onChange={e => setCustomParams(p => ({ ...p, zscore_critical: parseFloat(e.target.value) || 3 }))}
                          className="w-full text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-500 dark:text-gray-400 block mb-0.5">Z-score Alerte (σ)</label>
                        <input
                          type="number" step="0.1" min="1" max="6"
                          value={customParams.zscore_warning}
                          onChange={e => setCustomParams(p => ({ ...p, zscore_warning: parseFloat(e.target.value) || 2.5 }))}
                          className="w-full text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-500 dark:text-gray-400 block mb-0.5">Multiplicateur IQR</label>
                        <input
                          type="number" step="0.1" min="0.5" max="5"
                          value={customParams.iqr_multiplier}
                          onChange={e => setCustomParams(p => ({ ...p, iqr_multiplier: parseFloat(e.target.value) || 2 }))}
                          className="w-full text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-500 dark:text-gray-400 block mb-0.5">Lignes min. (stats)</label>
                        <input
                          type="number" step="1" min="3" max="20"
                          value={customParams.min_rows}
                          onChange={e => setCustomParams(p => ({ ...p, min_rows: parseInt(e.target.value) || 5 }))}
                          className="w-full text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                        />
                      </div>
                    </div>
                    <button
                      onClick={handleCustomApply}
                      className="w-full py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700 transition-colors"
                    >
                      Appliquer
                    </button>
                  </div>
                )}

                {/* Seuils actifs (lecture seule pour les presets) */}
                {sensitivity !== 'custom' && (
                  <div className="grid grid-cols-4 gap-1.5 text-center">
                    {[
                      { label: 'Critique', value: `>${currentPreset.zscore_critical}σ` },
                      { label: 'Alerte', value: `>${currentPreset.zscore_warning}σ` },
                      { label: 'IQR ×', value: currentPreset.iqr_multiplier },
                      { label: 'Min lignes', value: currentPreset.min_rows },
                    ].map(item => (
                      <div key={item.label} className="bg-white dark:bg-gray-700 rounded-lg py-1.5 px-1 border border-gray-200 dark:border-gray-600">
                        <div className="text-[10px] text-gray-400">{item.label}</div>
                        <div className="text-xs font-bold text-gray-700 dark:text-gray-200">{item.value}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Résumé compteurs */}
            <div className="px-4 py-3 grid grid-cols-3 gap-2 border-b border-gray-100 dark:border-gray-700">
              <div className="text-center">
                <div className="text-xl font-bold text-gray-800 dark:text-white">{summary.total}</div>
                <div className="text-xs text-gray-400">Total</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-red-600 dark:text-red-400">{summary.critical}</div>
                <div className="text-xs text-gray-400">Critiques</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-amber-600 dark:text-amber-400">{summary.warning}</div>
                <div className="text-xs text-gray-400">Alertes</div>
              </div>
            </div>

            {/* Champs les plus anormaux */}
            {summary.anomalous_fields?.length > 0 && (
              <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700">
                <span className="text-xs text-gray-400">Champs concernés : </span>
                {summary.anomalous_fields.map(f => (
                  <span key={f} className="inline-block text-xs px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 mr-1 mb-1">{f}</span>
                ))}
              </div>
            )}

            {/* Liste anomalies */}
            <div className="max-h-64 overflow-y-auto">
              {anomalies.length === 0 ? (
                <div className="py-6 text-center text-sm text-green-600 dark:text-green-400">
                  ✓ Aucune anomalie détectée
                </div>
              ) : (
                anomalies.map((anomaly, i) => {
                  const isCritical = anomaly.fields.some(f => f.severity === 'critical')
                  const isExpanded = expandedRows[i]
                  return (
                    <div key={i} className="border-b border-gray-100 dark:border-gray-700 last:border-0">
                      <button
                        onClick={() => setExpandedRows(prev => ({ ...prev, [i]: !prev[i] }))}
                        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                      >
                        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isCritical ? 'bg-red-500' : 'bg-amber-400'}`} />
                        <span className="flex-1 text-xs text-gray-600 dark:text-gray-300 truncate">
                          Ligne {anomaly.row_index + 1} — {anomaly.fields.length} champ{anomaly.fields.length > 1 ? 's' : ''} anormal{anomaly.fields.length > 1 ? 's' : ''}
                        </span>
                        <span className={`text-[10px] font-bold px-1.5 rounded ${isCritical ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600'}`}>
                          {isCritical ? 'CRITIQUE' : 'ALERTE'}
                        </span>
                        {isExpanded ? <ChevronUp className="w-3 h-3 text-gray-400 flex-shrink-0" /> : <ChevronDown className="w-3 h-3 text-gray-400 flex-shrink-0" />}
                      </button>

                      {isExpanded && (
                        <div className="px-4 pb-3 space-y-1.5">
                          {anomaly.fields.map((f, j) => (
                            <div key={j} className={`rounded-lg p-2 text-xs ${f.severity === 'critical' ? 'bg-red-50 dark:bg-red-900/20' : 'bg-amber-50 dark:bg-amber-900/20'}`}>
                              <div className="flex items-center justify-between mb-0.5">
                                <span className="font-semibold text-gray-700 dark:text-gray-300">{f.header}</span>
                                <span className={`font-bold ${f.severity === 'critical' ? 'text-red-600' : 'text-amber-600'}`}>
                                  Z={f.zscore > 0 ? '+' : ''}{f.zscore}σ
                                </span>
                              </div>
                              <div className="text-gray-500 dark:text-gray-400">
                                Valeur : <b className="text-gray-700 dark:text-gray-200">{f.value?.toLocaleString('fr-FR')}</b>
                                {' '}· Moy : {f.mean?.toLocaleString('fr-FR')}
                                {' '}· Plage : [{f.expected_range?.[0]?.toLocaleString('fr-FR')} → {f.expected_range?.[1]?.toLocaleString('fr-FR')}]
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex items-center justify-between">
              <p className="text-[10px] text-gray-400">
                Z-score ({'>'}  {getParams().zscore_warning}σ) + IQR × {getParams().iqr_multiplier} · {data?.length?.toLocaleString('fr-FR')} lignes
              </p>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400 font-medium">
                {SENSITIVITY_PRESETS[sensitivity]?.label || 'Personnalisé'}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
