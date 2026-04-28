/**
 * Tests de cohérence des calculs frontend - OptiBoard
 * Vérifie les fonctions utilitaires de calcul et formatage côté client.
 */
import { describe, it, expect } from 'vitest'

// ─────────────────────────────────────────────
// Fonctions utilitaires — reprises du code métier frontend
// (isolées ici pour être testées sans dépendances React)
// ─────────────────────────────────────────────

/** Formate un montant en MAD avec séparateurs */
function formatMontant(value, devise = 'MAD') {
  if (value === null || value === undefined) return `0.00 ${devise}`
  return `${Number(value).toLocaleString('fr-MA', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} ${devise}`
}

/** Calcule l'évolution % entre deux valeurs */
function calcEvolution(actuel, precedent) {
  if (!precedent || precedent === 0) return 0
  return ((actuel - precedent) / precedent) * 100
}

/** Calcule le DSO (Days Sales Outstanding) */
function calcDSO(encours, caTTC, nbJours = 365) {
  if (!caTTC || caTTC === 0) return 0
  return (encours / caTTC) * nbJours
}

/** Calcule la marge brute */
function calcMarge(caHT, cout) {
  return caHT - cout
}

/** Calcule le taux de marge */
function calcTauxMarge(caHT, cout) {
  if (!caHT || caHT === 0) return 0
  return ((caHT - cout) / caHT) * 100
}

/** Formate une date pour l'API (YYYY-MM-DD) */
function formatDateAPI(date) {
  if (!date) return null
  if (typeof date === 'string') return date
  const d = new Date(date)
  return d.toISOString().split('T')[0]
}

/** Retourne la plage de dates pour une période prédéfinie */
function getPeriodeDates(periode) {
  const today = new Date()
  const year = today.getFullYear()
  const todayStr = today.toISOString().split('T')[0]

  switch (periode) {
    case 'annee_courante':
      return { debut: `${year}-01-01`, fin: todayStr }
    case 'annee_precedente':
      return { debut: `${year - 1}-01-01`, fin: `${year - 1}-12-31` }
    case 'mois_courant': {
      const m = String(today.getMonth() + 1).padStart(2, '0')
      return { debut: `${year}-${m}-01`, fin: todayStr }
    }
    case '12_derniers_mois': {
      const d = new Date(today)
      d.setFullYear(d.getFullYear() - 1)
      return { debut: d.toISOString().split('T')[0], fin: todayStr }
    }
    default:
      return { debut: `${year}-01-01`, fin: todayStr }
  }
}

/** Extrait un message d'erreur depuis une réponse Axios */
function extractErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    'Erreur inconnue'
  )
}

// ═══════════════════════════════════════════════════════════════════
// 1. formatMontant
// ═══════════════════════════════════════════════════════════════════
describe('formatMontant', () => {
  it('retourne 0.00 MAD pour null', () => {
    expect(formatMontant(null)).toContain('0.00')
    expect(formatMontant(null)).toContain('MAD')
  })

  it('retourne 0.00 MAD pour undefined', () => {
    expect(formatMontant(undefined)).toContain('0.00')
  })

  it('formate un nombre positif', () => {
    const result = formatMontant(1000)
    expect(result).toContain('MAD')
    expect(result).toMatch(/1/)
  })

  it('supporte une devise personnalisée', () => {
    const result = formatMontant(500, 'EUR')
    expect(result).toContain('EUR')
  })

  it('formate zéro correctement', () => {
    const result = formatMontant(0)
    // Accepte '0.00 MAD' (en) ou '0,00 MAD' (fr) selon la locale jsdom
    expect(result).toMatch(/0[.,]00/)
    expect(result).toContain('MAD')
  })
})

// ═══════════════════════════════════════════════════════════════════
// 2. calcEvolution
// ═══════════════════════════════════════════════════════════════════
describe('calcEvolution', () => {
  it('hausse de 20%', () => {
    expect(calcEvolution(1_200_000, 1_000_000)).toBeCloseTo(20.0)
  })

  it('baisse de 20%', () => {
    expect(calcEvolution(800_000, 1_000_000)).toBeCloseTo(-20.0)
  })

  it('stable à 0%', () => {
    expect(calcEvolution(1_000_000, 1_000_000)).toBeCloseTo(0.0)
  })

  it('retourne 0 si précédent = 0', () => {
    expect(calcEvolution(500_000, 0)).toBe(0)
  })

  it('retourne 0 si précédent = null', () => {
    expect(calcEvolution(500_000, null)).toBe(0)
  })

  it('hausse de 50%', () => {
    expect(calcEvolution(750_000, 500_000)).toBeCloseTo(50.0)
  })
})

// ═══════════════════════════════════════════════════════════════════
// 3. calcDSO
// ═══════════════════════════════════════════════════════════════════
describe('calcDSO', () => {
  it('DSO correct avec valeurs réelles', () => {
    // Encours = CA_TTC * 30/365 → DSO ≈ 30 jours
    const caTTC = 1_200_000
    const encours = caTTC * 30 / 365
    expect(calcDSO(encours, caTTC)).toBeCloseTo(30, 0)
  })

  it('retourne 0 si CA TTC = 0', () => {
    expect(calcDSO(50_000, 0)).toBe(0)
  })

  it('retourne 0 si encours = 0', () => {
    expect(calcDSO(0, 1_000_000)).toBeCloseTo(0)
  })

  it('supporte nb_jours personnalisé', () => {
    const result = calcDSO(100_000, 1_200_000, 30)
    expect(result).toBeCloseTo((100_000 / 1_200_000) * 30)
  })

  it('cohérence : DSO × CA_TTC = Encours × 365', () => {
    const caTTC = 800_000
    const encours = 120_000
    const dso = calcDSO(encours, caTTC)
    expect(dso * caTTC).toBeCloseTo(encours * 365, 0)
  })
})

// ═══════════════════════════════════════════════════════════════════
// 4. calcMarge & calcTauxMarge
// ═══════════════════════════════════════════════════════════════════
describe('calcMarge', () => {
  it('marge brute = CA - Coût', () => {
    expect(calcMarge(1_000_000, 700_000)).toBe(300_000)
  })

  it('marge négative si coût > CA', () => {
    expect(calcMarge(500_000, 600_000)).toBe(-100_000)
  })

  it('marge nulle si CA = Coût', () => {
    expect(calcMarge(500_000, 500_000)).toBe(0)
  })
})

describe('calcTauxMarge', () => {
  it('taux marge de 30%', () => {
    expect(calcTauxMarge(1_000_000, 700_000)).toBeCloseTo(30.0)
  })

  it('retourne 0 si CA = 0', () => {
    expect(calcTauxMarge(0, 0)).toBe(0)
  })

  it('cohérence taux avec marge', () => {
    const caHT = 850_000
    const cout = 612_000
    const marge = calcMarge(caHT, cout)
    const taux = calcTauxMarge(caHT, cout)
    expect(taux).toBeCloseTo((marge / caHT) * 100)
  })

  it('marge + coût = CA', () => {
    const caHT = 500_000
    const cout = 350_000
    const marge = calcMarge(caHT, cout)
    expect(marge + cout).toBe(caHT)
  })
})

// ═══════════════════════════════════════════════════════════════════
// 5. formatDateAPI
// ═══════════════════════════════════════════════════════════════════
describe('formatDateAPI', () => {
  it('retourne null pour null', () => {
    expect(formatDateAPI(null)).toBeNull()
  })

  it('retourne la chaîne telle quelle si déjà au format YYYY-MM-DD', () => {
    expect(formatDateAPI('2025-01-15')).toBe('2025-01-15')
  })

  it('convertit un objet Date en YYYY-MM-DD', () => {
    const d = new Date('2025-04-15')
    const result = formatDateAPI(d)
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(result.startsWith('2025')).toBe(true)
  })

  it('format toujours YYYY-MM-DD', () => {
    const result = formatDateAPI('2025-03-05')
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})

// ═══════════════════════════════════════════════════════════════════
// 6. getPeriodeDates
// ═══════════════════════════════════════════════════════════════════
describe('getPeriodeDates', () => {
  it('annee_courante commence le 1er janvier', () => {
    const { debut } = getPeriodeDates('annee_courante')
    expect(debut).toMatch(/^\d{4}-01-01$/)
    expect(debut.startsWith(String(new Date().getFullYear()))).toBe(true)
  })

  it('annee_courante fin <= aujourd\'hui', () => {
    const { fin } = getPeriodeDates('annee_courante')
    const today = new Date().toISOString().split('T')[0]
    expect(fin <= today).toBe(true)
  })

  it('annee_precedente dans l\'année précédente', () => {
    const { debut, fin } = getPeriodeDates('annee_precedente')
    const prevYear = String(new Date().getFullYear() - 1)
    expect(debut.startsWith(prevYear)).toBe(true)
    expect(fin.startsWith(prevYear)).toBe(true)
  })

  it('mois_courant commence le 1er du mois', () => {
    const { debut } = getPeriodeDates('mois_courant')
    expect(debut).toMatch(/-01$/)
  })

  it('debut toujours <= fin pour toutes les périodes', () => {
    const periodes = ['annee_courante', 'annee_precedente', 'mois_courant', '12_derniers_mois']
    periodes.forEach(p => {
      const { debut, fin } = getPeriodeDates(p)
      expect(debut <= fin).toBe(true)
    })
  })

  it('fallback sur annee_courante pour période inconnue', () => {
    const { debut } = getPeriodeDates('periode_inconnue_xyz')
    expect(debut.startsWith(String(new Date().getFullYear()))).toBe(true)
  })
})

// ═══════════════════════════════════════════════════════════════════
// 7. extractErrorMessage
// ═══════════════════════════════════════════════════════════════════
describe('extractErrorMessage', () => {
  it('extrait detail de response.data', () => {
    const error = { response: { data: { detail: 'Accès refusé' } } }
    expect(extractErrorMessage(error)).toBe('Accès refusé')
  })

  it('extrait message de response.data', () => {
    const error = { response: { data: { message: 'Serveur indisponible' } } }
    expect(extractErrorMessage(error)).toBe('Serveur indisponible')
  })

  it('extrait message de error.message', () => {
    const error = { message: 'Network Error' }
    expect(extractErrorMessage(error)).toBe('Network Error')
  })

  it('retourne erreur inconnue si rien', () => {
    expect(extractErrorMessage({})).toBe('Erreur inconnue')
  })

  it('priorité à detail sur message', () => {
    const error = {
      response: { data: { detail: 'Detail', message: 'Message' } }
    }
    expect(extractErrorMessage(error)).toBe('Detail')
  })
})

// ═══════════════════════════════════════════════════════════════════
// 8. Tests de cohérence croisée frontend
// ═══════════════════════════════════════════════════════════════════
describe('Cohérence croisée des calculs', () => {
  it('marge + DSO cohérents avec les mêmes données', () => {
    const caHT = 1_000_000
    const caTTC = caHT * 1.2
    const cout = 700_000
    const encours = 100_000

    const marge = calcMarge(caHT, cout)
    const taux = calcTauxMarge(caHT, cout)
    const dso = calcDSO(encours, caTTC)

    // Vérifications de base
    expect(marge).toBe(300_000)
    expect(taux).toBeCloseTo(30.0)
    expect(dso).toBeCloseTo((100_000 / 1_200_000) * 365, 0)

    // La marge ne doit pas impacter le DSO
    expect(dso).toBeGreaterThan(0)
    expect(marge).toBeGreaterThan(0)
  })

  it('évolution positive implique valeur actuelle > précédente', () => {
    const actuel = 1_500_000
    const precedent = 1_200_000
    const evol = calcEvolution(actuel, precedent)

    expect(evol).toBeGreaterThan(0)
    expect(actuel).toBeGreaterThan(precedent)
  })

  it('évolution négative implique valeur actuelle < précédente', () => {
    const actuel = 900_000
    const precedent = 1_000_000
    const evol = calcEvolution(actuel, precedent)

    expect(evol).toBeLessThan(0)
    expect(actuel).toBeLessThan(precedent)
  })

  it('somme mensuelle cohérente avec total annuel', () => {
    const moisData = [
      { ca: 100_000 }, { ca: 110_000 }, { ca: 120_000 },
      { ca: 130_000 }, { ca: 140_000 }, { ca: 150_000 },
    ]
    const total = moisData.reduce((sum, m) => sum + m.ca, 0)
    expect(total).toBe(750_000)

    // L'évolution sur la période complète doit se baser sur ce total
    const caAnneePrec = 700_000
    const evol = calcEvolution(total, caAnneePrec)
    expect(evol).toBeCloseTo((750_000 - 700_000) / 700_000 * 100)
  })
})
