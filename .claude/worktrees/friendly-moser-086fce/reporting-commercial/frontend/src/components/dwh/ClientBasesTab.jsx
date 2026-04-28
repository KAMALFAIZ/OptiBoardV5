import {
  Server, CheckCircle, XCircle, AlertCircle, Loader2, RefreshCw,
  Upload, HardDrive, Database, RotateCcw, Plus
} from 'lucide-react'

export default function ClientBasesTab({
  clientDBs, clientDBLoading, clientDBStats,
  syncing, syncingAll, detailLoading,
  handleMigrateAll, handleSyncAllClients, loadClientDatabases,
  loadClientDBDetail, handleSyncClient, handleResetClient, handleCreateSingleClientDB
}) {
  return (
    <>
      {/* Stats Bases Client */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Server className="text-blue-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{clientDBStats.total}</p>
              <p className="text-sm text-gray-500">Bases Client</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <CheckCircle className="text-green-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{clientDBStats.healthy}</p>
              <p className="text-sm text-gray-500">Connectees</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
              <XCircle className="text-red-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{clientDBStats.unhealthy}</p>
              <p className="text-sm text-gray-500">En erreur</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
              <Upload className="text-orange-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{clientDBStats.pending}</p>
              <p className="text-sm text-gray-500">Migration pendante</p>
            </div>
          </div>
        </div>
      </div>

      {/* Actions groupees */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={handleMigrateAll}
          disabled={clientDBStats.pending === 0}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-40 text-white rounded-lg flex items-center gap-2 text-sm"
        >
          <Upload size={16} /> Migrer tous
        </button>
        <button
          onClick={handleSyncAllClients}
          disabled={syncingAll || clientDBStats.healthy === 0}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-lg flex items-center gap-2 text-sm"
        >
          {syncingAll ? <Loader2 className="animate-spin" size={16} /> : <RefreshCw size={16} />}
          Synchroniser tous
        </button>
        <button
          onClick={loadClientDatabases}
          disabled={clientDBLoading}
          className="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg flex items-center gap-2 text-sm"
        >
          {clientDBLoading ? <Loader2 className="animate-spin" size={16} /> : <RefreshCw size={16} />}
          Actualiser
        </button>
      </div>

      {/* Tableau des bases client */}
      {clientDBLoading ? (
        <div className="flex justify-center items-center py-12">
          <Loader2 className="animate-spin text-primary-600" size={32} />
        </div>
      ) : clientDBs.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <HardDrive className="mx-auto text-gray-400 mb-4" size={48} />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Aucune base client</h3>
          <p className="text-gray-500 mb-4">Les bases client seront creees lors de l&apos;ajout de DWH</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-700/50 text-left text-sm text-gray-500 dark:text-gray-400">
                <th className="px-4 py-3 font-medium">Client</th>
                <th className="px-4 py-3 font-medium">Base</th>
                <th className="px-4 py-3 font-medium text-center">Statut</th>
                <th className="px-4 py-3 font-medium text-right">Tables</th>
                <th className="px-4 py-3 font-medium text-right">Lignes</th>
                <th className="px-4 py-3 font-medium text-right">Taille</th>
                <th className="px-4 py-3 font-medium text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {clientDBs.map(db => (
                <tr key={db.dwh_code} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900 dark:text-white">{db.dwh_nom}</div>
                    <div className="text-xs text-gray-500">{db.dwh_code}</div>
                  </td>
                  <td className="px-4 py-3 font-mono text-sm text-gray-700 dark:text-gray-300">{db.db_name}</td>
                  <td className="px-4 py-3 text-center">
                    {db.connection_status === 'ok' ? (
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-600 rounded-full">
                        <CheckCircle size={14} /> OK
                      </span>
                    ) : db.connection_status === 'not_configured' ? (
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-600 rounded-full">
                        <AlertCircle size={14} /> Non cree
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-600 rounded-full">
                        <XCircle size={14} /> Erreur
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-sm">{db.tables_count}</td>
                  <td className="px-4 py-3 text-right text-sm">{(db.total_rows || 0).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-sm">{db.size_mb} MB</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      {db.connection_status === 'ok' ? (
                        <>
                          <button
                            onClick={() => loadClientDBDetail(db.dwh_code)}
                            disabled={detailLoading}
                            className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                            title="Details"
                          >
                            <Database size={16} />
                          </button>
                          <button
                            onClick={() => handleSyncClient(db.dwh_code)}
                            disabled={syncing[db.dwh_code]}
                            className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
                            title="Synchroniser"
                          >
                            {syncing[db.dwh_code]
                              ? <Loader2 className="animate-spin" size={16} />
                              : <RefreshCw size={16} />}
                          </button>
                          <button
                            onClick={() => handleResetClient(db.dwh_code)}
                            className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                            title="Reinitialiser"
                          >
                            <RotateCcw size={16} />
                          </button>
                        </>
                      ) : db.connection_status === 'not_configured' ? (
                        <button
                          onClick={() => handleCreateSingleClientDB(db.dwh_code)}
                          className="px-3 py-1 text-xs bg-purple-600 hover:bg-purple-700 text-white rounded-lg flex items-center gap-1"
                        >
                          <Plus size={14} /> Creer
                        </button>
                      ) : (
                        <span className="text-xs text-red-500" title={db.error}>Erreur connexion</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
