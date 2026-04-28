import { useState, useEffect } from 'react'
import { Brain, Play, CheckCircle, XCircle, Clock, RefreshCw, ChevronDown } from 'lucide-react'
import api from '../services/api'

export default function DigestAdmin() {
  const [status, setStatus]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [dwhCode, setDwhCode] = useState('')

  const loadStatus = async () => {
    try {
      const res = await api.get('/admin/digest/status')
      setStatus(res.data)
    } catch { /* ignore */ }
  }

  useEffect(() => { loadStatus() }, [])

  const triggerAll = async () => {
    setLoading(true); setResult(null)
    try {
      const res = await api.post('/admin/digest/trigger')
      setResult({ success: true, message: res.data.message || 'Digest déclenché pour tous les DWHs' })
    } catch (err) {
      setResult({ success: false, message: err.response?.data?.detail || 'Erreur lors du déclenchement' })
    } finally {
      setLoading(false)
    }
  }

  const triggerOne = async () => {
    if (!dwhCode.trim()) return
    setLoading(true); setResult(null)
    try {
      const res = await api.post(`/admin/digest/trigger/${dwhCode.trim()}`)
      setResult({ success: true, message: res.data.message || `Digest envoyé pour ${dwhCode}` })
    } catch (err) {
      setResult({ success: false, message: err.response?.data?.detail || 'Erreur lors du déclenchement' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900/30 rounded-xl flex items-center justify-center">
          <Brain className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Digest IA Hebdomadaire</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Résumé exécutif généré par IA — envoyé chaque lundi à 8h aux utilisateurs Direction
          </p>
        </div>
      </div>

      {/* Statut scheduler */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 dark:text-white">Statut du planificateur</h2>
          <button
            onClick={loadStatus}
            className="text-gray-400 hover:text-indigo-600 transition-colors"
            title="Rafraîchir"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        {status ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              {status.scheduled
                ? <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                : <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />}
              <span className="text-gray-700 dark:text-gray-300">
                {status.scheduled ? 'Planifié — Lundi 08:00' : 'Non planifié'}
              </span>
            </div>
            {status.next_run && (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Clock className="w-4 h-4 flex-shrink-0" />
                Prochain envoi : {new Date(status.next_run).toLocaleString('fr-FR')}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-400">Chargement...</p>
        )}
      </div>

      {/* Déclenchement manuel */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
        <h2 className="font-semibold text-gray-900 dark:text-white">Déclencher manuellement</h2>

        {/* Tous les DWHs */}
        <div className="flex items-center gap-3">
          <button
            onClick={triggerAll}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-colors"
          >
            {loading
              ? <><RefreshCw className="w-4 h-4 animate-spin" />Envoi en cours...</>
              : <><Play className="w-4 h-4" />Envoyer à tous les DWHs</>}
          </button>
          <span className="text-xs text-gray-400">Envoi immédiat à tous les clients actifs</span>
        </div>

        <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Ou envoyer à un DWH spécifique :</p>
          <div className="flex gap-2">
            <input
              type="text"
              value={dwhCode}
              onChange={e => setDwhCode(e.target.value)}
              placeholder="Code DWH (ex: DWH_CLIENT01)"
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
            <button
              onClick={triggerOne}
              disabled={loading || !dwhCode.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-800 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-colors"
            >
              <ChevronDown className="w-4 h-4 rotate-[-90deg]" />
              Envoyer
            </button>
          </div>
        </div>
      </div>

      {/* Résultat */}
      {result && (
        <div className={`flex items-start gap-2 p-4 rounded-xl border text-sm ${
          result.success
            ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
            : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-600 dark:text-red-400'
        }`}>
          {result.success
            ? <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            : <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />}
          {result.message}
        </div>
      )}

      {/* Explication */}
      <div className="bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-3 text-sm text-gray-600 dark:text-gray-400">
        <p className="font-medium text-gray-800 dark:text-gray-200">Comment fonctionne le digest ?</p>
        <ul className="space-y-1.5 list-disc list-inside">
          <li>Récupère les KPIs de la semaine précédente (CA, encours, retards)</li>
          <li>Génère un résumé exécutif via l'IA configurée (Claude / GPT / Ollama)</li>
          <li>Envoie un email HTML formaté aux utilisateurs avec rôle <strong>Direction / Admin</strong></li>
          <li>Planifié automatiquement chaque <strong>lundi à 8h00</strong></li>
        </ul>
      </div>
    </div>
  )
}
