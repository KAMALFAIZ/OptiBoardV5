import { useState } from 'react'
import { X, Send, Lightbulb } from 'lucide-react'
import api from '../../services/api'

export default function ETLProposalModal({ onClose, onSuccess }) {
  const [form, setForm] = useState({
    table_name: '',
    target_table: '',
    source_query: '',
    description: '',
    justification: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.table_name || !form.description || !form.justification) {
      setError('Nom de table, description et justification sont obligatoires')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/etl-tables/proposals', form)
      onSuccess?.()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la soumission')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
              <Lightbulb className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Proposer une table ETL
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Votre demande sera examinée par l'administrateur central
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-400">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Table source (Sage) <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.table_name}
                onChange={e => setForm(f => ({ ...f, table_name: e.target.value }))}
                placeholder="ex: F_ARTICLE"
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Table cible (DWH)
              </label>
              <input
                type="text"
                value={form.target_table}
                onChange={e => setForm(f => ({ ...f, target_table: e.target.value }))}
                placeholder="ex: Articles"
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Décrire les données contenues dans cette table"
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Justification métier <span className="text-red-500">*</span>
            </label>
            <textarea
              value={form.justification}
              onChange={e => setForm(f => ({ ...f, justification: e.target.value }))}
              rows={3}
              placeholder="Pourquoi avez-vous besoin de cette table ? Quel rapport ou analyse ?"
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Requête SQL (optionnel)
            </label>
            <textarea
              value={form.source_query}
              onChange={e => setForm(f => ({ ...f, source_query: e.target.value }))}
              rows={3}
              placeholder="SELECT ... FROM F_ARTICLE WHERE ..."
              className="w-full px-3 py-2 text-sm font-mono border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none resize-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 rounded-lg transition-colors"
            >
              <Send className="w-4 h-4" />
              {saving ? 'Envoi...' : 'Soumettre la proposition'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
