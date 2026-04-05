import { useState, useEffect } from 'react'

// ─── Icons (inline SVG pour zero dépendances) ───────────────────────────────
const Icon = ({ path, className = 'w-6 h-6' }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
    <path strokeLinecap="round" strokeLinejoin="round" d={path} />
  </svg>
)
const ICONS = {
  chart:    'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  bell:     'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9',
  cube:     'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
  document: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  desktop:  'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  globe:    'M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9',
  mobile:   'M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z',
  support:  'M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z',
  sage:     'M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4',
  check:    'M5 13l4 4L19 7',
  star:     'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z',
  ai:       'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
  shield:   'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
  rocket:   'M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z',
  phone:    'M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 7V5z',
  mail:     'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  location: 'M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z',
  menu:     'M4 6h16M4 12h16M4 18h16',
  close:    'M6 18L18 6M6 6l12 12',
  arrow:    'M17 8l4 4m0 0l-4 4m4-4H3',
  users:    'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
  clock:    'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  linkedin: 'M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z M4 6a2 2 0 100-4 2 2 0 000 4z',
}

// ─── Logo KAsoft (Hexagone Bicolore — Variante B) ────────────────────────────
// Coordonnées fixes identiques au modèle choisi (viewBox 215×60)
// Hexagone pointu : points="30,4 52,16 52,44 30,56 8,44 8,16"
// Moitié droite   : points="30,4 52,16 52,44 30,56"
function KasoftLogo({ dark = false, size = 'md' }) {
  const cfg = {
    sm: { w: 120, h: 34 },
    md: { w: 160, h: 45 },
    lg: { w: 215, h: 60 },
  }
  const { w, h } = cfg[size]
  const textColor = dark ? '#0f172a' : 'white'
  const softColor = dark ? '#2563eb' : '#bfdbfe'

  return (
    <svg width={w} height={h} viewBox="0 0 215 60" fill="none">
      {/* Hexagone entier — bleu foncé */}
      <polygon points="30,4 52,16 52,44 30,56 8,44 8,16" fill="#1e3a8a" />
      {/* Moitié droite — bleu vif */}
      <polygon points="30,4 52,16 52,44 30,56" fill="#2563eb" />
      {/* Ligne de séparation subtile */}
      <line x1="30" y1="4" x2="30" y2="56" stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
      {/* KA centré dans l'hexagone */}
      <text
        x="30" y="36"
        fontFamily="system-ui,-apple-system,sans-serif"
        fontWeight="900" fontSize="16"
        fill="white" textAnchor="middle">KA</text>
      {/* Wordmark */}
      <text
        x="64" y="38"
        fontFamily="system-ui,-apple-system,sans-serif"
        fontWeight="900" fontSize="28"
        fill={textColor}>
        KA<tspan fill={softColor}>soft</tspan>
      </text>
    </svg>
  )
}

// ─── Navbar ──────────────────────────────────────────────────────────────────
function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const links = [
    { label: 'Produits', href: '#produits' },
    { label: 'Services', href: '#services' },
    { label: 'À propos', href: '#pourquoi' },
    { label: 'Contact', href: '#contact' },
  ]

  return (
    <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${scrolled ? 'bg-white/95 backdrop-blur shadow-sm' : 'bg-transparent'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <a href="#" className="flex items-center">
            <KasoftLogo dark={scrolled} size="md" />
          </a>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-8">
            {links.map(l => (
              <a key={l.href} href={l.href} className="text-gray-600 hover:text-primary-800 font-medium transition-colors">
                {l.label}
              </a>
            ))}
          </div>

          {/* CTA */}
          <div className="hidden md:flex items-center gap-3">
            <a href="#contact" className="btn-primary text-sm py-2 px-5">
              Demander une démo
              <Icon path={ICONS.arrow} className="w-4 h-4" />
            </a>
          </div>

          {/* Mobile menu btn */}
          <button onClick={() => setMenuOpen(!menuOpen)} className="md:hidden p-2 rounded-lg hover:bg-gray-100">
            <Icon path={menuOpen ? ICONS.close : ICONS.menu} className="w-6 h-6 text-gray-700" />
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden bg-white border-t border-gray-100 px-4 pb-4 pt-2 shadow-lg">
          {links.map(l => (
            <a key={l.href} href={l.href} onClick={() => setMenuOpen(false)}
              className="block py-3 text-gray-700 font-medium border-b border-gray-50 last:border-0">
              {l.label}
            </a>
          ))}
          <a href="#contact" onClick={() => setMenuOpen(false)} className="btn-primary mt-4 w-full justify-center text-sm">
            Demander une démo
          </a>
        </div>
      )}
    </nav>
  )
}

// ─── Hero ─────────────────────────────────────────────────────────────────────
function Hero() {
  return (
    <section className="relative bg-gradient-to-br from-primary-900 via-primary-800 to-primary-700 text-white overflow-hidden pt-24 pb-20 md:pt-32 md:pb-28">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-10">
        <svg width="100%" height="100%">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="1"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Blob décoratif */}
      <div className="absolute -top-32 -right-32 w-96 h-96 bg-blue-400 rounded-full opacity-10 blur-3xl" />
      <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-blue-300 rounded-full opacity-10 blur-3xl" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Texte */}
          <div>
            <div className="inline-flex items-center gap-2 bg-white/10 border border-white/20 rounded-full px-4 py-1.5 text-sm font-medium mb-6">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              Revendeur Sage certifié · Casablanca, Maroc
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold leading-tight mb-6">
              La manière
              <span className="block text-blue-300">intelligente</span>
              de piloter votre entreprise
            </h1>
            <p className="text-lg md:text-xl text-blue-100 mb-8 leading-relaxed">
              Solutions BI, ERP et développement logiciel sur mesure pour les PME industrielles et de distribution au Maroc — avec intégration Sage native.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <a href="#contact" className="inline-flex items-center justify-center gap-2 bg-white text-primary-800 px-7 py-3.5 rounded-xl font-bold hover:bg-blue-50 transition-all shadow-lg hover:shadow-xl">
                Demander une démo gratuite
                <Icon path={ICONS.arrow} className="w-5 h-5" />
              </a>
              <a href="#produits" className="inline-flex items-center justify-center gap-2 border-2 border-white/40 text-white px-7 py-3.5 rounded-xl font-semibold hover:bg-white/10 transition-all">
                Découvrir nos produits
              </a>
            </div>
            {/* Badges */}
            <div className="flex flex-wrap gap-4 mt-10">
              {['100+ clients satisfaits', 'Sage certifié', 'Support Maroc'].map(b => (
                <div key={b} className="flex items-center gap-2 text-sm text-blue-200">
                  <Icon path={ICONS.check} className="w-4 h-4 text-green-400" />
                  {b}
                </div>
              ))}
            </div>
          </div>

          {/* Dashboard mockup */}
          <div className="hidden lg:block">
            <div className="relative bg-white/10 backdrop-blur border border-white/20 rounded-2xl p-6 shadow-2xl">
              {/* Barre titre mockup */}
              <div className="flex items-center gap-2 mb-5">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <div className="w-3 h-3 rounded-full bg-yellow-400" />
                <div className="w-3 h-3 rounded-full bg-green-400" />
                <span className="ml-3 text-xs text-blue-200 font-mono">OptiBoard v5 — Tableau de bord</span>
              </div>

              {/* KPI cards mockup */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                {[
                  { label: 'CA Mensuel', value: '2.4M MAD', trend: '+12%', color: 'bg-green-500' },
                  { label: 'DSO', value: '34 jours', trend: '-8%', color: 'bg-blue-500' },
                  { label: 'Stocks', value: '847 réf.', trend: '3 alertes', color: 'bg-orange-500' },
                ].map(kpi => (
                  <div key={kpi.label} className="bg-white/10 rounded-xl p-3">
                    <div className={`w-2 h-2 rounded-full ${kpi.color} mb-2`} />
                    <div className="text-xs text-blue-300 mb-1">{kpi.label}</div>
                    <div className="text-sm font-bold text-white">{kpi.value}</div>
                    <div className="text-xs text-blue-300 mt-1">{kpi.trend}</div>
                  </div>
                ))}
              </div>

              {/* Chart mockup */}
              <div className="bg-white/10 rounded-xl p-4">
                <div className="text-xs text-blue-300 mb-3">Évolution CA — 6 derniers mois</div>
                <div className="flex items-end gap-1.5 h-20">
                  {[45, 62, 55, 78, 71, 90].map((h, i) => (
                    <div key={i} className="flex-1 flex flex-col justify-end gap-1">
                      <div className="bg-blue-400 rounded-t-sm opacity-80" style={{ height: `${h}%` }} />
                    </div>
                  ))}
                </div>
                <div className="flex justify-between text-xs text-blue-400 mt-2">
                  {['Nov', 'Déc', 'Jan', 'Fév', 'Mar', 'Avr'].map(m => (
                    <span key={m}>{m}</span>
                  ))}
                </div>
              </div>

              {/* AI bar mockup */}
              <div className="mt-4 bg-white/10 rounded-xl px-4 py-3 flex items-center gap-3">
                <Icon path={ICONS.ai} className="w-4 h-4 text-blue-300 flex-shrink-0" />
                <span className="text-xs text-blue-200 italic">"Quel est mon top 5 clients ce trimestre ?"</span>
                <div className="ml-auto w-16 h-1.5 bg-blue-400 rounded-full animate-pulse" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Chiffres clés ────────────────────────────────────────────────────────────
function Stats() {
  const stats = [
    { value: '100+', label: 'Clients satisfaits', icon: ICONS.users },
    { value: '4',    label: 'Produits innovants', icon: ICONS.rocket },
    { value: '1j',   label: 'Time-to-value OptiBoard', icon: ICONS.clock },
    { value: '53+',  label: 'Endpoints API documentés', icon: ICONS.document },
  ]
  return (
    <section className="bg-primary-800 text-white py-14">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map(s => (
            <div key={s.label} className="text-center">
              <div className="flex justify-center mb-2">
                <Icon path={s.icon} className="w-8 h-8 text-blue-300" />
              </div>
              <div className="text-4xl font-extrabold text-white mb-1">{s.value}</div>
              <div className="text-sm text-blue-200">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Produits ─────────────────────────────────────────────────────────────────
function Products() {
  const products = [
    {
      name: 'OptiBoard',
      badge: 'Produit Phare',
      icon: ICONS.chart,
      color: 'bg-primary-800',
      featured: true,
      tagline: 'Business Intelligence & Reporting avec IA',
      description: 'Plateforme BI complète connectée nativement à Sage. Tableaux de bord temps réel, analyse des ventes, gestion des stocks, recouvrement DSO et assistant IA conversationnel.',
      features: ['Tableaux de bord temps réel', 'IA conversationnelle (NL → SQL)', 'Intégration Sage native', 'Builder no-code drag & drop', 'Multi-tenant & RBAC', 'Export Excel / PDF / PowerPoint'],
    },
    {
      name: 'OptiNotif',
      icon: ICONS.bell,
      color: 'bg-emerald-600',
      tagline: 'Notifications intelligentes temps réel',
      description: 'Envoyez des alertes automatiques à vos clients, équipes et partenaires par SMS, WhatsApp et Email — depuis votre ERP ou vos applications métier.',
      features: ['SMS, WhatsApp, Email', 'Déclencheurs automatiques', 'Templates personnalisables', 'Historique & analytics'],
    },
    {
      name: 'OptickFlow',
      icon: ICONS.cube,
      color: 'bg-violet-600',
      tagline: 'Gestion d\'inventaire intelligente',
      description: 'Suivi de stock en temps réel, traçabilité complète des mouvements, alertes de réapprovisionnement et rapports de rotation pour toute votre chaîne logistique.',
      features: ['Stock temps réel', 'Traçabilité mouvements', 'Alertes réapprovisionnement', 'Rapports de rotation'],
    },
    {
      name: 'OptiEDI',
      icon: ICONS.document,
      color: 'bg-orange-600',
      tagline: 'TVA & télédéclaration marocaine',
      description: 'Simplifiez votre conformité fiscale marocaine. Génération automatique des déclarations TVA, télétransmission à la DGI et archivage sécurisé.',
      features: ['Génération déclarations TVA', 'Télétransmission DGI', 'Conformité fiscale Maroc', 'Archivage sécurisé'],
    },
  ]

  return (
    <section id="produits" className="py-20 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14">
          <span className="inline-block text-primary-800 font-semibold text-sm uppercase tracking-wider mb-3">Nos Produits</span>
          <h2 className="section-title">Une suite logicielle pensée pour le Maroc</h2>
          <p className="section-subtitle">Quatre solutions complémentaires qui couvrent l'intégralité de votre pilotage opérationnel et financier.</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* OptiBoard — featured card grande */}
          <div className="lg:col-span-3">
            <div className="card p-8 border-2 border-primary-200 bg-gradient-to-br from-white to-primary-50 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-primary-100 rounded-full -translate-y-32 translate-x-32 opacity-50" />
              <div className="relative">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 bg-primary-800 rounded-xl flex items-center justify-center shadow-md">
                        <Icon path={products[0].icon} className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-2xl font-bold text-gray-900">{products[0].name}</h3>
                          <span className="text-xs bg-primary-800 text-white px-2.5 py-0.5 rounded-full font-semibold">{products[0].badge}</span>
                        </div>
                        <p className="text-primary-700 font-medium">{products[0].tagline}</p>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-6 max-w-2xl leading-relaxed">{products[0].description}</p>
                    <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
                      {products[0].features.map(f => (
                        <div key={f} className="flex items-center gap-2 text-sm text-gray-700">
                          <Icon path={ICONS.check} className="w-4 h-4 text-primary-700 flex-shrink-0" />
                          {f}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    <a href="#contact" className="btn-primary">
                      Demander une démo
                      <Icon path={ICONS.arrow} className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Autres produits */}
          {products.slice(1).map(p => (
            <div key={p.name} className="card p-6">
              <div className={`w-11 h-11 ${p.color} rounded-xl flex items-center justify-center mb-4 shadow-sm`}>
                <Icon path={p.icon} className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-1">{p.name}</h3>
              <p className="text-sm font-medium text-gray-500 mb-3">{p.tagline}</p>
              <p className="text-sm text-gray-600 mb-4 leading-relaxed">{p.description}</p>
              <ul className="space-y-1.5">
                {p.features.map(f => (
                  <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                    <Icon path={ICONS.check} className="w-4 h-4 text-green-500 flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Services ─────────────────────────────────────────────────────────────────
function Services() {
  const services = [
    {
      icon: ICONS.sage,
      title: 'Revendeur Sage Certifié',
      description: 'Intégration, déploiement, configuration et support des solutions Sage (Sage 100, Sage X3) pour PME industrielles et de distribution.',
      highlight: true,
    },
    {
      icon: ICONS.globe,
      title: 'Développement Web',
      description: 'Applications web métier sur mesure : dashboards, portails clients, intranets — React, FastAPI, full-stack moderne.',
    },
    {
      icon: ICONS.desktop,
      title: 'Applications Desktop',
      description: 'Logiciels Windows de gestion commerciale, facturation, comptabilité et paie — performance et robustesse pour vos équipes.',
    },
    {
      icon: ICONS.mobile,
      title: 'Applications Mobile',
      description: 'Apps Android & iOS pour vos commerciaux terrain, livreurs et agents logistiques — synchronisation temps réel avec votre ERP.',
    },
    {
      icon: ICONS.support,
      title: 'Prestation Informatique',
      description: 'Support technique, maintenance, formation utilisateurs et conseil en transformation digitale pour PME marocaines.',
    },
    {
      icon: ICONS.shield,
      title: 'Sécurité & Infrastructure',
      description: 'Audit de sécurité, mise en place RBAC, double authentification 2FA, déploiement Windows Server / IIS.',
    },
  ]

  return (
    <section id="services" className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14">
          <span className="inline-block text-primary-800 font-semibold text-sm uppercase tracking-wider mb-3">Nos Services</span>
          <h2 className="section-title">Un partenaire technologique complet</h2>
          <p className="section-subtitle">De l'intégration ERP au développement sur mesure, KAsoft accompagne votre transformation digitale.</p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map(s => (
            <div key={s.title} className={`card p-6 ${s.highlight ? 'border-2 border-primary-200 bg-primary-50' : ''}`}>
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-4 ${s.highlight ? 'bg-primary-800' : 'bg-gray-100'}`}>
                <Icon path={s.icon} className={`w-5 h-5 ${s.highlight ? 'text-white' : 'text-gray-600'}`} />
              </div>
              <h3 className="font-bold text-gray-900 mb-2 text-lg">
                {s.title}
                {s.highlight && <span className="ml-2 text-xs bg-primary-800 text-white px-2 py-0.5 rounded-full">Certifié</span>}
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed">{s.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Pourquoi KAsoft ──────────────────────────────────────────────────────────
function WhyKasoft() {
  const reasons = [
    {
      icon: ICONS.location,
      title: 'Expertise locale Maroc',
      body: 'Basés à Casablanca, nous comprenons les contraintes réglementaires, fiscales et culturelles des PME marocaines. Support en français et arabe.',
    },
    {
      icon: ICONS.sage,
      title: 'Intégration Sage native',
      body: 'Connexion directe à votre base Sage sans middleware coûteux. Vos données disponibles en temps réel, sans doublon ni re-saisie.',
    },
    {
      icon: ICONS.clock,
      title: 'Time-to-value < 1 jour',
      body: 'Connexion SQL Server, configuration initiale et premiers tableaux de bord en moins d\'une journée. Pas de mois d\'implémentation.',
    },
    {
      icon: ICONS.ai,
      title: 'IA accessible à tous',
      body: 'Posez vos questions en français naturel — l\'IA génère les analyses automatiquement. Pas besoin d\'être data scientist.',
    },
    {
      icon: ICONS.shield,
      title: 'Sécurité enterprise',
      body: 'RBAC, double authentification 2FA, requêtes paramétrées, déploiement on-premise possible. Vos données restent chez vous.',
    },
    {
      icon: ICONS.users,
      title: '100+ clients satisfaits',
      body: 'Références dans l\'industrie sanitaire, la distribution, le BTP et l\'agroalimentaire au Maroc. Accompagnement sur le long terme.',
    },
  ]

  return (
    <section id="pourquoi" className="py-20 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <span className="inline-block text-primary-800 font-semibold text-sm uppercase tracking-wider mb-3">Pourquoi KAsoft ?</span>
            <h2 className="section-title text-left">Votre partenaire digital de confiance au Maroc</h2>
            <p className="text-gray-500 mb-8 leading-relaxed">
              Depuis Casablanca, nous aidons les PME industrielles et de distribution à transformer leurs données en décisions — avec des solutions adaptées au contexte marocain.
            </p>
            <a href="#contact" className="btn-primary">
              Parler à un expert
              <Icon path={ICONS.arrow} className="w-4 h-4" />
            </a>
          </div>
          <div className="grid sm:grid-cols-2 gap-5">
            {reasons.map(r => (
              <div key={r.title} className="card p-5">
                <div className="w-9 h-9 bg-primary-100 rounded-lg flex items-center justify-center mb-3">
                  <Icon path={r.icon} className="w-5 h-5 text-primary-800" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-1.5">{r.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{r.body}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── CTA Banner ───────────────────────────────────────────────────────────────
function CTABanner() {
  return (
    <section className="bg-primary-800 py-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 className="text-3xl md:text-4xl font-extrabold text-white mb-4">
          Prêt à piloter votre entreprise avec l'IA ?
        </h2>
        <p className="text-blue-200 text-lg mb-8">
          Demandez une démo gratuite d'OptiBoard — connexion à votre Sage et premiers KPIs en moins d'une journée.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <a href="#contact" className="inline-flex items-center justify-center gap-2 bg-white text-primary-800 px-8 py-3.5 rounded-xl font-bold hover:bg-blue-50 transition-all shadow-lg">
            Demander une démo gratuite
            <Icon path={ICONS.arrow} className="w-5 h-5" />
          </a>
          <a href="tel:+212670834026" className="inline-flex items-center justify-center gap-2 border-2 border-white/40 text-white px-8 py-3.5 rounded-xl font-semibold hover:bg-white/10 transition-all">
            <Icon path={ICONS.phone} className="w-5 h-5" />
            +212 6 70 83 40 26
          </a>
        </div>
      </div>
    </section>
  )
}

// ─── Contact ──────────────────────────────────────────────────────────────────
function Contact() {
  const [form, setForm] = useState({ nom: '', email: '', tel: '', sujet: '', message: '' })
  const [sent, setSent] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    const body = `Nom: ${form.nom}%0ATéléphone: ${form.tel}%0ASujet: ${form.sujet}%0A%0A${form.message}`
    window.location.href = `mailto:contact@kasoft.ma?subject=Demande: ${form.sujet}&body=${body}`
    setSent(true)
  }

  return (
    <section id="contact" className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14">
          <span className="inline-block text-primary-800 font-semibold text-sm uppercase tracking-wider mb-3">Contact</span>
          <h2 className="section-title">Parlons de votre projet</h2>
          <p className="section-subtitle">Une démo gratuite de 30 min, sans engagement. Notre équipe Casablanca vous répond sous 24h.</p>
        </div>

        <div className="grid lg:grid-cols-5 gap-12">
          {/* Infos contact */}
          <div className="lg:col-span-2 space-y-8">
            <div>
              <h3 className="font-bold text-gray-900 text-lg mb-5">KAsoft — Casablanca</h3>
              <div className="space-y-4">
                {[
                  { icon: ICONS.phone,    label: 'Téléphone', value: '+212 6 70 83 40 26', href: 'tel:+212670834026' },
                  { icon: ICONS.mail,     label: 'Email',     value: 'contact@kasoft.ma',   href: 'mailto:contact@kasoft.ma' },
                  { icon: ICONS.location, label: 'Adresse',   value: 'Hay Essafa, Lissasfa, Casablanca', href: '#' },
                ].map(c => (
                  <div key={c.label} className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Icon path={c.icon} className="w-5 h-5 text-primary-800" />
                    </div>
                    <div>
                      <div className="text-xs text-gray-400 mb-0.5">{c.label}</div>
                      <a href={c.href} className="font-medium text-gray-800 hover:text-primary-800 transition-colors">
                        {c.value}
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Réseaux sociaux */}
            <div>
              <h4 className="font-semibold text-gray-700 mb-3">Suivez-nous</h4>
              <div className="flex gap-3">
                {[
                  { label: 'LinkedIn', href: 'https://linkedin.com/company/kasoft', color: 'bg-blue-700' },
                  { label: 'Facebook', href: 'https://facebook.com/kasoft', color: 'bg-blue-600' },
                  { label: 'YouTube',  href: 'https://youtube.com/@kasoft',  color: 'bg-red-600' },
                ].map(s => (
                  <a key={s.label} href={s.href} target="_blank" rel="noreferrer"
                    className={`${s.color} text-white text-xs px-3 py-2 rounded-lg font-medium hover:opacity-90 transition-opacity`}>
                    {s.label}
                  </a>
                ))}
              </div>
            </div>

            {/* Horaires */}
            <div className="bg-primary-50 rounded-xl p-5">
              <h4 className="font-semibold text-primary-900 mb-2 flex items-center gap-2">
                <Icon path={ICONS.clock} className="w-4 h-4" />
                Horaires
              </h4>
              <p className="text-sm text-primary-700">Lundi – Vendredi : 9h00 – 18h00</p>
              <p className="text-sm text-primary-700">Samedi : 9h00 – 13h00</p>
            </div>
          </div>

          {/* Formulaire */}
          <div className="lg:col-span-3">
            {sent ? (
              <div className="h-full flex flex-col items-center justify-center text-center py-12">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                  <Icon path={ICONS.check} className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Message envoyé !</h3>
                <p className="text-gray-500">Votre client mail va s'ouvrir. Notre équipe vous répond sous 24h.</p>
                <button onClick={() => setSent(false)} className="mt-6 text-primary-800 font-medium hover:underline">
                  Envoyer un autre message
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="card p-8 space-y-5">
                <div className="grid sm:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Nom & Prénom *</label>
                    <input required value={form.nom} onChange={e => setForm({...form, nom: e.target.value})}
                      placeholder="Mohammed Alami"
                      className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-800 focus:border-transparent transition" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Email *</label>
                    <input required type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})}
                      placeholder="m.alami@entreprise.ma"
                      className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-800 focus:border-transparent transition" />
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Téléphone</label>
                    <input value={form.tel} onChange={e => setForm({...form, tel: e.target.value})}
                      placeholder="+212 6 XX XX XX XX"
                      className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-800 focus:border-transparent transition" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Sujet *</label>
                    <select required value={form.sujet} onChange={e => setForm({...form, sujet: e.target.value})}
                      className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-800 focus:border-transparent transition bg-white">
                      <option value="">Choisir...</option>
                      <option>Démo OptiBoard</option>
                      <option>Intégration Sage</option>
                      <option>Développement sur mesure</option>
                      <option>Partenariat / Revendeur</option>
                      <option>Autre</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Message *</label>
                  <textarea required rows={4} value={form.message} onChange={e => setForm({...form, message: e.target.value})}
                    placeholder="Décrivez votre besoin — secteur d'activité, ERP utilisé, nombre d'utilisateurs..."
                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-800 focus:border-transparent transition resize-none" />
                </div>
                <button type="submit" className="btn-primary w-full justify-center">
                  Envoyer ma demande
                  <Icon path={ICONS.arrow} className="w-4 h-4" />
                </button>
                <p className="text-xs text-gray-400 text-center">Réponse garantie sous 24h ouvrées · Démo gratuite sans engagement</p>
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Footer ───────────────────────────────────────────────────────────────────
function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer className="bg-gray-900 text-gray-400 pt-14 pb-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-4 gap-10 mb-12">
          {/* Brand */}
          <div className="md:col-span-2">
            <div className="mb-4">
              <KasoftLogo dark={false} size="md" />
            </div>
            <p className="text-sm leading-relaxed mb-5 max-w-xs">
              Solutions BI, ERP et développement logiciel pour PME industrielles et de distribution au Maroc. Revendeur Sage certifié depuis Casablanca.
            </p>
            <div className="flex gap-3">
              {['LinkedIn', 'Facebook', 'YouTube', 'Instagram'].map(s => (
                <a key={s} href="#" className="w-9 h-9 bg-gray-800 rounded-lg flex items-center justify-center hover:bg-primary-800 transition-colors text-xs font-bold text-gray-300 hover:text-white">
                  {s[0]}
                </a>
              ))}
            </div>
          </div>

          {/* Produits */}
          <div>
            <h4 className="text-white font-semibold mb-4">Produits</h4>
            <ul className="space-y-2 text-sm">
              {['OptiBoard', 'OptiNotif', 'OptickFlow', 'OptiEDI'].map(p => (
                <li key={p}><a href="#produits" className="hover:text-white transition-colors">{p}</a></li>
              ))}
            </ul>
          </div>

          {/* Services */}
          <div>
            <h4 className="text-white font-semibold mb-4">Services</h4>
            <ul className="space-y-2 text-sm">
              {['Revendeur Sage', 'Développement Web', 'Applications Mobile', 'Prestation IT', 'Sécurité'].map(s => (
                <li key={s}><a href="#services" className="hover:text-white transition-colors">{s}</a></li>
              ))}
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <p className="text-sm">© {year} KAsoft · Hay Essafa, Lissasfa, Casablanca, Maroc</p>
          <div className="flex gap-6 text-sm">
            <a href="mailto:contact@kasoft.ma" className="hover:text-white transition-colors">contact@kasoft.ma</a>
            <a href="tel:+212670834026" className="hover:text-white transition-colors">+212 6 70 83 40 26</a>
          </div>
        </div>
      </div>
    </footer>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <Hero />
      <Stats />
      <Products />
      <Services />
      <WhyKasoft />
      <CTABanner />
      <Contact />
      <Footer />
    </div>
  )
}
