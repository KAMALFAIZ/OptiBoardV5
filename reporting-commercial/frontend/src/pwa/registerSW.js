/*
 * Enregistrement du service worker + plomberie PWA.
 *
 * Evenements custom emis sur window (consommes par PwaPrompts.jsx) :
 *  - 'pwa:update-available'  { detail: { apply } } : nouvelle version prete
 *  - 'pwa:install-available'                        : install native possible (Android/Chrome)
 *  - 'pwa:installed'                                : l'app vient d'etre installee
 */

// Prompt d'installation differe (beforeinstallprompt — Chrome/Edge/Android)
let deferredInstallPrompt = null

export function getDeferredInstallPrompt() {
  return deferredInstallPrompt
}

export async function promptInstall() {
  if (!deferredInstallPrompt) return null
  deferredInstallPrompt.prompt()
  const choice = await deferredInstallPrompt.userChoice
  deferredInstallPrompt = null
  return choice?.outcome || null
}

/** True si l'app tourne deja en mode installe (standalone). */
export function isStandalone() {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true // iOS Safari
  )
}

/** True sur iOS/iPadOS (ou l'install passe par "Partager > Sur l'ecran d'accueil"). */
export function isIOS() {
  const ua = window.navigator.userAgent
  const iPadOS = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1
  return /iPad|iPhone|iPod/.test(ua) || iPadOS
}

export function setupPwa() {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    deferredInstallPrompt = e
    window.dispatchEvent(new CustomEvent('pwa:install-available'))
  })

  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null
    window.dispatchEvent(new CustomEvent('pwa:installed'))
  })

  if (!('serviceWorker' in navigator)) return
  // Pas de SW en dev : il court-circuiterait le HMR de Vite
  if (!import.meta.env.PROD) return

  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js')

      const notifyUpdate = (worker) => {
        const apply = () => {
          worker.postMessage({ type: 'SKIP_WAITING' })
        }
        window.dispatchEvent(new CustomEvent('pwa:update-available', { detail: { apply } }))
      }

      // Un SW etait deja en attente avant ce chargement de page
      if (registration.waiting && navigator.serviceWorker.controller) {
        notifyUpdate(registration.waiting)
      }

      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing
        if (!newWorker) return
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            notifyUpdate(newWorker)
          }
        })
      })

      // Quand le nouveau SW prend le controle -> recharger pour servir la nouvelle version
      let reloaded = false
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (reloaded) return
        reloaded = true
        window.location.reload()
      })

      // Verification periodique des mises a jour (utile en mode standalone,
      // ou l'app peut rester ouverte des jours sans navigation)
      setInterval(() => {
        registration.update().catch(() => {})
      }, 60 * 60 * 1000)
    } catch (err) {
      console.warn('Enregistrement du service worker impossible:', err)
    }
  })
}
