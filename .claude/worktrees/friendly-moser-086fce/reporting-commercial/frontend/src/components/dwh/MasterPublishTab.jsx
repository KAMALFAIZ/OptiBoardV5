import {
  Database, CheckCircle, Clock, Upload, Loader2, RefreshCw,
  ArrowUpCircle, Settings, Search
} from 'lucide-react'

export default function MasterPublishTab({
  masterEntities, masterLoading, masterStats,
  masterFilter, setMasterFilter, masterSearch, setMasterSearch,
  masterSelected, setMasterSelected,
  publishingAll,
  handlePublishAll, handlePublishSelected, loadMasterEntities,
  handleGenerateCodes, selectAllMasterEntities, getFilteredMasterEntities,
  openPublishModal, ENTITY_TYPE_ICONS
}) {
  return (
    <>
      {/* Stats Master */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Database className="text-blue-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{masterStats.total}</p>
              <p className="text-sm text-gray-500">Entites Master</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <CheckCircle className="text-green-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{masterStats.with_code}</p>
              <p className="text-sm text-gray-500">Avec code</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
              <Clock className="text-orange-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {masterStats.total - masterStats.with_code}
              </p>
              <p className="text-sm text-gray-500">Sans code</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Upload className="text-purple-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {Object.keys(masterEntities).length}
              </p>
              <p className="text-sm text-gray-500">Types</p>
            </div>
          </div>
        </div>
      </div>

      {/* Actions + Filtres */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <button
          onClick={handlePublishAll}
          disabled={publishingAll || masterStats.with_code === 0}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 text-sm"
        >
          {publishingAll ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
          Publier tout
        </button>
        {masterSelected.length > 0 && (
          <button
            onClick={handlePublishSelected}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm"
          >
            <ArrowUpCircle size={16} />
            Publier la selection ({masterSelected.length})
          </button>
        )}
        <button
          onClick={loadMasterEntities}
          disabled={masterLoading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg text-sm"
        >
          <RefreshCw size={16} className={masterLoading ? 'animate-spin' : ''} />
          Rafraichir
        </button>
        <button
          onClick={() => masterSelected.length > 0 ? setMasterSelected([]) : selectAllMasterEntities()}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg text-sm"
        >
          {masterSelected.length > 0 ? 'Deselectionner tout' : 'Selectionner tout'}
        </button>
        {masterStats.total > masterStats.with_code && (
          <button
            onClick={handleGenerateCodes}
            className="flex items-center gap-2 px-4 py-2 bg-orange-100 dark:bg-orange-900/30 hover:bg-orange-200 text-orange-700 rounded-lg text-sm"
          >
            <Settings size={16} />
            Generer les codes ({masterStats.total - masterStats.with_code})
          </button>
        )}

        <div className="flex-1" />

        {/* Filtre par type */}
        <select
          value={masterFilter}
          onChange={e => setMasterFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm"
        >
          <option value="all">Tous les types</option>
          <option value="gridviews">GridViews</option>
          <option value="pivots">Pivots</option>
          <option value="dashboards">Dashboards</option>
          <option value="datasources">DataSources</option>
          <option value="menus">Menus</option>
        </select>

        {/* Recherche */}
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={masterSearch}
            onChange={e => setMasterSearch(e.target.value)}
            placeholder="Rechercher..."
            className="pl-9 pr-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm w-48"
          />
        </div>
      </div>

      {/* Tableau des entites */}
      {masterLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={32} className="animate-spin text-blue-600" />
          <span className="ml-3 text-gray-500">Chargement des entites Master...</span>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={masterSelected.length > 0 && masterSelected.length === getFilteredMasterEntities().filter(i => i.code).length}
                    onChange={() => masterSelected.length > 0 ? setMasterSelected([]) : selectAllMasterEntities()}
                    className="rounded"
                  />
                </th>
                <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Type</th>
                <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Nom</th>
                <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Code</th>
                <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Modifie</th>
                <th className="text-right text-xs font-medium text-gray-500 uppercase px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {getFilteredMasterEntities().map((item) => {
                const typeConf = ENTITY_TYPE_ICONS[item.entity_type] || ENTITY_TYPE_ICONS.gridviews
                const TypeIcon = typeConf.icon
                const key = `${item.entity_type}::${item.code}`
                const isSelected = masterSelected.includes(key)

                return (
                  <tr
                    key={`${item.entity_type}-${item.id}`}
                    className={`hover:bg-gray-50 dark:hover:bg-gray-700/30 ${isSelected ? 'bg-blue-50 dark:bg-blue-900/10' : ''}`}
                  >
                    <td className="px-4 py-3">
                      {item.code ? (
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {
                            const k = `${item.entity_type}::${item.code}`
                            setMasterSelected(prev =>
                              prev.includes(k) ? prev.filter(x => x !== k) : [...prev, k]
                            )
                          }}
                          className="rounded"
                        />
                      ) : (
                        <span className="text-gray-300">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${typeConf.bg} ${typeConf.color}`}>
                        <TypeIcon size={12} />
                        {item.entity_label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                      {item.nom}
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-gray-500">
                      {item.code || <span className="text-orange-500 italic">Sans code</span>}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {item.date_modification
                        ? new Date(item.date_modification).toLocaleDateString('fr-FR', {
                            day: '2-digit', month: '2-digit', year: 'numeric',
                            hour: '2-digit', minute: '2-digit'
                          })
                        : '-'
                      }
                    </td>
                    <td className="px-4 py-3 text-right">
                      {item.code ? (
                        <button
                          onClick={() => openPublishModal(item.entity_type, item.code, item.nom)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 hover:text-white hover:bg-blue-600 border border-blue-300 hover:border-blue-600 rounded-lg transition-colors"
                        >
                          <Upload size={12} />
                          Publier
                        </button>
                      ) : (
                        <span className="text-xs text-gray-400 italic">Code requis</span>
                      )}
                    </td>
                  </tr>
                )
              })}
              {getFilteredMasterEntities().length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-gray-500">
                    {masterSearch ? 'Aucun resultat pour cette recherche' : 'Aucune entite trouvee'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Resume par type */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-6">
        {Object.entries(masterEntities).map(([type, data]) => {
          const typeConf = ENTITY_TYPE_ICONS[type] || ENTITY_TYPE_ICONS.gridviews
          const TypeIcon = typeConf.icon
          return (
            <button
              key={type}
              onClick={() => setMasterFilter(masterFilter === type ? 'all' : type)}
              className={`p-3 rounded-xl border transition-colors text-left ${
                masterFilter === type
                  ? 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-200'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <TypeIcon size={14} className={typeConf.color} />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-300">{data.label}s</span>
              </div>
              <p className="text-lg font-bold text-gray-900 dark:text-white">{data.count}</p>
              <p className="text-xs text-gray-500">{data.with_code} avec code</p>
            </button>
          )
        })}
      </div>
    </>
  )
}
