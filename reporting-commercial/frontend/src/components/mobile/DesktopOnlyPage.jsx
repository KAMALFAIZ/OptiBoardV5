import { Monitor } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

export default function DesktopOnlyPage() {
  const { logout } = useAuth()

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900 p-6 text-center">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 max-w-sm w-full">
        <div className="flex justify-center mb-4">
          <div className="bg-primary-100 dark:bg-primary-900 rounded-full p-4">
            <Monitor className="w-10 h-10 text-primary-600 dark:text-primary-400" />
          </div>
        </div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
          Disponible sur Desktop
        </h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">
          Cette fonctionnalité n'est pas disponible sur mobile.
          Veuillez utiliser un ordinateur pour y accéder.
        </p>
        <button
          onClick={() => window.history.back()}
          className="w-full py-3 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-medium text-sm transition-colors mb-3"
        >
          Retour
        </button>
        <button
          onClick={() => logout()}
          className="w-full py-3 rounded-xl border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium text-sm transition-colors"
        >
          Déconnexion
        </button>
      </div>
    </div>
  )
}
