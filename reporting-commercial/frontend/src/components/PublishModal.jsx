import React, { useState, useEffect, useCallback } from 'react'
import { X, Upload, Check, AlertCircle, Loader2, RefreshCw, CheckCircle, XCircle, Clock } from 'lucide-react'
import api from '../services/api'

const STATUS_CONFIG = {
  synced: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20', label: 'A jour' },
  outdated: { icon: Clock, color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-900/20', label: 'Obsolete' },
  missing: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/20', label: 'Absent' },
  error: { icon: AlertCircle, color: 'text-gray-500', bg: 'bg-gray-50 dark:bg-gray-900/20', label: 'Erreur' },
  unknown: { icon: AlertCircle, color: 'text-gray-400', bg: 'bg-gray-50 dark:bg-gray-900/20', label: 'Inconnu' }
}

export default function PublishModal({ isOpen, onClose, entityType, entityCode, entityName }) {
  const [clients, setClients] = useState([])
  const [syncStatus, setSyncStatus] = useState(null)
  const [selectedClients, setSelectedClients] = useState([])
  const [loading, setLoading] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [publishResult, setPublishResult] = useState(null)

  const loadData = useCallback(async () => {
    if (!isOpen || !entityType || !entityCode) return
    setLoading(true)
    setPublishResult(null)
    try {
      const [clientsRes, statusRes] = await Promise.all([
        api.get('/master/clients'),
        api.get(`/master/sync-status?entity_type=${entityType}&code=${entityCode}`)
      ])
      if (clientsRes.data.success) {
        setClients(clientsRes.data.data)
        // Pre-selectionner tous les clients connectes
        setSelectedClients(clientsRes.data.data.filter(c => c.connected).map(c => c.code))
      }
      if (statusRes.data.success) {
        setSyncStatus(statusRes.data.data)
      }
    } catch (err) {
      console.error('Erreur chargement publish data:', err)
    } finally {
      setLoading(false)
    }
  }, [isOpen, entityType, entityCode])

  useEffect(() => {
    loadData()
  }, [loadData])

  const toggleClient = (code) => {
    setSelectedClients(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    )
  }

  const selectAll = () => {
    setSelectedClients(clients.filter(c => c.connected).map(c => c.code))
  }

  const deselectAll = () => {
    setSelectedClients([])
  }

  const handlePublish = async () => {
    if (selectedClients.length === 0) return
    setPublishing(true)
    setPublishResult(null)
    try {
      const res = await api.post('/master/publish', {
        entities: [{ type: entityType, codes: [entityCode] }],
        clients: selectedClients,
        mode: 'upsert'
      })
      setPublishResult(res.data)
      // Recharger les statuts apres publication
      try {
        const statusRes = await api.get(`/master/sync-status?entity_type=${entityType}&code=${entityCode}`)
        if (statusRes.data.success) setSyncStatus(statusRes.data.data)
      } catch (e) { /* ignore */ }
    } catch (err) {
      setPublishResult({ success: false, error: err.message })
    } finally {
      setPublishing(false)
    }
  }

  const getClientStatus = (clientCode) => {
    if (!syncStatus?.clients) return 'unknown'
    const found = syncStatus.clients.find(c => c.code === clientCode)
    return found?.status || 'unknown'
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Upload size={20} className="text-blue-600" />
              Publier vers les clients
            </h2>
            <p className="text-sm text-gray-500 mt-1">{entityName} ({entityCode})</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={24} className="animate-spin text-blue-600" />
              <span className="ml-3 text-gray-500">Chargement...</span>
            </div>
          ) : (
            <>
              {/* Selection clients */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Clients cibles ({selectedClients.length}/{clients.filter(c => c.connected).length})
                  </h3>
                  <div className="flex gap-2">
                    <button onClick={selectAll} className="text-xs text-blue-600 hover:underline">
                      Tout
                    </button>
                    <button onClick={deselectAll} className="text-xs text-gray-500 hover:underline">
                      Aucun
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  {clients.map(client => {
                    const status = getClientStatus(client.code)
                    const statusConf = STATUS_CONFIG[status] || STATUS_CONFIG.unknown
                    const StatusIcon = statusConf.icon
                    const isDisabled = !client.connected

                    return (
                      <label
                        key={client.code}
                        className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors
                          ${isDisabled
                            ? 'opacity-50 cursor-not-allowed bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700'
                            : selectedClients.includes(client.code)
                              ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-600'
                              : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-200'
                          }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedClients.includes(client.code)}
                          onChange={() => !isDisabled && toggleClient(client.code)}
                          disabled={isDisabled}
                          className="rounded text-blue-600"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm text-gray-900 dark:text-white">{client.nom}</div>
                          <div className="text-xs text-gray-500">{client.db_name}</div>
                        </div>
                        <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${statusConf.bg} ${statusConf.color}`}>
                          <StatusIcon size={12} />
                          {statusConf.label}
                        </div>
                      </label>
                    )
                  })}
                </div>

                {clients.length === 0 && (
                  <p className="text-sm text-gray-500 text-center py-4">Aucun client configure</p>
                )}
              </div>

              {/* Resultat publication */}
              {publishResult && (
                <div className={`p-4 rounded-lg mb-4 ${
                  publishResult.success
                    ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                    : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {publishResult.success
                      ? <CheckCircle size={16} className="text-green-600" />
                      : <XCircle size={16} className="text-red-600" />
                    }
                    <span className={`font-medium text-sm ${publishResult.success ? 'text-green-700' : 'text-red-700'}`}>
                      {publishResult.success ? 'Publication terminee' : 'Erreur de publication'}
                    </span>
                  </div>
                  {publishResult.total_published > 0 && (
                    <p className="text-xs text-green-600">{publishResult.total_published} entite(s) publiee(s)</p>
                  )}
                  {publishResult.total_updated > 0 && (
                    <p className="text-xs text-blue-600">{publishResult.total_updated} entite(s) mise(s) a jour</p>
                  )}
                  {publishResult.total_failed > 0 && (
                    <p className="text-xs text-red-600">{publishResult.total_failed} echec(s)</p>
                  )}
                  {publishResult.error && (
                    <p className="text-xs text-red-600 mt-1">{publishResult.error}</p>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-5 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Actualiser
          </button>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
            >
              Fermer
            </button>
            <button
              onClick={handlePublish}
              disabled={publishing || selectedClients.length === 0}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 transition-colors"
            >
              {publishing ? (
                <><Loader2 size={14} className="animate-spin" /> Publication...</>
              ) : (
                <><Upload size={14} /> Publier ({selectedClients.length})</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
