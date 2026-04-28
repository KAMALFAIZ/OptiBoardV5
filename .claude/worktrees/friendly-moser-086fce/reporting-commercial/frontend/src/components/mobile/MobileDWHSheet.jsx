import { useState } from 'react'
import { X, Database, Check, Loader2 } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useDWH } from '../../context/DWHContext'

export default function MobileDWHSheet({ open, onClose }) {
  const { user } = useAuth()
  const { currentDWH, dwhList, switchDWH, loading } = useDWH()
  const [switching, setSwitching] = useState(null)

  const handleSwitch = async (code) => {
    if (code === currentDWH?.code || switching) return
    setSwitching(code)
    try {
      await switchDWH(user.id, code)
      onClose()
    } finally {
      setSwitching(null)
    }
  }

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      )}
      <div
        className={`fixed left-0 right-0 bottom-0 z-50 bg-white dark:bg-gray-800 rounded-t-2xl shadow-2xl transition-transform duration-300 ease-out`}
        style={{ transform: open ? 'translateY(0)' : 'translateY(100%)' }}
      >
        {/* Handle */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full bg-gray-300 dark:bg-gray-600" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-primary-500" />
            <span className="font-semibold text-gray-900 dark:text-white text-sm">Changer de base</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Liste DWH */}
        <div className="px-4 py-2 max-h-72 overflow-y-auto">
          {dwhList.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">Aucune base disponible</p>
          ) : (
            dwhList.map(dwh => {
              const isActive = dwh.code === currentDWH?.code
              const isLoading = switching === dwh.code
              return (
                <button
                  key={dwh.code}
                  onClick={() => handleSwitch(dwh.code)}
                  disabled={!!switching}
                  className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl mb-1.5 transition-colors text-left
                    ${isActive
                      ? 'bg-primary-50 dark:bg-primary-900/20'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 active:bg-gray-100'
                    }`}
                >
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0
                    ${isActive ? 'bg-primary-100 dark:bg-primary-800/40' : 'bg-gray-100 dark:bg-gray-700'}`}>
                    <Database className={`w-4 h-4 ${isActive ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400'}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-semibold truncate ${isActive ? 'text-primary-700 dark:text-primary-300' : 'text-gray-900 dark:text-white'}`}>
                      {dwh.nom}
                    </p>
                    <p className="text-xs text-gray-400 truncate">{dwh.code}</p>
                  </div>
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 text-primary-500 animate-spin flex-shrink-0" />
                  ) : isActive ? (
                    <Check className="w-4 h-4 text-primary-600 dark:text-primary-400 flex-shrink-0" />
                  ) : null}
                </button>
              )
            })
          )}
        </div>
        <div className="safe-area-pb pb-4" />
      </div>
    </>
  )
}
