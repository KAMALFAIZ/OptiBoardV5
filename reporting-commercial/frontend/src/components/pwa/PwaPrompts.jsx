import { useState, useEffect } from 'react'
import { X, Download, Share, RefreshCw, PlusSquare } from 'lucide-react'
import { promptInstall, getDeferredInstallPrompt, isStandalone, isIOS } from '../../pwa/registerSW'

const DISMISS_KEY = 'pwa_install_dismissed_at'
const DISMISS_DAYS = 14

function isDismissed() {
  try {
    const ts = parseInt(localStorage.getItem(DISMISS_KEY) || '0', 10)
    return ts && Date.now() - ts < DISMISS_DAYS * 24 * 60 * 60 * 1000
  } catch (_) {
    return false
  }
}

function dismiss() {
  try { localStorage.setItem(DISMISS_KEY, String(Date.now())) } catch (_) { /* ignore */ }
}

/** Banniere d'installation : bouton natif (Android/Chrome) ou guide (iOS Safari). */
function InstallPrompt() {
  const [mode, setMode] = useState(null) // null | 'native' | 'ios'
  const [showIosGuide, setShowIosGuide] = useState(false)

  useEffect(() => {
    if (isStandalone() || isDismissed()) return

    if (getDeferredInstallPrompt()) setMode('native')

    const onAvailable = () => setMode('native')
    const onInstalled = () => setMode(null)
    window.addEventListener('pwa:install-available', onAvailable)
    window.addEventListener('pwa:installed', onInstalled)

    // iOS : pas de beforeinstallprompt — proposer le guide apres un court delai
    let iosTimer = null
    if (isIOS()) {
      iosTimer = setTimeout(() => setMode((m) => m || 'ios'), 4000)
    }

    return () => {
      window.removeEventListener('pwa:install-available', onAvailable)
      window.removeEventListener('pwa:installed', onInstalled)
      if (iosTimer) clearTimeout(iosTimer)
    }
  }, [])

  if (!mode) return null

  const close = () => { dismiss(); setMode(null); setShowIosGuide(false) }

  const handleInstall = async () => {
    if (mode === 'native') {
      const outcome = await promptInstall()
      if (outcome !== null) setMode(null)
      if (outcome === 'dismissed') dismiss()
    } else {
      setShowIosGuide(true)
    }
  }

  return (
    <>
      <div className="fixed bottom-0 inset-x-0 z-[70] p-3 safe-area-pb pointer-events-none">
        <div className="pointer-events-auto max-w-md mx-auto flex items-center gap-3 rounded-2xl bg-white dark:bg-gray-800 shadow-2xl border border-gray-200 dark:border-gray-700 p-3">
          <img src="/icons/icon-192.png" alt="" className="w-10 h-10 rounded-xl shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">Installer OptiBoard</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">Accès rapide depuis votre écran d'accueil</p>
          </div>
          <button
            onClick={handleInstall}
            className="shrink-0 flex items-center gap-1.5 bg-primary-600 hover:bg-primary-700 text-white text-sm font-semibold px-3.5 py-2 rounded-xl"
          >
            <Download className="w-4 h-4" />
            Installer
          </button>
          <button onClick={close} aria-label="Fermer" className="shrink-0 p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {showIosGuide && (
        <div className="fixed inset-0 z-[80] flex items-end justify-center bg-black/50" onClick={close}>
          <div
            className="w-full max-w-md bg-white dark:bg-gray-800 rounded-t-3xl p-6 safe-area-pb"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-gray-900 dark:text-white">Installer sur iPhone / iPad</h3>
              <button onClick={close} aria-label="Fermer" className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                <X className="w-5 h-5" />
              </button>
            </div>
            <ol className="space-y-4 text-sm text-gray-700 dark:text-gray-300">
              <li className="flex items-center gap-3">
                <span className="w-7 h-7 shrink-0 rounded-full bg-primary-600 text-white text-xs font-bold flex items-center justify-center">1</span>
                <span className="flex items-center gap-1.5 flex-wrap">
                  Dans Safari, touchez le bouton
                  <Share className="w-4 h-4 inline text-primary-600" />
                  <strong>Partager</strong>
                </span>
              </li>
              <li className="flex items-center gap-3">
                <span className="w-7 h-7 shrink-0 rounded-full bg-primary-600 text-white text-xs font-bold flex items-center justify-center">2</span>
                <span className="flex items-center gap-1.5 flex-wrap">
                  Choisissez
                  <PlusSquare className="w-4 h-4 inline text-primary-600" />
                  <strong>Sur l'écran d'accueil</strong>
                </span>
              </li>
              <li className="flex items-center gap-3">
                <span className="w-7 h-7 shrink-0 rounded-full bg-primary-600 text-white text-xs font-bold flex items-center justify-center">3</span>
                <span>Touchez <strong>Ajouter</strong> — OptiBoard apparaît comme une app</span>
              </li>
            </ol>
          </div>
        </div>
      )}
    </>
  )
}

/** Toast "nouvelle version disponible" — applique la MAJ du service worker. */
function UpdateToast() {
  const [applyFn, setApplyFn] = useState(null)
  const [updating, setUpdating] = useState(false)

  useEffect(() => {
    const onUpdate = (e) => setApplyFn(() => e.detail.apply)
    window.addEventListener('pwa:update-available', onUpdate)
    return () => window.removeEventListener('pwa:update-available', onUpdate)
  }, [])

  if (!applyFn) return null

  return (
    <div className="fixed top-3 inset-x-0 z-[70] px-3 safe-area-pt pointer-events-none">
      <div className="pointer-events-auto max-w-md mx-auto flex items-center gap-3 rounded-2xl bg-gray-900 dark:bg-gray-700 text-white shadow-2xl p-3">
        <RefreshCw className={`w-5 h-5 shrink-0 text-primary-300 ${updating ? 'animate-spin' : ''}`} />
        <p className="flex-1 text-sm font-medium">Nouvelle version disponible</p>
        <button
          onClick={() => { setUpdating(true); applyFn() }}
          disabled={updating}
          className="shrink-0 bg-white text-gray-900 text-sm font-semibold px-3.5 py-1.5 rounded-xl disabled:opacity-60"
        >
          {updating ? 'Mise à jour…' : 'Actualiser'}
        </button>
      </div>
    </div>
  )
}

export default function PwaPrompts() {
  return (
    <>
      <InstallPrompt />
      <UpdateToast />
    </>
  )
}
