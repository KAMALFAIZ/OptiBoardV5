import { useState } from 'react'
import {
  Building2, Plus, Edit2, Trash2, Server, Database, Users, Mail,
  CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronRight,
  MapPin, Phone, Link2, Download, XCircle, Info, Menu as MenuIcon,
  RefreshCw, FlaskConical
} from 'lucide-react'
import api from '../../services/api'

export default function DWHClientsTab({
  loading, dwhList, expandedDWH, toggleExpand,
  openCreateModal, openEditModal, openSMTPModal, openSourcesModal, handleDeleteDWH
}) {
  const [dlStatus, setDlStatus] = useState({})     // { [code]: 'loading'|'ok'|'error' }
  const [menuStatus, setMenuStatus] = useState({}) // { [code]: 'loading'|'ok'|'exists'|'error' }
  const [syncStatus, setSyncStatus] = useState({}) // { [code]: 'loading'|'ok'|'error' }

  const handleSyncDemo = async (dwh) => {
    if (!confirm(`Réinitialiser les données démo de "${dwh.nom}" ?\nCela écrasera les alertes, abonnements et templates.`)) return
    setSyncStatus(s => ({ ...s, [dwh.code]: 'loading' }))
    try {
      await api.post(`/admin/dwh/${dwh.code}/sync-demo`)
      setSyncStatus(s => ({ ...s, [dwh.code]: 'ok' }))
      setTimeout(() => setSyncStatus(s => ({ ...s, [dwh.code]: null })), 3000)
    } catch {
      setSyncStatus(s => ({ ...s, [dwh.code]: 'error' }))
      setTimeout(() => setSyncStatus(s => ({ ...s, [dwh.code]: null })), 3000)
    }
  }

  const handleInitMenus = async (dwh) => {
    setMenuStatus(s => ({ ...s, [dwh.code]: 'loading' }))
    try {
      const res = await api.post(`/dwh-admin/${dwh.code}/init-menus`)
      if (res.data?.count > 0) {
        setMenuStatus(s => ({ ...s, [dwh.code]: 'ok' }))
      } else {
        setMenuStatus(s => ({ ...s, [dwh.code]: 'exists' }))
      }
      setTimeout(() => setMenuStatus(s => ({ ...s, [dwh.code]: null })), 4000)
    } catch {
      setMenuStatus(s => ({ ...s, [dwh.code]: 'error' }))
    }
  }

  const handleDownloadSql = async (dwh) => {
    setDlStatus(s => ({ ...s, [dwh.code]: 'loading' }))
    try {
      const res = await api.get(`/dwh-admin/${dwh.code}/optiboard-sql-script`, {
        responseType: 'blob'
      })
      const dbName = dwh.base_optiboard || `OptiBoard_clt${dwh.code}`
      const url = URL.createObjectURL(new Blob([res.data], { type: 'text/plain' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `init_${dbName}.sql`
      a.click()
      URL.revokeObjectURL(url)
      setDlStatus(s => ({ ...s, [dwh.code]: 'ok' }))
      setTimeout(() => setDlStatus(s => ({ ...s, [dwh.code]: null })), 4000)
    } catch (e) {
      setDlStatus(s => ({ ...s, [dwh.code]: 'error' }))
    }
  }

  return (
    <>
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Building2 className="text-blue-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{dwhList.length}</p>
              <p className="text-sm text-gray-500">DWH Clients</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <CheckCircle className="text-green-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {dwhList.filter(d => d.actif).length}
              </p>
              <p className="text-sm text-gray-500">Actifs</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Database className="text-purple-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {dwhList.reduce((acc, d) => acc + (d.sources_count || 0), 0)}
              </p>
              <p className="text-sm text-gray-500">Sources Sage</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
              <Users className="text-orange-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {dwhList.reduce((acc, d) => acc + (d.users_count || 0), 0)}
              </p>
              <p className="text-sm text-gray-500">Utilisateurs</p>
            </div>
          </div>
        </div>
      </div>

      {/* Liste des DWH */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <Loader2 className="animate-spin text-primary-600" size={32} />
        </div>
      ) : dwhList.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <Building2 className="mx-auto text-gray-400 mb-4" size={48} />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Aucun DWH configure
          </h3>
          <p className="text-gray-500 mb-4">
            Commencez par ajouter votre premier client DWH
          </p>
          <button
            onClick={openCreateModal}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg inline-flex items-center gap-2"
          >
            <Plus size={18} />
            Ajouter un DWH
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {dwhList.map((dwh) => (
            <div
              key={dwh.code}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
            >
              {/* Header DWH */}
              <div
                className="p-4 flex items-center gap-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50"
                onClick={() => toggleExpand(dwh.code)}
              >
                <button className="text-gray-400">
                  {expandedDWH === dwh.code ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                </button>

                {/* Logo */}
                <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center overflow-hidden">
                  {dwh.logo_url ? (
                    <img src={dwh.logo_url} alt={dwh.nom} className="w-full h-full object-contain" />
                  ) : (
                    <Building2 className="text-gray-400" size={24} />
                  )}
                </div>

                {/* Info principale */}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-900 dark:text-white">{dwh.nom}</h3>
                    <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-400">
                      {dwh.code}
                    </span>
                    {dwh.actif ? (
                      <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-600 rounded">
                        Actif
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-600 rounded">
                        Inactif
                      </span>
                    )}
                  </div>
                  {dwh.raison_sociale && (
                    <p className="text-sm text-gray-500">{dwh.raison_sociale}</p>
                  )}
                </div>

                {/* Stats */}
                <div className="flex items-center gap-6 text-sm text-gray-500">
                  <div className="flex items-center gap-1">
                    <Database size={16} />
                    <span>{dwh.sources_count || 0} sources</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Users size={16} />
                    <span>{dwh.users_count || 0} users</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Server size={16} />
                    <span className="font-mono text-xs">{dwh.serveur_dwh}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => openSourcesModal(dwh)}
                    className="p-2 text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg"
                    title="Gerer les sources Sage"
                  >
                    <Link2 size={18} />
                  </button>
                  <button
                    onClick={() => openSMTPModal(dwh)}
                    className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg"
                    title="Configuration SMTP"
                  >
                    <Mail size={18} />
                  </button>
                  <button
                    onClick={() => openEditModal(dwh)}
                    className="p-2 text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                    title="Modifier"
                  >
                    <Edit2 size={18} />
                  </button>
                  {(dwh.is_demo || dwh.code === 'KA') && (
                    <button
                      onClick={() => handleSyncDemo(dwh)}
                      disabled={syncStatus[dwh.code] === 'loading'}
                      className={`p-2 rounded-lg ${
                        syncStatus[dwh.code] === 'ok' ? 'text-green-600 bg-green-50' :
                        syncStatus[dwh.code] === 'error' ? 'text-red-600 bg-red-50' :
                        'text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20'
                      }`}
                      title="Synchroniser données démo"
                    >
                      {syncStatus[dwh.code] === 'loading'
                        ? <Loader2 size={18} className="animate-spin" />
                        : syncStatus[dwh.code] === 'ok'
                        ? <CheckCircle size={18} />
                        : <FlaskConical size={18} />}
                    </button>
                  )}
                  {!(dwh.is_demo || dwh.code === 'KA') && (
                    <button
                      onClick={() => handleDeleteDWH(dwh)}
                      className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                      title="Supprimer"
                    >
                      <Trash2 size={18} />
                    </button>
                  )}
                </div>
              </div>

              {/* Details expandus */}
              {expandedDWH === dwh.code && (
                <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-900/50">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    {/* Coordonnees */}
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                        <MapPin size={16} />
                        Coordonnees
                      </h4>
                      <div className="space-y-2 text-sm">
                        {dwh.adresse && <p className="text-gray-600 dark:text-gray-400">{dwh.adresse}</p>}
                        {dwh.ville && <p className="text-gray-600 dark:text-gray-400">{dwh.ville}, {dwh.pays}</p>}
                        {dwh.telephone && (
                          <p className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                            <Phone size={14} /> {dwh.telephone}
                          </p>
                        )}
                        {dwh.email && (
                          <p className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                            <Mail size={14} /> {dwh.email}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Connexion DWH */}
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                        <Database size={16} />
                        Base DWH
                      </h4>
                      <div className="space-y-2 text-sm font-mono">
                        <p className="text-gray-600 dark:text-gray-400">
                          Serveur: <span className="text-gray-900 dark:text-white">{dwh.serveur_dwh}</span>
                        </p>
                        <p className="text-gray-600 dark:text-gray-400">
                          Base: <span className="text-gray-900 dark:text-white">{dwh.base_dwh}</span>
                        </p>
                        <p className="text-gray-600 dark:text-gray-400">
                          User: <span className="text-gray-900 dark:text-white">{dwh.user_dwh}</span>
                        </p>
                      </div>
                    </div>

                    {/* Base OptiBoard */}
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                        <Server size={16} className="text-emerald-600" />
                        Base OptiBoard
                      </h4>
                      <div className="space-y-2 text-sm font-mono mb-3">
                        <p className="text-gray-600 dark:text-gray-400">
                          Serveur: <span className="text-gray-900 dark:text-white">
                            {dwh.serveur_optiboard || dwh.serveur_dwh || '—'}
                          </span>
                        </p>
                        <p className="text-gray-600 dark:text-gray-400">
                          Base: <span className="text-gray-900 dark:text-white">
                            {dwh.base_optiboard || `OptiBoard_clt${dwh.code}`}
                          </span>
                        </p>
                      </div>

                    </div>

                    {/* SMTP */}
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                        <Mail size={16} />
                        Configuration SMTP
                      </h4>
                      {dwh.smtp_configured ? (
                        <div className="space-y-2 text-sm">
                          <p className="flex items-center gap-2 text-green-600">
                            <CheckCircle size={14} /> Configure
                          </p>
                          <p className="text-gray-600 dark:text-gray-400 font-mono">
                            {dwh.smtp_server}:{dwh.smtp_port}
                          </p>
                        </div>
                      ) : (
                        <div className="text-sm">
                          <p className="flex items-center gap-2 text-amber-600">
                            <AlertCircle size={14} /> Non configure
                          </p>
                          <button
                            onClick={() => openSMTPModal(dwh)}
                            className="mt-2 text-primary-600 hover:underline text-sm"
                          >
                            Configurer maintenant
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  )
}
