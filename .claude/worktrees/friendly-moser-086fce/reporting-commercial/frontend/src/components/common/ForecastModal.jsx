import { useState, useEffect, useMemo } from 'react'
import { X, TrendingUp, TrendingDown, Minus, ChevronDown, BarChart2 } from 'lucide-react'
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine
} from 'recharts'
import api from '../../services/api'

const METHOD_OPTIONS = [
  { value: 'auto', label: 'Auto (meilleure méthode)' },
  { value: 'linear', label: 'Régression linéaire' },
  { value: 'moving_avg', label: 'Moyenne mobile pondérée' },
  { value: 'holt', label: 'Lissage exponentiel (Holt)' },
]

const PERIOD_OPTIONS = [3, 6, 9, 12]

const METHOD_LABELS = {
  linear: 'Régression linéaire',
  moving_avg: 'Moy. mobile pondérée',
  holt: 'Lissage Holt',
}

function TrendIcon({ trend }) {
  if (trend === 'up') return <TrendingUp className="w-4 h-4 text-green-500" />
  if (trend === 'down') return <TrendingDown className="w-4 h-4 text-red-500" />
  return <Minus className="w-4 h-4 text-gray-400" />
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg p-3 text-xs">
      <p className="font-semibold text-gray-700 dark:text-gray-300 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="leading-5">
          {p.name}: <b>{typeof p.value === 'number' ? p.value?.toLocaleString('fr-FR', { maximumFractionDigits: 2 }) : '—'}</b>
        </p>
      ))}
    </div>
  )
}

/**
 * Modal de prévision pour OptiBoard.
 * Props:
 *   isOpen       — bool
 *   onClose      — fn
 *   data         — array des données brutes du rapport
 *   columns      — config colonnes [{field, header, type}]
 *   reportName   — nom du rapport
 */
export default function ForecastModal({ isOpen, onClose, data, columns, reportName }) {
  const [valueField, setValueField] = useState('')
  const [labelField, setLabelField]  = useState('')
  const [periods, setPeriods]        = useState(6)
  const [method, setMethod]          = useState('auto')
  const [loading, setLoading]        = useState(false)
  const [result, setResult]          = useState(null)
  const [error, setError]            = useState(null)

  // Identifier colonnes numériques et texte
  const numericCols = useMemo(() => {
    if (!columns?.length || !data?.length) return []
    const sample = data.slice(0, 20)
    return columns.filter(c => {
      const field = c.field || c.key
      if (!field) return false
      const vals = sample.map(r => r[field]).filter(v => v != null)
      return vals.some(v => typeof v === 'number' || (typeof v === 'string' && !isNaN(parseFloat(v.replace(',', '.')))))
    })
  }, [columns, data])

  const labelCols = useMemo(() => {
    if (!columns?.length) return []
    return columns.filter(c => {
      const field = c.field || c.key
      return field && field !== valueField
    })
  }, [columns, valueField])

  // Initialiser par défaut
  useEffect(() => {
    if (numericCols.length > 0 && !valueField) {
      setValueField(numericCols[0].field || numericCols[0].key)
    }
  }, [numericCols])

  const handleRun = async () => {
    if (!valueField || !data?.length) return
    setLoading(true); setError(null); setResult(null)

    const values = data
      .filter(r => !r.__isGroupRow)
      .map(r => {
        const v = r[valueField]
        if (v == null) return null
        if (typeof v === 'number') return v
        if (typeof v === 'string') {
          const f = parseFloat(v.replace(/\s/g, '').replace(',', '.'))
          return isNaN(f) ? null : f
        }
        return null
      })

    const labels = labelField
      ? data.filter(r => !r.__isGroupRow).map(r => String(r[labelField] ?? ''))
      : null

    try {
      const res = await api.post('/forecast/predict', { values, labels, periods, method })
      setResult(res.data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Erreur lors de la prévision')
    } finally {
      setLoading(false)
    }
  }

  // Construire données chart
  const chartData = useMemo(() => {
    if (!result) return []
    const hist = result.historical.map(h => ({
      label: h.label,
      réel: h.value,
      ajusté: h.fitted,
      prévision: null,
      ci_low: null,
      ci_high: null,
      isHistory: true,
    }))
    // Point de jonction
    const lastHist = hist[hist.length - 1]
    const forecastPts = result.forecast.map((f, i) => ({
      label: f.label,
      réel: i === 0 ? lastHist?.réel : null,
      ajusté: null,
      prévision: f.value,
      ci_low: f.ci_low,
      ci_high: f.ci_high,
      isHistory: false,
    }))
    return [...hist, ...forecastPts]
  }, [result])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
              <BarChart2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800 dark:text-white">Prévision</h2>
              <p className="text-xs text-gray-400">{reportName}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* Config */}
          <div className="px-6 py-4 grid grid-cols-2 sm:grid-cols-4 gap-3 border-b border-gray-100 dark:border-gray-800">
            <div>
              <label className="text-xs text-gray-500 font-medium mb-1 block">Colonne à prévoir</label>
              <select
                value={valueField}
                onChange={e => setValueField(e.target.value)}
                className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">— Choisir —</option>
                {numericCols.map(c => (
                  <option key={c.field || c.key} value={c.field || c.key}>{c.header || c.label || c.field || c.key}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium mb-1 block">Étiquettes (x-axis)</label>
              <select
                value={labelField}
                onChange={e => setLabelField(e.target.value)}
                className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Automatique</option>
                {labelCols.map(c => (
                  <option key={c.field || c.key} value={c.field || c.key}>{c.header || c.label || c.field || c.key}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium mb-1 block">Périodes futures</label>
              <select
                value={periods}
                onChange={e => setPeriods(Number(e.target.value))}
                className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {PERIOD_OPTIONS.map(p => <option key={p} value={p}>{p} périodes</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium mb-1 block">Méthode</label>
              <select
                value={method}
                onChange={e => setMethod(e.target.value)}
                className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {METHOD_OPTIONS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
          </div>

          {/* Bouton Lancer */}
          <div className="px-6 py-3 border-b border-gray-100 dark:border-gray-800 flex items-center gap-3">
            <button
              onClick={handleRun}
              disabled={!valueField || loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors"
            >
              {loading ? (
                <><div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />Calcul en cours…</>
              ) : (
                <><BarChart2 className="w-3.5 h-3.5" />Lancer la prévision</>
              )}
            </button>
            {result && (
              <div className="flex items-center gap-4 text-sm">
                <span className="flex items-center gap-1 text-gray-500">
                  <TrendIcon trend={result.trend} />
                  {result.trend === 'up' ? 'Tendance haussière' : result.trend === 'down' ? 'Tendance baissière' : 'Tendance stable'}
                </span>
                <span className="text-gray-400">·</span>
                <span className="text-gray-500">
                  Croissance historique :
                  <b className={`ml-1 ${result.growth_rate_pct > 0 ? 'text-green-600' : result.growth_rate_pct < 0 ? 'text-red-600' : 'text-gray-500'}`}>
                    {result.growth_rate_pct > 0 ? '+' : ''}{result.growth_rate_pct}%
                  </b>
                </span>
                <span className="text-gray-400">·</span>
                <span className="text-gray-500">
                  Prévision {periods}P :
                  <b className={`ml-1 ${result.forecast_growth_pct > 0 ? 'text-blue-600' : result.forecast_growth_pct < 0 ? 'text-red-600' : 'text-gray-500'}`}>
                    {result.forecast_growth_pct > 0 ? '+' : ''}{result.forecast_growth_pct}%
                  </b>
                </span>
                <span className="text-gray-400">·</span>
                <span className="text-xs text-gray-400">
                  {METHOD_LABELS[result.method_used] || result.method_used} · MAE={result.mae?.toLocaleString('fr-FR')}
                </span>
              </div>
            )}
          </div>

          {/* Erreur */}
          {error && (
            <div className="mx-6 my-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg text-sm text-red-700 dark:text-red-300">
              {error}
            </div>
          )}

          {/* Chart */}
          {result && chartData.length > 0 && (
            <div className="px-6 py-4">
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                    <defs>
                      <linearGradient id="ciGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 11, fill: '#9ca3af' }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: '#9ca3af' }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={v => v?.toLocaleString('fr-FR', { maximumFractionDigits: 0 })}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                      wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                      formatter={(value) => <span className="text-gray-600 dark:text-gray-300">{value}</span>}
                    />

                    {/* Ligne de séparation historique/prévision */}
                    <ReferenceLine
                      x={result.historical[result.historical.length - 1]?.label}
                      stroke="#d1d5db"
                      strokeDasharray="4 4"
                      label={{ value: 'Aujourd\'hui', position: 'top', fontSize: 10, fill: '#9ca3af' }}
                    />

                    {/* Intervalle de confiance */}
                    <Area
                      type="monotone"
                      dataKey="ci_high"
                      stroke="none"
                      fill="url(#ciGradient)"
                      name="IC haut (95%)"
                      legendType="none"
                      connectNulls
                    />
                    <Area
                      type="monotone"
                      dataKey="ci_low"
                      stroke="none"
                      fill="#fff"
                      fillOpacity={1}
                      name="IC bas"
                      legendType="none"
                      connectNulls
                    />

                    {/* Courbe réelle */}
                    <Line
                      type="monotone"
                      dataKey="réel"
                      stroke="#3b82f6"
                      strokeWidth={2.5}
                      dot={{ r: 2.5, fill: '#3b82f6' }}
                      activeDot={{ r: 4 }}
                      name="Réel"
                      connectNulls={false}
                    />

                    {/* Courbe ajustée (fitted) */}
                    <Line
                      type="monotone"
                      dataKey="ajusté"
                      stroke="#94a3b8"
                      strokeWidth={1.5}
                      strokeDasharray="3 3"
                      dot={false}
                      name="Ajusté"
                      connectNulls
                    />

                    {/* Courbe prévision */}
                    <Line
                      type="monotone"
                      dataKey="prévision"
                      stroke="#6366f1"
                      strokeWidth={2.5}
                      strokeDasharray="6 3"
                      dot={{ r: 3, fill: '#6366f1', strokeWidth: 0 }}
                      activeDot={{ r: 5 }}
                      name="Prévision"
                      connectNulls
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* Tableau prévisions */}
              <div className="mt-4">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Valeurs prévisionnelles</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                  {result.forecast.map((f, i) => (
                    <div key={i} className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-2.5 text-center">
                      <div className="text-[10px] text-gray-400 mb-0.5">{f.label}</div>
                      <div className="text-sm font-bold text-indigo-700 dark:text-indigo-300">
                        {f.value?.toLocaleString('fr-FR', { maximumFractionDigits: 0 })}
                      </div>
                      <div className="text-[10px] text-gray-400 mt-0.5">
                        [{f.ci_low?.toLocaleString('fr-FR', { maximumFractionDigits: 0 })} – {f.ci_high?.toLocaleString('fr-FR', { maximumFractionDigits: 0 })}]
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* État initial */}
          {!result && !loading && !error && (
            <div className="py-12 text-center text-gray-400">
              <BarChart2 className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Sélectionnez une colonne et lancez la prévision</p>
              <p className="text-xs mt-1 opacity-70">Algorithme : {METHOD_OPTIONS.find(m => m.value === method)?.label}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
