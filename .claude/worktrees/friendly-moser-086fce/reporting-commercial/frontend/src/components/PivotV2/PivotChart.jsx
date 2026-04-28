import { useMemo } from 'react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  AreaChart, Area,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid,
  LabelList
} from 'recharts'
import { useSettings } from '../../context/SettingsContext'

// Palette de couleurs améliorée — couleurs plus vives et distinctes
const CHART_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
  '#14b8a6', '#e11d48', '#a855f7', '#0ea5e9', '#eab308',
  '#22c55e', '#d946ef', '#64748b', '#fb923c', '#2dd4bf'
]


export default function PivotChart({
  data = [],
  pivotColumns = [],
  rowFields = [],
  columnField,
  valueFields = [],
  chartType = 'bar',
  maxRows = 50,
  selectedValueIndex = null,
  onCellClick = null,
  className = '',
}) {
  const { formatNumber, settings } = useSettings()
  const colors = settings?.chartColors || CHART_COLORS

  // Transformer les donnees pour Recharts
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    const filteredData = data.filter(r => !r.__isSubtotal__ && !r.__isGrandTotal__)
    const rowFieldName = rowFields[0]?.field || rowFields[0]

    if (columnField && pivotColumns.length > 0) {
      const activeVFs = selectedValueIndex !== null && selectedValueIndex >= 0
        ? [valueFields[selectedValueIndex]]
        : valueFields
      return filteredData.slice(0, maxRows).map(row => {
        const item = { name: String(row[rowFieldName] || '') }
        for (const vf of activeVFs) {
          for (const col of pivotColumns) {
            const key = `${col}__${vf.alias}`
            const seriesName = activeVFs.length > 1 ? `${col} (${vf.label || vf.field})` : col
            item[seriesName] = row[key] || 0
          }
        }
        return item
      })
    } else {
      return filteredData.slice(0, maxRows).map(row => {
        const item = { name: String(row[rowFieldName] || '') }
        for (const vf of valueFields) {
          item[vf.label || vf.field] = row[vf.alias] || 0
        }
        return item
      })
    }
  }, [data, pivotColumns, rowFields, columnField, valueFields, maxRows, selectedValueIndex])

  // Series du chart
  const series = useMemo(() => {
    if (columnField && pivotColumns.length > 0) {
      const activeVFs = selectedValueIndex !== null && selectedValueIndex >= 0
        ? [valueFields[selectedValueIndex]]
        : valueFields
      const result = []
      let colorIdx = 0
      for (const vf of activeVFs) {
        for (const col of pivotColumns) {
          const seriesName = activeVFs.length > 1 ? `${col} (${vf.label || vf.field})` : col
          result.push({ key: seriesName, color: colors[colorIdx % colors.length] })
          colorIdx++
        }
      }
      return result
    }
    return valueFields.map((vf, i) => ({
      key: vf.label || vf.field,
      color: colors[i % colors.length],
    }))
  }, [columnField, pivotColumns, valueFields, colors, selectedValueIndex])

  const rowFieldName = rowFields[0]?.field || rowFields[0]

  const handleChartClick = (rowName, seriesKey) => {
    if (!onCellClick) return
    const rowValue = (rowName === '' || rowName === 'null' || rowName === 'None') ? null : rowName
    onCellClick({
      rowValues: rowFieldName ? { [rowFieldName]: rowValue } : {},
      valueField: seriesKey,
    })
  }

  // Tooltip amélioré
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || payload.length === 0) return null

    // Trier par valeur décroissante
    const sorted = [...payload].sort((a, b) => (b.value || 0) - (a.value || 0))
    const total = sorted.reduce((sum, e) => sum + (e.value || 0), 0)

    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl p-3 text-sm max-h-[280px] overflow-y-auto min-w-[180px]">
        <p className="font-bold text-gray-900 dark:text-white mb-2 pb-1.5 border-b border-gray-100 dark:border-gray-700 text-xs">
          {label}
        </p>
        <div className="space-y-1">
          {sorted.map((entry, i) => (
            <div key={i} className="flex items-center justify-between gap-3 text-xs">
              <span className="flex items-center gap-1.5 min-w-0">
                <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: entry.color }} />
                <span className="truncate text-gray-600 dark:text-gray-400">{entry.name}</span>
              </span>
              <span className="font-semibold text-gray-900 dark:text-white tabular-nums whitespace-nowrap">
                {formatNumber(entry.value, { showCurrency: false })}
              </span>
            </div>
          ))}
        </div>
        {sorted.length > 1 && (
          <div className="mt-2 pt-1.5 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between text-xs">
            <span className="font-medium text-gray-500">Total</span>
            <span className="font-bold text-gray-900 dark:text-white tabular-nums">
              {formatNumber(total, { showCurrency: false })}
            </span>
          </div>
        )}
      </div>
    )
  }

  // Légende personnalisée
  const CustomLegend = ({ payload }) => {
    if (!payload || payload.length === 0) return null
    // Afficher max 12 légendes, tronquer sinon
    const maxDisplay = 12
    const displayed = payload.slice(0, maxDisplay)
    const remaining = payload.length - maxDisplay

    return (
      <div className="flex flex-wrap justify-center gap-x-3 gap-y-1 mt-2 px-2">
        {displayed.map((entry, i) => (
          <span key={i} className="inline-flex items-center gap-1 text-[10px] text-gray-600 dark:text-gray-400">
            <span className="w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: entry.color }} />
            <span className="truncate max-w-[100px]">{entry.value}</span>
          </span>
        ))}
        {remaining > 0 && (
          <span className="text-[10px] text-gray-400">+{remaining} autres</span>
        )}
      </div>
    )
  }

  if (chartData.length === 0) {
    return (
      <div className={`flex items-center justify-center h-48 text-gray-400 text-sm ${className}`}>
        Pas de donnees pour le graphique
      </div>
    )
  }

  // Hauteur dynamique selon le type de chart et le nombre de données
  const getChartHeight = () => {
    if (chartType === 'horizontal_bar') {
      return Math.max(300, Math.min(700, chartData.length * 28 + 60))
    }
    if (chartType === 'pie' || chartType === 'donut') {
      return 380
    }
    // Hauteur ajustée selon le nombre de données ET le nombre de séries
    const baseHeight = 250 + chartData.length * 4
    const seriesBonus = series.length > 3 ? (series.length - 3) * 20 : 0
    return Math.max(300, Math.min(600, baseHeight + seriesBonus))
  }

  const chartHeight = getChartHeight()
  const needsAngle = chartData.length > 12
  const xAxisAngle = needsAngle ? -40 : 0
  const xAxisTextAnchor = needsAngle ? 'end' : 'middle'
  const xAxisHeight = needsAngle ? 70 : 35

  // ─── Pie / Donut ───
  if (chartType === 'pie' || chartType === 'donut') {
    const isDonut = chartType === 'donut'
    const pieData = chartData.map((item, i) => ({
      name: item.name,
      value: Math.abs(item[series[0]?.key] || 0),
      color: colors[i % colors.length],
    })).filter(d => d.value > 0)

    const totalValue = pieData.reduce((s, d) => s + d.value, 0)

    const renderLabel = ({ name, percent, cx, cy, midAngle, innerRadius, outerRadius }) => {
      if (percent < 0.03) return null // Masquer les labels < 3%
      const RADIAN = Math.PI / 180
      const radius = outerRadius + 22
      const x = cx + radius * Math.cos(-midAngle * RADIAN)
      const y = cy + radius * Math.sin(-midAngle * RADIAN)
      return (
        <text x={x} y={y} fill="currentColor" textAnchor={x > cx ? 'start' : 'end'}
          dominantBaseline="central" fontSize={10} className="text-gray-600 dark:text-gray-400">
          {name} ({(percent * 100).toFixed(0)}%)
        </text>
      )
    }

    return (
      <div className={`${className}`}>
        <ResponsiveContainer width="100%" height={chartHeight}>
          <PieChart>
            <Pie
              data={pieData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={isDonut ? 60 : 0}
              outerRadius={isDonut ? 120 : 130}
              label={renderLabel}
              labelLine={{ stroke: '#94a3b8', strokeWidth: 1 }}
              paddingAngle={isDonut ? 2 : 0}
              stroke="none"
              onClick={(entry) => handleChartClick(entry.name, series[0]?.key)}
              style={onCellClick ? { cursor: 'pointer' } : undefined}
            >
              {pieData.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            {isDonut && (
              <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle">
                <tspan x="50%" dy="-8" fontSize={20} fontWeight="bold" fill="currentColor" className="text-gray-800 dark:text-gray-200">
                  {formatNumber(totalValue, { format: 'abbreviated' })}
                </tspan>
                <tspan x="50%" dy="18" fontSize={10} fill="currentColor" className="text-gray-400">
                  Total
                </tspan>
              </text>
            )}
            <Tooltip content={<CustomTooltip />} />
            <Legend content={<CustomLegend />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // ─── Horizontal Bar ───
  if (chartType === 'horizontal_bar') {
    return (
      <div className={`${className}`}>
        <ResponsiveContainer width="100%" height={chartHeight}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="currentColor" className="text-gray-200 dark:text-gray-700" />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 10 }}
              width={Math.min(160, Math.max(60, chartData.reduce((max, d) => Math.max(max, (d.name || '').length), 0) * 6))}
            />
            <XAxis
              type="number"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => formatNumber(v, { format: 'abbreviated' })}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend content={<CustomLegend />} />
            {series.map((s, i) => (
              <Bar
                key={s.key}
                dataKey={s.key}
                fill={colors[i % colors.length]}
                fillOpacity={0.85}
                radius={[0, 4, 4, 0]}
                barSize={Math.max(14, Math.min(24, 400 / chartData.length))}
                onClick={(data) => handleChartClick(data.name, s.key)}
                style={onCellClick ? { cursor: 'pointer' } : undefined}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // ─── Line chart ───
  if (chartType === 'line') {
    return (
      <div className={`${className}`}>
        <ResponsiveContainer width="100%" height={chartHeight}>
          <LineChart data={chartData} margin={{ left: 5, right: 10, top: 5, bottom: 5 }}
            onClick={onCellClick ? (d) => { if (d?.activeLabel !== undefined && d?.activePayload?.[0]) handleChartClick(d.activeLabel, d.activePayload[0].name) } : undefined}
            style={onCellClick ? { cursor: 'pointer' } : undefined}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-gray-200 dark:text-gray-700" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={xAxisAngle} textAnchor={xAxisTextAnchor} height={xAxisHeight} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatNumber(v, { format: 'abbreviated' })} />
            <Tooltip content={<CustomTooltip />} />
            <Legend content={<CustomLegend />} />
            {series.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.color}
                strokeWidth={2.5}
                dot={{ fill: s.color, r: 3, strokeWidth: 0 }}
                activeDot={{ r: 6, strokeWidth: 2, stroke: '#fff' }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // ─── Area chart ───
  if (chartType === 'area') {
    return (
      <div className={`${className}`}>
        <ResponsiveContainer width="100%" height={chartHeight}>
          <AreaChart data={chartData} margin={{ left: 5, right: 10, top: 5, bottom: 5 }}
            onClick={onCellClick ? (d) => { if (d?.activeLabel !== undefined && d?.activePayload?.[0]) handleChartClick(d.activeLabel, d.activePayload[0].name) } : undefined}
            style={onCellClick ? { cursor: 'pointer' } : undefined}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-gray-200 dark:text-gray-700" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={xAxisAngle} textAnchor={xAxisTextAnchor} height={xAxisHeight} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatNumber(v, { format: 'abbreviated' })} />
            <Tooltip content={<CustomTooltip />} />
            <Legend content={<CustomLegend />} />
            {series.map((s, i) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.color}
                strokeWidth={2}
                fill={s.color}
                fillOpacity={0.15}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // ─── Bar chart (défaut) + stacked_bar ───
  const isStacked = chartType === 'stacked_bar'

  // Limiter les séries affichées quand la densité est trop élevée (trop de séries × trop de lignes)
  // Pour éviter les micro-barres illisibles, on tronque à 1 série si nécessaire
  const tooManyBars = series.length > 2 && chartData.length > 15
  const displaySeries = tooManyBars ? series.slice(0, 1) : series
  const truncatedCount = series.length - displaySeries.length

  // Calcul du domaine Y intelligent (inline — pas un hook, on est après des returns conditionnels)
  const _rawVals = chartData.flatMap(d => displaySeries.map(s => typeof d[s.key] === 'number' ? d[s.key] : 0))
  const _posVals = _rawVals.filter(v => v > 0).sort((a, b) => a - b)
  const _hasNeg  = _rawVals.some(v => v < 0)
  const _median  = _posVals.length ? _posVals[Math.floor(_posVals.length / 2)] : 0
  const _maxVal  = _posVals.length ? _posVals[_posVals.length - 1] : 0
  // Si outlier : cap le max à ~2.4× la médiane ; si valeurs négatives : laisser l'axe auto
  const yDomainMax = (_median > 0 && _maxVal > 10 * _median) ? Math.ceil(_median * 2.4) : 'auto'
  const yDomain = [_hasNeg ? 'auto' : 0, yDomainMax]

  // Taille des barres proportionnelle au nombre de colonnes × séries
  const barsPerGroup = isStacked ? 1 : displaySeries.length
  const computedBarSize = Math.max(8, Math.min(40, Math.floor(560 / (chartData.length * barsPerGroup))))

  return (
    <div className={`${className}`}>
      {truncatedCount > 0 && (
        <div className="text-center text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded px-3 py-1 mb-1 mx-2">
          ⚠ Graphique limité à «&nbsp;{displaySeries[0]?.key}&nbsp;» ({truncatedCount} mesure{truncatedCount > 1 ? 's' : ''} masquée{truncatedCount > 1 ? 's' : ''}).
          Sélectionnez une mesure dans le panneau Champs pour afficher toutes les séries.
        </div>
      )}
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart data={chartData} margin={{ left: 5, right: 10, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-gray-200 dark:text-gray-700" />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={xAxisAngle} textAnchor={xAxisTextAnchor} height={xAxisHeight} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatNumber(v, { format: 'abbreviated' })} domain={yDomain} allowDataOverflow={true} />
          <Tooltip content={<CustomTooltip />} />
          <Legend content={<CustomLegend />} />
          {displaySeries.map((s, i) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              fill={colors[i % colors.length]}
              fillOpacity={0.85}
              radius={isStacked ? [0, 0, 0, 0] : [4, 4, 0, 0]}
              stackId={isStacked ? 'stack' : undefined}
              barSize={computedBarSize}
              onClick={(data) => handleChartClick(data.name, s.key)}
              style={onCellClick ? { cursor: 'pointer' } : undefined}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
