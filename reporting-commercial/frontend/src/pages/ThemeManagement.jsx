import { useState } from 'react'
import { useTheme, themes } from '../context/ThemeContext'
import { useAuth } from '../context/AuthContext'
import { Check, Sun, Moon, Palette, Sparkles, Minimize2, Maximize2 } from 'lucide-react'

export default function ThemeManagement() {
  const { currentTheme, changeTheme, darkMode, setDarkMode, compactMode, setCompactMode } = useTheme()
  const { user } = useAuth()
  const [saved, setSaved] = useState(false)

  const handleThemeChange = (themeId) => {
    changeTheme(themeId)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleDarkModeChange = (value) => {
    setDarkMode(value)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleCompactModeChange = (value) => {
    setCompactMode(value)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <Palette className="w-7 h-7 text-primary-600" />
          Gestion des Thèmes
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Personnalisez l'apparence de votre interface. Vos préférences sont sauvegardées pour votre compte.
        </p>
        {user && (
          <p className="text-sm text-primary-600 dark:text-primary-400 mt-2">
            Connecté en tant que: {user.nom} {user.prenom}
          </p>
        )}
      </div>

      {/* Notification de sauvegarde */}
      {saved && (
        <div className="mb-4 p-3 bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded-lg flex items-center gap-2 text-green-700 dark:text-green-400">
          <Check className="w-5 h-5" />
          <span>Thème sauvegardé avec succès!</span>
        </div>
      )}

      {/* Mode clair/sombre */}
      <div className="card p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5" />
          Mode d'affichage
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => handleDarkModeChange(false)}
            className={`
              p-4 rounded-xl border-2 transition-all duration-200
              ${!darkMode
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                : 'border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-gray-600'
              }
            `}
          >
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-xl bg-white border border-gray-200 flex items-center justify-center shadow-sm">
                <Sun className="w-8 h-8 text-amber-500" />
              </div>
              <div className="text-center">
                <p className="font-medium text-gray-900 dark:text-white">Mode Clair</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Interface lumineuse</p>
              </div>
              {!darkMode && (
                <div className="w-6 h-6 rounded-full bg-primary-500 flex items-center justify-center">
                  <Check className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          </button>

          <button
            onClick={() => handleDarkModeChange(true)}
            className={`
              p-4 rounded-xl border-2 transition-all duration-200
              ${darkMode
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                : 'border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-gray-600'
              }
            `}
          >
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-xl bg-gray-800 border border-gray-700 flex items-center justify-center shadow-sm">
                <Moon className="w-8 h-8 text-blue-400" />
              </div>
              <div className="text-center">
                <p className="font-medium text-gray-900 dark:text-white">Mode Sombre</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Réduit la fatigue oculaire</p>
              </div>
              {darkMode && (
                <div className="w-6 h-6 rounded-full bg-primary-500 flex items-center justify-center">
                  <Check className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          </button>
        </div>
      </div>

      {/* Mode compact */}
      <div className="card p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Minimize2 className="w-5 h-5" />
          Mode d'affichage compact
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Réduit les espacements et la taille des éléments pour afficher plus de contenu à l'écran.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => handleCompactModeChange(false)}
            className={`
              p-4 rounded-xl border-2 transition-all duration-200
              ${!compactMode
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                : 'border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-gray-600'
              }
            `}
          >
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-xl bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center">
                <Maximize2 className="w-8 h-8 text-gray-600 dark:text-gray-400" />
              </div>
              <div className="text-center">
                <p className="font-medium text-gray-900 dark:text-white">Normal</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Espacement standard</p>
              </div>
              {!compactMode && (
                <div className="w-6 h-6 rounded-full bg-primary-500 flex items-center justify-center">
                  <Check className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          </button>

          <button
            onClick={() => handleCompactModeChange(true)}
            className={`
              p-4 rounded-xl border-2 transition-all duration-200
              ${compactMode
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                : 'border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-gray-600'
              }
            `}
          >
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-xl bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center">
                <Minimize2 className="w-8 h-8 text-gray-600 dark:text-gray-400" />
              </div>
              <div className="text-center">
                <p className="font-medium text-gray-900 dark:text-white">Compact</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Espacement réduit</p>
              </div>
              {compactMode && (
                <div className="w-6 h-6 rounded-full bg-primary-500 flex items-center justify-center">
                  <Check className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          </button>
        </div>
      </div>

      {/* Sélection du thème */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Palette className="w-5 h-5" />
          Thème de couleurs
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.values(themes).map((theme) => (
            <button
              key={theme.id}
              onClick={() => handleThemeChange(theme.id)}
              className={`
                p-4 rounded-xl border-2 transition-all duration-200 text-left
                ${currentTheme === theme.id
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                  : 'border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-gray-600'
                }
              `}
            >
              <div className="flex flex-col gap-3">
                {/* Aperçu des couleurs */}
                <div className="flex gap-1">
                  <div
                    className="w-8 h-8 rounded-lg shadow-sm"
                    style={{ backgroundColor: theme.colors.primary[600] }}
                  />
                  <div
                    className="w-8 h-8 rounded-lg shadow-sm"
                    style={{ backgroundColor: theme.colors.primary[400] }}
                  />
                  <div
                    className="w-8 h-8 rounded-lg shadow-sm"
                    style={{ backgroundColor: theme.colors.accent }}
                  />
                </div>

                {/* Nom du thème */}
                <div>
                  <p className="font-medium text-gray-900 dark:text-white text-sm">
                    {theme.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {theme.description}
                  </p>
                </div>

                {/* Indicateur de sélection */}
                {currentTheme === theme.id && (
                  <div className="flex items-center gap-1 text-primary-600 dark:text-primary-400">
                    <Check className="w-4 h-4" />
                    <span className="text-xs font-medium">Actif</span>
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Aperçu du thème */}
      <div className="card p-6 mt-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Aperçu du thème
        </h2>
        <div className="space-y-4">
          {/* Boutons */}
          <div className="flex flex-wrap gap-2">
            <button className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors">
              Bouton Principal
            </button>
            <button className="px-4 py-2 bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 rounded-lg font-medium transition-colors">
              Bouton Secondaire
            </button>
            <button className="px-4 py-2 border border-primary-300 dark:border-primary-700 text-primary-600 dark:text-primary-400 rounded-lg font-medium transition-colors hover:bg-primary-50 dark:hover:bg-primary-900/30">
              Bouton Outline
            </button>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-2">
            <span className="px-3 py-1 bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 rounded-full text-sm font-medium">
              Badge Primary
            </span>
            <span className="px-3 py-1 bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 rounded-full text-sm font-medium">
              Succès
            </span>
            <span className="px-3 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 rounded-full text-sm font-medium">
              Attention
            </span>
            <span className="px-3 py-1 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 rounded-full text-sm font-medium">
              Erreur
            </span>
          </div>

          {/* Barre de progression */}
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
            <div
              className="bg-primary-600 h-3 rounded-full transition-all duration-500"
              style={{ width: '65%' }}
            />
          </div>

          {/* Cards d'exemple */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-primary-50 dark:bg-primary-900/30 rounded-lg border border-primary-200 dark:border-primary-800">
              <p className="text-2xl font-bold text-primary-600 dark:text-primary-400">1.5M</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Chiffre d'affaires</p>
            </div>
            <div className="p-4 bg-green-50 dark:bg-green-900/30 rounded-lg border border-green-200 dark:border-green-800">
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">+12%</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Croissance</p>
            </div>
            <div className="p-4 bg-amber-50 dark:bg-amber-900/30 rounded-lg border border-amber-200 dark:border-amber-800">
              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">85%</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Objectif</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
