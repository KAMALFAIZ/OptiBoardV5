import { useState, useEffect, useCallback } from 'react'
import {
  TrendingUp,
  Target,
  Users,
  Package,
  MapPin,
  BarChart3,
  Calendar,
  Download,
  RefreshCw,
  AlertTriangle,
  ArrowUp,
  ArrowDown,
  Settings,
  Building2,
  Layers
} from 'lucide-react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart as RechartsPie,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart
} from 'recharts'
import Loading from '../components/common/Loading'
import { useSettings } from '../context/SettingsContext'
import { useTheme } from '../context/ThemeContext'
import api from '../services/api'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

// Composant KPI Card pour PIC
function PICKPICard({ title, value, objectif, icon: Icon, color = 'blue', evolution, suffix = '' }) {
  const { formatNumber } = useSettings()

  const colorClasses = {
    blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400',
    green: 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400',
    yellow: 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-600 dark:text-yellow-400',
    purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400',
    red: 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
  }

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            {title}
          </p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-white">
            {typeof value === 'number' ? formatNumber(value) : value}{suffix}
          </p>
          {objectif && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Objectif: {formatNumber(objectif)}
            </p>
          )}
          {evolution !== undefined && (
            <div className={`flex items-center gap-1 mt-1 text-xs ${evolution >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {evolution >= 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
              {Math.abs(evolution).toFixed(1)}%
            </div>
          )}
        </div>
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  )
}

// Composant Tableau de donnees
function DataTable({ title, data, columns, maxRows = 10 }) {
  const { formatNumber } = useSettings()
  const displayData = data?.slice(0, maxRows) || []

  const formatValue = (value, format) => {
    if (value === null || value === undefined) return '-'
    switch (format) {
      case 'currency':
        return formatNumber(value)
      case 'percent':
        return `${Number(value).toFixed(2)}%`
      case 'number':
        return formatNumber(value, { decimals: 0 })
      default:
        return value
    }
  }

  return (
    <div className="card">
      <div className="p-3 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  className={`px-3 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {displayData.map((row, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                {columns.map((col, colIdx) => (
                  <td
                    key={colIdx}
                    className={`px-3 py-2 text-xs text-gray-900 dark:text-gray-100 ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                  >
                    {formatValue(row[col.key], col.format)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data?.length > maxRows && (
        <div className="p-2 text-center text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700">
          Affichage de {maxRows} sur {data.length} lignes
        </div>
      )}
    </div>
  )
}

// Graphique Saisonnalite
function SaisonnaliteChart({ data }) {
  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Indices de Saisonnalite (base 100)</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="mois" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 150]} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value) => value?.toFixed(1)} />
            <Bar dataKey="indice" name="Indice">
              {data?.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.indice > 110 ? COLORS[1] : entry.indice < 90 ? COLORS[3] : COLORS[2]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// Graphique Repartition par Region
function RegionChart({ data }) {
  const { formatNumber } = useSettings()

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">CA par Region</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RechartsPie>
            <Pie
              data={data?.slice(0, 8)}
              dataKey="ca"
              nameKey="region"
              cx="50%"
              cy="50%"
              outerRadius={80}
              label={({ name, percent }) => `${name?.substring(0, 10)} (${(percent * 100).toFixed(0)}%)`}
              labelLine={false}
            >
              {data?.slice(0, 8).map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => formatNumber(value)} />
          </RechartsPie>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// Graphique Performance Commerciaux
function CommerciauxChart({ data }) {
  const { formatNumber } = useSettings()

  const chartData = data?.slice(0, 10).map(c => ({
    nom: c.representant?.substring(0, 12) || 'N/A',
    ca: c.ca || 0,
    objectif: c.objectif_ca_2026 || 0
  }))

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Top 10 Commerciaux - CA vs Objectif 2026</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => formatNumber(v, { decimals: 0 })} />
            <YAxis dataKey="nom" type="category" width={100} tick={{ fontSize: 10 }} />
            <Tooltip formatter={(value) => formatNumber(value)} />
            <Legend />
            <Bar dataKey="ca" name="CA Historique" fill={COLORS[0]} radius={[0, 4, 4, 0]} />
            <Bar dataKey="objectif" name="Objectif 2026" fill={COLORS[1]} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// Graphique Classification ABC
function ABCChart({ data }) {
  const classA = data?.filter(d => d.classe === 'A').length || 0
  const classB = data?.filter(d => d.classe === 'B').length || 0
  const classC = data?.filter(d => d.classe === 'C').length || 0

  const chartData = [
    { name: 'A - Prioritaire (80% CA)', value: classA, fill: COLORS[1] },
    { name: 'B - Important (15% CA)', value: classB, fill: COLORS[2] },
    { name: 'C - Secondaire (5% CA)', value: classC, fill: COLORS[3] }
  ]

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Classification ABC Articles</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RechartsPie>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={80}
              label={({ name, value }) => `${name.split(' ')[0]}: ${value}`}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip />
          </RechartsPie>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// Graphique Marge par Region
function MargeRegionChart({ data }) {
  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Taux de Marge par Region</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data?.slice(0, 10)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="region" tick={{ fontSize: 9 }} angle={-45} textAnchor="end" height={60} />
            <YAxis domain={[0, 50]} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value) => `${value?.toFixed(2)}%`} />
            <Bar dataKey="taux_marge" name="Taux Marge %">
              {data?.slice(0, 10).map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.taux_marge >= 25 ? COLORS[1] : entry.taux_marge < 15 ? COLORS[3] : COLORS[2]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// Graphique Objectifs Mensuels
function ObjectifsMensuelsChart({ data }) {
  const { formatNumber } = useSettings()

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Objectifs Mensuels CA 2026</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="mois" tick={{ fontSize: 10 }} tickFormatter={(v) => v?.substring(0, 3)} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => formatNumber(v, { decimals: 0 })} />
            <Tooltip formatter={(value) => formatNumber(value)} />
            <Legend />
            <Bar dataKey="objectif_ca" name="Objectif CA" fill={COLORS[0]} radius={[4, 4, 0, 0]} />
            <Line type="monotone" dataKey="objectif_marge" name="Objectif Marge" stroke={COLORS[1]} strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// Graphique par Catalogue
function CatalogueChart({ data }) {
  const { formatNumber } = useSettings()

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">CA par Catalogue (Famille)</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data?.slice(0, 8)} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => formatNumber(v, { decimals: 0 })} />
            <YAxis dataKey="catalogue" type="category" width={120} tick={{ fontSize: 9 }} />
            <Tooltip formatter={(value) => formatNumber(value)} />
            <Bar dataKey="ca" name="CA Total" fill={COLORS[4]} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default function PIC2026() {
  const [loading, setLoading] = useState(true)
  const [tauxCroissance, setTauxCroissance] = useState(5)
  const [activeTab, setActiveTab] = useState('synthese')
  const [data, setData] = useState({
    synthese: null,
    regions: [],
    commerciaux: [],
    articles: [],
    saisonnalite: [],
    objectifsMensuels: [],
    catalogues: [],
    chargeCapacite: []
  })

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.get('/pic/2026', {
        params: { taux_croissance: tauxCroissance / 100 }
      })

      if (response.data?.success) {
        setData({
          synthese: response.data.synthese,
          saisonnalite: response.data.saisonnalite || [],
          regions: response.data.regions || [],
          commerciaux: response.data.commerciaux || [],
          articles: response.data.articles || [],
          objectifsMensuels: response.data.objectifsMensuels || [],
          catalogues: response.data.catalogues || [],
          chargeCapacite: response.data.chargeCapacite || []
        })
      }
    } catch (error) {
      console.error('Erreur chargement PIC 2026:', error)
    } finally {
      setLoading(false)
    }
  }, [tauxCroissance])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleExport = async () => {
    try {
      const response = await api.get('/pic/2026/export', {
        params: { taux_croissance: tauxCroissance / 100 },
        responseType: 'blob'
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `PIC_2026_${tauxCroissance}pct.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Erreur export:', error)
    }
  }

  const tabs = [
    { id: 'synthese', label: 'Synthese', icon: BarChart3 },
    { id: 'regions', label: 'Regions', icon: MapPin },
    { id: 'commerciaux', label: 'Commerciaux', icon: Users },
    { id: 'articles', label: 'Articles', icon: Package },
    { id: 'marges', label: 'Marges', icon: TrendingUp },
    { id: 'capacite', label: 'Capacite', icon: Calendar }
  ]

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
        <div>
          <h1 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Target className="w-5 h-5 text-primary-600" />
            PIC 2026 - Plan Industriel et Commercial
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Basé sur la procédure sp_PIC_2026 - Objectifs et prévisions pour l'année 2026
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 rounded-lg px-3 py-1.5">
            <Settings className="w-4 h-4 text-gray-500" />
            <label className="text-xs text-gray-600 dark:text-gray-400">Croissance:</label>
            <select
              value={tauxCroissance}
              onChange={(e) => setTauxCroissance(Number(e.target.value))}
              className="bg-transparent text-sm font-medium text-gray-900 dark:text-white border-none focus:ring-0"
            >
              <option value={3}>3%</option>
              <option value={5}>5%</option>
              <option value={8}>8%</option>
              <option value={10}>10%</option>
              <option value={15}>15%</option>
            </select>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="btn-secondary flex items-center gap-1"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </button>
          <button onClick={handleExport} className="btn-primary flex items-center gap-1">
            <Download className="w-3.5 h-3.5" />
            Exporter
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <Loading message="Chargement du PIC 2026..." />
      ) : (
        <>
          {/* Synthese Tab */}
          {activeTab === 'synthese' && (
            <div className="space-y-4">
              {/* KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                <PICKPICard
                  title="CA Annuel Moyen"
                  value={data.synthese?.ca_annuel_moyen || 0}
                  objectif={data.synthese?.objectif_ca_2026}
                  icon={TrendingUp}
                  color="blue"
                  evolution={tauxCroissance}
                />
                <PICKPICard
                  title="Marge Moyenne"
                  value={data.synthese?.marge_annuelle_moyenne || 0}
                  objectif={data.synthese?.objectif_marge_2026}
                  icon={Target}
                  color="green"
                />
                <PICKPICard
                  title="Nb Societes"
                  value={data.synthese?.nb_societes || 0}
                  icon={Building2}
                  color="purple"
                />
                <PICKPICard
                  title="Nb Regions"
                  value={data.synthese?.nb_regions || 0}
                  icon={MapPin}
                  color="yellow"
                />
                <PICKPICard
                  title="Nb Commerciaux"
                  value={data.synthese?.nb_commerciaux || 0}
                  icon={Users}
                  color="blue"
                />
                <PICKPICard
                  title="Nb Articles"
                  value={data.synthese?.nb_articles || 0}
                  icon={Package}
                  color="green"
                />
              </div>

              {/* Charts Row 1 */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <SaisonnaliteChart data={data.saisonnalite} />
                <RegionChart data={data.regions} />
              </div>

              {/* Charts Row 2 */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <ObjectifsMensuelsChart data={data.objectifsMensuels} />
                <ABCChart data={data.articles} />
              </div>

              {/* Tableau Objectifs Mensuels */}
              <DataTable
                title="Objectifs Mensuels 2026 (avec saisonnalite)"
                data={data.objectifsMensuels}
                columns={[
                  { key: 'mois', header: 'Mois' },
                  { key: 'poids_percent', header: 'Poids %', format: 'percent', align: 'right' },
                  { key: 'objectif_ca', header: 'Objectif CA', format: 'currency', align: 'right' },
                  { key: 'objectif_marge', header: 'Objectif Marge', format: 'currency', align: 'right' }
                ]}
                maxRows={12}
              />
            </div>
          )}

          {/* Regions Tab */}
          {activeTab === 'regions' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <RegionChart data={data.regions} />
                <MargeRegionChart data={data.regions} />
              </div>

              <DataTable
                title="Tableau PIC 2026 par Region"
                data={data.regions}
                columns={[
                  { key: 'region', header: 'Region' },
                  { key: 'nb_commerciaux', header: 'Commerciaux', format: 'number', align: 'right' },
                  { key: 'nb_articles', header: 'Articles', format: 'number', align: 'right' },
                  { key: 'ca_reference', header: 'CA Reference', format: 'currency', align: 'right' },
                  { key: 'objectif_ca_2026', header: 'Objectif CA 2026', format: 'currency', align: 'right' },
                  { key: 'objectif_qte_2026', header: 'Objectif Qte', format: 'number', align: 'right' },
                  { key: 'objectif_marge_2026', header: 'Objectif Marge', format: 'currency', align: 'right' },
                  { key: 'taux_marge', header: 'Taux Marge Cible', format: 'percent', align: 'right' },
                  { key: 'part_ca_percent', header: 'Part CA %', format: 'percent', align: 'right' }
                ]}
              />
            </div>
          )}

          {/* Commerciaux Tab */}
          {activeTab === 'commerciaux' && (
            <div className="space-y-4">
              <CommerciauxChart data={data.commerciaux} />

              <DataTable
                title="Objectifs 2026 par Commercial"
                data={data.commerciaux}
                columns={[
                  { key: 'representant', header: 'Commercial' },
                  { key: 'region', header: 'Region' },
                  { key: 'ca_reference', header: 'CA Reference', format: 'currency', align: 'right' },
                  { key: 'objectif_ca_2026', header: 'Objectif CA 2026', format: 'currency', align: 'right' },
                  { key: 'objectif_qte_2026', header: 'Objectif Qte', format: 'number', align: 'right' },
                  { key: 'objectif_marge_2026', header: 'Objectif Marge', format: 'currency', align: 'right' },
                  { key: 'taux_marge', header: 'Taux Marge Min', format: 'percent', align: 'right' },
                  { key: 'rang_ca', header: 'Rang CA', format: 'number', align: 'right' },
                  { key: 'rang_marge', header: 'Rang Marge', format: 'number', align: 'right' }
                ]}
                maxRows={25}
              />
            </div>
          )}

          {/* Articles Tab */}
          {activeTab === 'articles' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <ABCChart data={data.articles} />
                <CatalogueChart data={data.catalogues} />
              </div>

              <DataTable
                title="Classification ABC - Top Articles Priorites Stock 2026"
                data={data.articles}
                columns={[
                  { key: 'code_article', header: 'Code' },
                  { key: 'designation', header: 'Designation' },
                  { key: 'catalogue_1', header: 'Catalogue 1' },
                  { key: 'qte_vendue', header: 'Qte Vendue', format: 'number', align: 'right' },
                  { key: 'ca', header: 'CA Article', format: 'currency', align: 'right' },
                  { key: 'marge', header: 'Marge', format: 'currency', align: 'right' },
                  { key: 'taux_marge', header: 'Taux Marge', format: 'percent', align: 'right' },
                  { key: 'part_ca_percent', header: 'Part CA %', format: 'percent', align: 'right' },
                  { key: 'classe', header: 'Classe ABC' },
                  { key: 'qte_prevue_2026', header: 'Qte Prevue 2026', format: 'number', align: 'right' }
                ]}
                maxRows={50}
              />

              <DataTable
                title="Analyse par Catalogue (Famille Principale)"
                data={data.catalogues}
                columns={[
                  { key: 'catalogue', header: 'Famille' },
                  { key: 'nb_articles', header: 'Nb Articles', format: 'number', align: 'right' },
                  { key: 'qte_totale', header: 'Qte Totale', format: 'number', align: 'right' },
                  { key: 'ca', header: 'CA Total', format: 'currency', align: 'right' },
                  { key: 'marge', header: 'Marge Totale', format: 'currency', align: 'right' },
                  { key: 'taux_marge', header: 'Taux Marge', format: 'percent', align: 'right' },
                  { key: 'part_ca_percent', header: 'Part CA %', format: 'percent', align: 'right' }
                ]}
              />
            </div>
          )}

          {/* Marges Tab */}
          {activeTab === 'marges' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <MargeRegionChart data={data.regions} />
                <div className="card p-3">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Zones de Rentabilite par Region</h3>
                  <div className="space-y-2 mt-4 max-h-56 overflow-y-auto">
                    {data.regions?.map((r, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                        <span className="text-xs font-medium text-gray-900 dark:text-white">{r.region}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">{r.taux_marge?.toFixed(1)}%</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            r.taux_marge >= 30 ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                            r.taux_marge >= 20 ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' :
                            r.taux_marge >= 10 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' :
                            'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                          }`}>
                            {r.taux_marge >= 30 ? 'EXCELLENTE' :
                             r.taux_marge >= 20 ? 'BONNE' :
                             r.taux_marge >= 10 ? 'MOYENNE' : 'A AMELIORER'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <DataTable
                title="Articles a Faible Marge (< 10%) avec CA significatif"
                data={data.articles?.filter(a => a.taux_marge < 10 && a.ca > 1000).sort((a, b) => b.ca - a.ca)}
                columns={[
                  { key: 'code_article', header: 'Code' },
                  { key: 'designation', header: 'Designation' },
                  { key: 'catalogue_1', header: 'Catalogue' },
                  { key: 'ca', header: 'CA', format: 'currency', align: 'right' },
                  { key: 'cout', header: 'Cout', format: 'currency', align: 'right' },
                  { key: 'marge', header: 'Marge', format: 'currency', align: 'right' },
                  { key: 'taux_marge', header: 'Taux Marge', format: 'percent', align: 'right' }
                ]}
                maxRows={20}
              />

              <DataTable
                title="Articles a Marge Negative (En Perte)"
                data={data.articles?.filter(a => a.marge < 0).sort((a, b) => a.marge - b.marge)}
                columns={[
                  { key: 'code_article', header: 'Code' },
                  { key: 'designation', header: 'Designation' },
                  { key: 'catalogue_1', header: 'Catalogue' },
                  { key: 'qte_vendue', header: 'Qte', format: 'number', align: 'right' },
                  { key: 'ca', header: 'CA', format: 'currency', align: 'right' },
                  { key: 'cout', header: 'Cout', format: 'currency', align: 'right' },
                  { key: 'marge', header: 'Marge Negative', format: 'currency', align: 'right' }
                ]}
                maxRows={15}
              />
            </div>
          )}

          {/* Capacite Tab */}
          {activeTab === 'capacite' && (
            <div className="space-y-4">
              <div className="card p-3">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Repartition de la Charge par Mois - Recommandations Capacite</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.chargeCapacite}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="mois" tick={{ fontSize: 10 }} tickFormatter={(v) => v?.substring(0, 3)} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="qte_totale" name="Qte Historique" fill={COLORS[0]}>
                        {data.chargeCapacite?.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={entry.periode === 'HAUTE' ? COLORS[3] : entry.periode === 'BASSE' ? COLORS[1] : COLORS[0]}
                          />
                        ))}
                      </Bar>
                      <Bar dataKey="charge_prevue_2026" name="Charge Prevue 2026" fill={COLORS[4]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <DataTable
                title="Recommandations Charge/Capacite 2026"
                data={data.chargeCapacite}
                columns={[
                  { key: 'mois', header: 'Mois' },
                  { key: 'qte_totale', header: 'Qte Historique', format: 'number', align: 'right' },
                  { key: 'poids_percent', header: 'Poids %', format: 'percent', align: 'right' },
                  { key: 'charge_prevue_2026', header: 'Charge Prevue 2026', format: 'number', align: 'right' },
                  { key: 'periode', header: 'Recommandation' }
                ]}
                maxRows={12}
              />

              <div className="grid grid-cols-3 gap-3">
                <div className="card p-4 text-center">
                  <div className="text-2xl font-bold text-red-600">{data.chargeCapacite?.filter(c => c.periode === 'HAUTE').length || 0}</div>
                  <div className="text-xs text-gray-500">Periodes Hautes</div>
                  <div className="text-xs text-gray-400 mt-1">Renforcer capacite</div>
                </div>
                <div className="card p-4 text-center">
                  <div className="text-2xl font-bold text-blue-600">{data.chargeCapacite?.filter(c => c.periode === 'NORMALE').length || 0}</div>
                  <div className="text-xs text-gray-500">Periodes Normales</div>
                  <div className="text-xs text-gray-400 mt-1">Capacite standard</div>
                </div>
                <div className="card p-4 text-center">
                  <div className="text-2xl font-bold text-green-600">{data.chargeCapacite?.filter(c => c.periode === 'BASSE').length || 0}</div>
                  <div className="text-xs text-gray-500">Periodes Basses</div>
                  <div className="text-xs text-gray-400 mt-1">Optimiser ressources</div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
