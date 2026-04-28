import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import { useSettings } from '../../context/SettingsContext'
import { useTheme } from '../../context/ThemeContext'

// Fonction pour générer une palette de couleurs basée sur la couleur primaire du thème
function generateThemeColors(theme) {
  if (!theme?.colors?.primary) {
    return ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
  }

  const primary = theme.colors.primary
  const accent = theme.colors.accent

  return [
    primary[600],  // Couleur principale
    accent,        // Couleur accent
    primary[400],  // Variante claire
    primary[800],  // Variante foncée
    '#f59e0b',     // Orange (contrast)
    '#8b5cf6',     // Violet (contrast)
    primary[300],  // Très clair
    '#ec4899'      // Rose (contrast)
  ]
}

export function CAEvolutionChart({ data = [], onBarClick }) {
  const { formatNumber, settings } = useSettings()
  const { theme } = useTheme()
  const COLORS = generateThemeColors(theme)

  const formatAxis = (value) => {
    return formatNumber(value, { decimals: 1 })
  }

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
        Evolution du CA Mensuel
      </h3>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} onClick={(e) => e && onBarClick && onBarClick(e.activePayload?.[0]?.payload)}>
            {settings.showGridLines && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis
              dataKey="periode"
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                const [year, month] = value.split('-')
                return `${month}/${year.slice(2)}`
              }}
            />
            <YAxis tickFormatter={formatAxis} tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value) => [formatNumber(value), 'CA HT']}
              labelFormatter={(label) => `Période: ${label}`}
            />
            <Bar
              dataKey="ca_ht"
              fill={COLORS[0]}
              radius={[4, 4, 0, 0]}
              cursor={onBarClick ? 'pointer' : 'default'}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export function CAMargeChart({ data = [] }) {
  const { formatNumber, settings } = useSettings()
  const { theme } = useTheme()
  const COLORS = generateThemeColors(theme)

  const formatAxis = (value) => {
    return formatNumber(value, { decimals: 1 })
  }

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
        CA et Marge Brute
      </h3>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            {settings.showGridLines && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis
              dataKey="periode"
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                const [year, month] = value.split('-')
                return `${month}/${year.slice(2)}`
              }}
            />
            <YAxis tickFormatter={formatAxis} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(value) => formatNumber(value)} />
            {settings.showLegend && <Legend />}
            <Line
              type="monotone"
              dataKey="ca_ht"
              name="CA HT"
              stroke={COLORS[0]}
              strokeWidth={2}
              dot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="marge_brute"
              name="Marge Brute"
              stroke={COLORS[1]}
              strokeWidth={2}
              dot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export function CAParGammeChart({ data = [], onSliceClick }) {
  const { formatNumber, settings } = useSettings()
  const { theme } = useTheme()
  const COLORS = generateThemeColors(theme)

  const pieData = data.slice(0, 8).map((item, index) => ({
    ...item,
    color: COLORS[index % COLORS.length]
  }))

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
        Repartition par Gamme
      </h3>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={pieData}
              dataKey="ca_ht"
              nameKey="gamme"
              cx="50%"
              cy="50%"
              outerRadius={70}
              label={({ gamme, pourcentage_ca }) => `${gamme?.slice(0, 10) || 'N/A'} (${pourcentage_ca}%)`}
              labelLine={{ stroke: '#9ca3af' }}
              onClick={(e) => onSliceClick && onSliceClick(e)}
              cursor={onSliceClick ? 'pointer' : 'default'}
            >
              {pieData.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => formatNumber(value)} />
            {settings.showLegend && <Legend />}
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export function BalanceAgeeChart({ data = {}, onBarClick }) {
  const { formatNumber, settings } = useSettings()
  const { theme } = useTheme()
  const COLORS = generateThemeColors(theme)

  const formatAxis = (value) => {
    return formatNumber(value, { decimals: 1 })
  }

  const chartData = [
    { tranche: '0-30j', montant: data['0_30'] || 0, color: settings.positiveColor || COLORS[1] },
    { tranche: '31-60j', montant: data['31_60'] || 0, color: COLORS[2] },
    { tranche: '61-90j', montant: data['61_90'] || 0, color: '#f59e0b' },
    { tranche: '91-120j', montant: data['91_120'] || 0, color: '#f97316' },
    { tranche: '+120j', montant: data['plus_120'] || 0, color: settings.negativeColor || '#ef4444' },
  ]

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
        Balance Agee
      </h3>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            onClick={(e) => e && onBarClick && onBarClick(e.activePayload?.[0]?.payload)}
          >
            {settings.showGridLines && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis type="number" tickFormatter={formatAxis} />
            <YAxis type="category" dataKey="tranche" width={80} />
            <Tooltip formatter={(value) => formatNumber(value)} />
            <Bar
              dataKey="montant"
              radius={[0, 4, 4, 0]}
              cursor={onBarClick ? 'pointer' : 'default'}
            >
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export function TopChart({ data = [], dataKey, nameKey, title, onBarClick }) {
  const { formatNumber, settings } = useSettings()
  const { theme } = useTheme()
  const COLORS = generateThemeColors(theme)

  const formatAxis = (value) => {
    return formatNumber(value, { decimals: 1 })
  }

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
        {title}
      </h3>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            onClick={(e) => e && onBarClick && onBarClick(e.activePayload?.[0]?.payload)}
          >
            {settings.showGridLines && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis type="number" tickFormatter={formatAxis} />
            <YAxis
              type="category"
              dataKey={nameKey}
              width={120}
              tick={{ fontSize: 11 }}
              tickFormatter={(value) => value?.length > 15 ? value.slice(0, 15) + '...' : value}
            />
            <Tooltip formatter={(value) => formatNumber(value)} />
            <Bar
              dataKey={dataKey}
              fill={COLORS[0]}
              radius={[0, 4, 4, 0]}
              cursor={onBarClick ? 'pointer' : 'default'}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
