/**
 * Watermark.jsx — Filigrane dynamique par utilisateur
 * =====================================================
 * - Canvas tuilé diagonal (non supprimable par CSS DevTools)
 * - Affiche : nom utilisateur + rôle + date/heure en temps réel
 * - pointer-events: none → n'interfère pas avec l'UI
 * - Actif aussi à l'impression (@media print)
 * - Se régénère chaque minute (date/heure à jour)
 * - Protégé contre la suppression DOM par MutationObserver
 */

import { useEffect, useRef, useCallback } from 'react'

// ── Génère le pattern canvas (une tuile 340×160) ──────────────────────────
function buildPattern(lines, darkMode) {
  const W = 340
  const H = 160
  const canvas = document.createElement('canvas')
  canvas.width  = W
  canvas.height = H
  const ctx = canvas.getContext('2d')

  // Fond transparent
  ctx.clearRect(0, 0, W, H)

  // Rotation diagonale
  ctx.save()
  ctx.translate(W / 2, H / 2)
  ctx.rotate(-Math.PI / 6)  // -30°

  // Style du texte
  const alpha   = darkMode ? 0.06 : 0.055
  const color   = darkMode ? `rgba(255,255,255,${alpha})` : `rgba(0,0,0,${alpha})`
  ctx.fillStyle = color
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'

  // Ligne principale (nom)
  ctx.font = 'bold 13px system-ui, sans-serif'
  ctx.fillText(lines[0] || '', 0, -14)

  // Ligne secondaire (rôle)
  ctx.font = '11px system-ui, sans-serif'
  ctx.fillStyle = darkMode ? `rgba(255,255,255,${alpha * 0.85})` : `rgba(0,0,0,${alpha * 0.85})`
  ctx.fillText(lines[1] || '', 0, 2)

  // Ligne tertiaire (date/heure)
  ctx.font = '10px system-ui, sans-serif'
  ctx.fillStyle = darkMode ? `rgba(255,255,255,${alpha * 0.7})` : `rgba(0,0,0,${alpha * 0.7})`
  ctx.fillText(lines[2] || '', 0, 16)

  ctx.restore()
  return canvas.toDataURL('image/png')
}

// ── Composant principal ────────────────────────────────────────────────────
export default function Watermark({ user, darkMode }) {
  const divRef      = useRef(null)
  const observerRef = useRef(null)
  const intervalRef = useRef(null)

  // Formate la date/heure locale
  const getDateTime = () =>
    new Date().toLocaleString('fr-MA', {
      day:    '2-digit',
      month:  '2-digit',
      year:   'numeric',
      hour:   '2-digit',
      minute: '2-digit',
    })

  // Formate le rôle
  const getRoleLabel = (role) => {
    const map = {
      superadmin:   'Super Admin',
      admin:        'Administrateur',
      admin_client: 'Admin Client',
      user:         'Utilisateur',
      editeur:      'Éditeur',
    }
    return map[role] || role || ''
  }

  // Construit les 3 lignes du filigrane
  const buildLines = useCallback(() => {
    if (!user) return []
    const nom  = [user.prenom, user.nom].filter(Boolean).join(' ') || user.username || ''
    const role = getRoleLabel(user.role_global || user.role_dwh || user.role || '')
    const dt   = getDateTime()
    return [nom, role, dt]
  }, [user])

  // Applique le filigrane sur le div
  const applyWatermark = useCallback(() => {
    const el = divRef.current
    if (!el) return
    const lines   = buildLines()
    if (!lines.length) return
    const dataUrl = buildPattern(lines, darkMode)
    el.style.backgroundImage  = `url(${dataUrl})`
    el.style.backgroundRepeat = 'repeat'
    el.style.backgroundSize   = '340px 160px'
  }, [buildLines, darkMode])

  // Réinjecte le div si supprimé du DOM (anti-tamper)
  const ensurePresent = useCallback(() => {
    const container = document.getElementById('__wm_container__')
    if (!container) return
    if (!container.contains(divRef.current)) {
      container.appendChild(divRef.current)
      applyWatermark()
    }
  }, [applyWatermark])

  useEffect(() => {
    if (!user) return

    // Créer le div overlay permanent
    const div = document.createElement('div')
    div.setAttribute('aria-hidden', 'true')
    Object.assign(div.style, {
      position:      'fixed',
      inset:         '0',
      width:         '100vw',
      height:        '100vh',
      pointerEvents: 'none',
      zIndex:        '99999',
      userSelect:    'none',
      WebkitUserSelect: 'none',
    })
    divRef.current = div

    // Conteneur racine (attaché au body pour résister aux re-renders React)
    let container = document.getElementById('__wm_container__')
    if (!container) {
      container = document.createElement('div')
      container.id = '__wm_container__'
      Object.assign(container.style, {
        position:      'fixed',
        inset:         '0',
        pointerEvents: 'none',
        zIndex:        '99999',
        overflow:      'hidden',
      })
      document.body.appendChild(container)
    }
    container.appendChild(div)

    // Premier rendu
    applyWatermark()

    // Mise à jour chaque minute (date/heure)
    intervalRef.current = setInterval(applyWatermark, 60_000)

    // MutationObserver : réinjecte si le div est supprimé
    observerRef.current = new MutationObserver(ensurePresent)
    observerRef.current.observe(container, { childList: true, subtree: false })
    observerRef.current.observe(document.body, { childList: true, subtree: false })

    // Bloquer Ctrl+P (impression navigateur)
    const blockPrint = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        e.preventDefault()
        e.stopPropagation()
      }
    }
    window.addEventListener('keydown', blockPrint, { capture: true })

    return () => {
      clearInterval(intervalRef.current)
      observerRef.current?.disconnect()
      window.removeEventListener('keydown', blockPrint, { capture: true })
      // Garder le container mais nettoyer le div de cette instance
      if (div.parentNode) div.parentNode.removeChild(div)
      // Supprimer le container si vide
      if (container && container.children.length === 0) {
        container.remove()
      }
    }
  }, [user?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  // Re-rendre si darkMode change
  useEffect(() => {
    applyWatermark()
  }, [darkMode, applyWatermark])

  return null  // Pas de JSX — tout est dans le DOM impératif
}
