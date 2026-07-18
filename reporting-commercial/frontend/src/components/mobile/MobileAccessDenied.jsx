import { SmartphoneNfc } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

// Écran affiché quand un utilisateur ouvre l'app sur mobile alors que son
// compte n'a pas l'accès mobile (mobile_access=0). L'accès desktop reste ouvert.
export default function MobileAccessDenied() {
  const { logout } = useAuth()

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900 p-6 text-center">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 max-w-sm w-full">
        <div className="flex justify-center mb-4">
          <div className="bg-amber-100 dark:bg-amber-900/40 rounded-full p-4">
            <SmartphoneNfc className="w-10 h-10 text-amber-600 dark:text-amber-400" />
          </div>
        </div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
          Accès mobile désactivé
        </h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">
          Votre compte n'est pas autorisé à utiliser l'application sur mobile.
          Connectez-vous depuis un ordinateur ou contactez votre administrateur.
        </p>
        <button
          onClick={() => logout()}
          className="w-full py-3 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-medium text-sm transition-colors"
        >
          Déconnexion
        </button>
      </div>
    </div>
  )
}
