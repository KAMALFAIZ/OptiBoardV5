import { useEffect, useRef } from 'react'
import { useToast } from './Toast'

// Fenêtre de déduplication : un même message d'erreur n'est pas réaffiché
// s'il survient dans les 3 secondes suivant le précédent.
const DEDUP_WINDOW_MS = 3000

/**
 * Pont entre l'intercepteur axios (src/services/api.js) et le système Toast.
 *
 * L'intercepteur dispatch un CustomEvent `api:error` ({ status, message, url })
 * pour toute erreur HTTP sur méthode mutante (post/put/delete/patch),
 * hors 401, requêtes annulées et requêtes marquées `skipErrorToast: true`.
 *
 * Ce composant (monté dans App.jsx, sous ToastProvider) écoute l'event
 * et affiche un toast d'erreur, avec déduplication par message.
 * Il ne rend rien.
 */
export default function ApiErrorBridge() {
  const toast = useToast()
  const recentRef = useRef(new Map()) // message -> timestamp du dernier affichage

  useEffect(() => {
    const handler = (event) => {
      const message = event?.detail?.message
      if (!message) return

      const now = Date.now()
      const recent = recentRef.current

      // Purge des entrées sorties de la fenêtre de déduplication
      for (const [msg, ts] of recent) {
        if (now - ts >= DEDUP_WINDOW_MS) recent.delete(msg)
      }

      // Même message dans les 3 dernières secondes -> on ne réaffiche pas
      if (recent.has(message)) return
      recent.set(message, now)

      toast.error(message)
    }

    window.addEventListener('api:error', handler)
    return () => window.removeEventListener('api:error', handler)
  }, [toast])

  return null
}
