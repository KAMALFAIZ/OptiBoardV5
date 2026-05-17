import { BookOpen, X, Zap } from 'lucide-react'

export default function ReportDocModal({ title, config, onClose }) {
  if (!config) return null
  const { doc_description, doc_fields, doc_formula, doc_advantage } = config

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/30 dark:to-blue-900/20">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            <h3 className="text-base font-bold text-gray-800 dark:text-white">{title}</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
          {doc_description && (
            <div>
              <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Objectif</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{doc_description}</p>
            </div>
          )}
          {doc_fields && (
            <div>
              <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Descriptif des colonnes</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{doc_fields}</p>
            </div>
          )}
          {doc_formula && (
            <div>
              <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Formule / Logique</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 font-mono bg-gray-50 dark:bg-gray-900/50 px-3 py-2 rounded-lg whitespace-pre-wrap">{doc_formula}</p>
            </div>
          )}
          {doc_advantage && (
            <div>
              <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Avantage</h4>
              <div className="flex gap-2 items-start">
                <Zap className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{doc_advantage}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function hasDoc(config) {
  return !!(config?.doc_description || config?.doc_fields || config?.doc_formula || config?.doc_advantage)
}
