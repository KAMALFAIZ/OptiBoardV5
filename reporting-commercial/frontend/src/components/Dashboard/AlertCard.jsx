import { AlertTriangle, AlertCircle, Info } from 'lucide-react'

export default function AlertCard({ alertes = [] }) {
  if (!alertes || alertes.length === 0) {
    return (
      <div className="card p-3">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Alertes</h3>
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 text-sm">
          <Info className="w-4 h-4" />
          <span>Aucune alerte</span>
        </div>
      </div>
    )
  }

  const getAlertIcon = (niveau) => {
    if (niveau === 'critical') return <AlertTriangle className="w-4 h-4 text-red-500" />
    if (niveau === 'warning') return <AlertCircle className="w-4 h-4 text-amber-500" />
    return <Info className="w-4 h-4 text-blue-500" />
  }

  const getAlertBg = (niveau) => {
    if (niveau === 'critical') return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
    if (niveau === 'warning') return 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'
    return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
  }

  return (
    <div className="card p-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
        Alertes ({alertes.length})
      </h3>
      <div className="space-y-2">
        {alertes.map((alerte, index) => (
          <div
            key={index}
            className={`flex items-start gap-2 p-2 rounded-md border ${getAlertBg(alerte.niveau)}`}
          >
            {getAlertIcon(alerte.niveau)}
            <div>
              <p className="font-medium text-gray-900 dark:text-white text-xs">
                {alerte.type}
              </p>
              <p className="text-xs text-gray-600 dark:text-gray-300">
                {alerte.message}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
