import { useState, useEffect, useCallback } from 'react'
import {
  Database, HardDrive, Rows3, ArrowUpCircle, ArrowRightLeft,
  RefreshCw, AlertTriangle, ChevronDown, ChevronUp, Clock,
  Server, BarChart3
} from 'lucide-react'
import { getSyncDashboard } from '../../services/etlApi'

function formatNumber(num) {
  if (num === null || num === undefined) return '-'
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toLocaleString('fr-FR')
}

function formatSize(mb) {
  if (mb === null || mb === undefined) return '-'
  if (mb >= 1024) return `${(mb / 1024).toFixed(2)} GB`
  return `${mb.toFixed(2)} MB`
}

function formatDate(dateStr) {
  if (!dateStr) return 'Jamais'
  return new Date(dateStr).toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

function SummaryCard({ icon: Icon, label, value, color }) {
  const colorMap = {
    blue: 'bg-primary-500',
    purple: 'bg-primary-600',
    green: 'bg-green-500',
    cyan: 'bg-primary-400'
  }
  return (
    <div className={`${colorMap[color]} text-white rounded-lg p-4`}>
      <div className="flex items-center gap-3">
        <Icon size={32} className="opacity-75" />
        <div>
          <div className="text-2xl font-bold">{value}</div>
          <div className="text-sm opacity-90">{label}</div>
        </div>
      </div>
    </div>
  )
}

function DWHRow({ dwh, expanded, onToggle }) {
  return (
    <>
      <tr
        className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
        onClick={onToggle}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <Database size={16} className="text-primary-500" />
            <div>
              <div className="font-medium text-gray-900 dark:text-white">
                {dwh.dwh_name || dwh.dwh_code}
              </div>
              <div className="text-xs text-gray-500">{dwh.database} @ {dwh.server}</div>
            </div>
          </div>
        </td>
        <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-white">
          {formatSize(dwh.db_size_mb)}
        </td>
        <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-white">
          {formatNumber(dwh.total_rows)}
        </td>
        <td className="px-4 py-3 text-right text-green-600 dark:text-green-400 font-medium">
          {formatNumber(dwh.total_inserted)}
        </td>
        <td className="px-4 py-3 text-right text-primary-600 dark:text-primary-400 font-medium">
          {formatNumber(dwh.total_updated)}
        </td>
        <td className="px-4 py-3 text-center">
          {dwh.error ? (
            <span className="inline-flex items-center gap-1 text-red-600 text-sm" title={dwh.error}>
              <AlertTriangle size={14} /> Erreur
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-green-600 text-sm">
              <Server size={14} /> OK
            </span>
          )}
        </td>
        <td className="px-4 py-3 text-gray-400">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={7} className="bg-gray-50 dark:bg-gray-900 px-4 py-3">
            {/* Stats du jour */}
            {dwh.today_stats && dwh.today_stats.syncs_today > 0 && (
              <div className="mb-3 p-2 bg-primary-50 dark:bg-primary-900/20 rounded text-sm">
                <span className="font-medium text-primary-700 dark:text-primary-300">
                  Aujourd'hui :
                </span>{' '}
                {dwh.today_stats.syncs_today} syncs,{' '}
                {formatNumber(dwh.today_stats.rows_inserted_today)} inserees,{' '}
                {formatNumber(dwh.today_stats.rows_updated_today)} modifiees
                {dwh.today_stats.rows_failed_today > 0 && (
                  <span className="text-red-600 ml-2">
                    ({formatNumber(dwh.today_stats.rows_failed_today)} erreurs)
                  </span>
                )}
              </div>
            )}

            {/* SyncControl par table */}
            {dwh.sync_control && dwh.sync_control.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 dark:text-gray-400">
                      <th className="text-left py-1 px-2">Table</th>
                      <th className="text-right py-1 px-2">Inserees</th>
                      <th className="text-right py-1 px-2">Modifiees</th>
                      <th className="text-right py-1 px-2">Supprimees</th>
                      <th className="text-right py-1 px-2">Derniere sync</th>
                      <th className="text-center py-1 px-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dwh.sync_control.map(sc => (
                      <tr key={sc.TableName} className="border-t border-gray-200 dark:border-gray-700">
                        <td className="py-1 px-2 font-medium text-gray-900 dark:text-white">
                          {sc.TableName}
                        </td>
                        <td className="py-1 px-2 text-right text-green-600">
                          {formatNumber(sc.TotalInserted)}
                        </td>
                        <td className="py-1 px-2 text-right text-primary-600">
                          {formatNumber(sc.TotalUpdated)}
                        </td>
                        <td className="py-1 px-2 text-right text-red-600">
                          {formatNumber(sc.TotalDeleted)}
                        </td>
                        <td className="py-1 px-2 text-right text-gray-500">
                          {formatDate(sc.LastSyncDate)}
                        </td>
                        <td className="py-1 px-2 text-center">
                          {sc.LastStatus === 'success' || sc.LastStatus === 'OK' ? (
                            <span className="text-green-600">OK</span>
                          ) : sc.LastStatus === 'error' ? (
                            <span className="text-red-600">Erreur</span>
                          ) : (
                            <span className="text-gray-400">{sc.LastStatus || '-'}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">Aucune donnee SyncControl disponible</p>
            )}

            {/* Top tables par nombre de lignes */}
            {dwh.table_rows && dwh.table_rows.length > 0 && (
              <div className="mt-3">
                <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Top tables par nombre de lignes
                </h4>
                <div className="flex flex-wrap gap-2">
                  {dwh.table_rows.slice(0, 10).map(t => (
                    <span
                      key={t.table_name}
                      className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs"
                    >
                      {t.table_name}: <strong>{formatNumber(t.row_count)}</strong>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

export default function SyncMonitoringDashboard() {
  const [data, setData] = useState([])
  const [totals, setTotals] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedDwh, setExpandedDwh] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const loadData = useCallback(async () => {
    try {
      const res = await getSyncDashboard()
      const result = res.data
      setData(result.data || [])
      setTotals(result.totals || {})
      setError(null)
    } catch (err) {
      console.error('Erreur chargement monitoring:', err)
      setError('Erreur lors du chargement des donnees de monitoring')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [loadData])

  const handleRefresh = () => {
    setRefreshing(true)
    loadData()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <RefreshCw className="animate-spin text-primary-600" size={24} />
        <span className="ml-2 text-gray-500">Chargement du monitoring...</span>
      </div>
    )
  }

  return (
    <div>
      {/* Refresh + auto-refresh */}
      <div className="flex justify-between items-center mb-4">
        <div className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
          <Clock size={14} />
          Actualisation automatique toutes les 30s
        </div>
        <button
          className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-2"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Actualiser
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg">
          {error}
        </div>
      )}

      {/* Cartes resumees */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <SummaryCard
          icon={HardDrive}
          label="Occupation totale"
          value={formatSize(totals.total_db_size_mb)}
          color="blue"
        />
        <SummaryCard
          icon={Rows3}
          label="Total lignes DWH"
          value={formatNumber(totals.total_rows)}
          color="purple"
        />
        <SummaryCard
          icon={ArrowUpCircle}
          label="Total inserees"
          value={formatNumber(totals.total_inserted)}
          color="green"
        />
        <SummaryCard
          icon={ArrowRightLeft}
          label="Total modifiees"
          value={formatNumber(totals.total_updated)}
          color="cyan"
        />
      </div>

      {/* Tableau par DWH */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-900 text-left">
              <th className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300">DWH</th>
              <th className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300 text-right">Taille DB</th>
              <th className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300 text-right">Total Lignes</th>
              <th className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300 text-right">Inserees</th>
              <th className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300 text-right">Modifiees</th>
              <th className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300 text-center">Status</th>
              <th className="px-4 py-3 w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {data.map(dwh => (
              <DWHRow
                key={dwh.dwh_code}
                dwh={dwh}
                expanded={expandedDwh === dwh.dwh_code}
                onToggle={() => setExpandedDwh(
                  expandedDwh === dwh.dwh_code ? null : dwh.dwh_code
                )}
              />
            ))}
          </tbody>
        </table>
        {data.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            <Database size={48} className="mx-auto mb-4 opacity-50" />
            <p>Aucun DWH configure</p>
          </div>
        )}
      </div>
    </div>
  )
}
