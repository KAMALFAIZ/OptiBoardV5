import { Database, X, AlertCircle, Loader2, RefreshCw, RotateCcw } from 'lucide-react'

export default function ClientDBDetailModal({
  show, onClose, detailData, syncing, resetting,
  handleSyncClient, handleResetClient, SYNCABLE_TABLES
}) {
  if (!show || !detailData) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Database size={20} className="text-primary-600" />
              {detailData.db_name}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {detailData.dwh_nom} &middot; {detailData.server_version?.substring(0, 60)}
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <X size={20} />
          </button>
        </div>

        {/* Stats */}
        <div className="p-6 grid grid-cols-4 gap-4">
          <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <p className="text-2xl font-bold text-blue-600">{detailData.tables_count}</p>
            <p className="text-xs text-gray-500">Tables</p>
          </div>
          <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <p className="text-2xl font-bold text-green-600">{(detailData.total_rows || 0).toLocaleString()}</p>
            <p className="text-xs text-gray-500">Lignes</p>
          </div>
          <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <p className="text-2xl font-bold text-purple-600">{detailData.size_data_mb} MB</p>
            <p className="text-xs text-gray-500">Donnees</p>
          </div>
          <div className="text-center p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
            <p className="text-2xl font-bold text-orange-600">{detailData.size_log_mb} MB</p>
            <p className="text-xs text-gray-500">Log</p>
          </div>
        </div>

        {/* Alerte tables manquantes */}
        {detailData.missing_tables?.length > 0 && (
          <div className="mx-6 mb-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <p className="text-sm text-amber-700 dark:text-amber-400 font-medium">
              <AlertCircle size={14} className="inline mr-1 -mt-0.5" />
              Tables manquantes: {detailData.missing_tables.join(', ')}
            </p>
          </div>
        )}

        {/* Liste des tables */}
        <div className="px-6 pb-4">
          <h3 className="font-medium text-gray-900 dark:text-white mb-3">
            Tables ({detailData.tables?.length || 0})
          </h3>
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden max-h-[300px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-50 dark:bg-gray-700/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">Table</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-500">Lignes</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-500">Modifie</th>
                  <th className="px-4 py-2 text-center font-medium text-gray-500">Sync</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {(detailData.tables || []).map(t => (
                  <tr key={t.name} className="hover:bg-gray-50 dark:hover:bg-gray-700/20">
                    <td className="px-4 py-2 font-mono text-xs text-gray-700 dark:text-gray-300">{t.name}</td>
                    <td className="px-4 py-2 text-right text-gray-600 dark:text-gray-400">
                      {(t.rows || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-right text-xs text-gray-400">{t.modified?.substring(0, 16)}</td>
                    <td className="px-4 py-2 text-center">
                      {SYNCABLE_TABLES.includes(t.name) && (
                        <button
                          onClick={() => handleSyncClient(detailData.dwh_code, [t.name])}
                          disabled={syncing[detailData.dwh_code]}
                          className="text-xs px-2 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/40 rounded transition-colors"
                        >
                          Sync
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-between">
          <button
            onClick={() => handleResetClient(detailData.dwh_code)}
            disabled={resetting}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg flex items-center gap-2 text-sm"
          >
            {resetting ? <Loader2 className="animate-spin" size={16} /> : <RotateCcw size={16} />}
            Reinitialiser
          </button>
          <button
            onClick={() => handleSyncClient(detailData.dwh_code)}
            disabled={syncing[detailData.dwh_code]}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg flex items-center gap-2 text-sm"
          >
            {syncing[detailData.dwh_code]
              ? <Loader2 className="animate-spin" size={16} />
              : <RefreshCw size={16} />}
            Synchroniser tout
          </button>
        </div>
      </div>
    </div>
  )
}
