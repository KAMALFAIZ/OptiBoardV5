/**
 * LicenseBanner — Bannière d'avertissement licence
 * Affiche un bandeau coloré selon l'état de la licence :
 *  - Orange : expiration dans moins de 30 jours
 *  - Rouge   : mode grâce (serveur injoignable)
 *  - Amber  : mode limité (TOP 100 lignes actif)
 */
import { useState } from 'react'
import { AlertTriangle, Clock, Shield, X, ChevronRight } from 'lucide-react'
import { useLicense } from '../../context/LicenseContext'

export default function LicenseBanner() {
  const { isExpiringSoon, isGraceMode, isLimitedMode, license } = useLicense()
  const [dismissed, setDismissed] = useState({})

  const dismiss = (key) => setDismissed(d => ({ ...d, [key]: true }))

  const banners = []

  // Expiration imminente
  if (isExpiringSoon && !dismissed['expiring']) {
    banners.push({
      key: 'expiring',
      bg: 'bg-orange-500',
      icon: <Clock className="w-4 h-4 flex-shrink-0" />,
      text: `Votre licence expire dans ${license?.days_remaining} jour${license?.days_remaining > 1 ? 's' : ''}. Contactez votre fournisseur pour le renouvellement.`,
      dismissible: true,
    })
  }

  // Mode grâce
  if (isGraceMode && !dismissed['grace']) {
    banners.push({
      key: 'grace',
      bg: 'bg-red-600',
      icon: <AlertTriangle className="w-4 h-4 flex-shrink-0" />,
      text: `Mode grâce actif — Serveur de licences injoignable. ${license?.grace_days_remaining ?? '?'} jour(s) restant(s) avant blocage.`,
      dismissible: false,
    })
  }

  // Mode limité (TOP 100)
  if (isLimitedMode && !dismissed['limited']) {
    banners.push({
      key: 'limited',
      bg: 'bg-amber-500',
      icon: <Shield className="w-4 h-4 flex-shrink-0" />,
      text: 'Mode limité — Les résultats sont restreints à 100 lignes. Passez à un plan supérieur pour lever cette limitation.',
      dismissible: true,
      action: null,
    })
  }

  if (banners.length === 0) return null

  return (
    <div className="flex flex-col">
      {banners.map(banner => (
        <div
          key={banner.key}
          className={`${banner.bg} text-white text-sm py-2 px-4 flex items-center justify-center gap-2 relative`}
        >
          {banner.icon}
          <span className="text-center leading-snug">{banner.text}</span>
          {banner.dismissible && (
            <button
              onClick={() => dismiss(banner.key)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-white/20 rounded transition-colors"
              title="Fermer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
