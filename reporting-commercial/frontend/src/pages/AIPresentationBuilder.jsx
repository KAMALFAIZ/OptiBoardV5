import { useState, useCallback } from 'react'
import {
  Presentation, FileSpreadsheet, ChevronRight, ChevronLeft,
  Sparkles, Download, FileDown, AlertCircle,
  CheckCircle2, Eye, Loader2, RotateCcw, Wand2
} from 'lucide-react'
import { aiGenerateDocument } from '../services/api'

// ─────────────────────────────────────────────────────────────────────────────
// PALETTES DE COULEURS PAR STYLE
// ─────────────────────────────────────────────────────────────────────────────
const PALETTES = {
  formal:  { bg: '#1E40AF', accent: '#2563EB', light: '#DBEAFE', text: '#1E294E', label: 'Classique' },
  dynamic: { bg: '#EA580C', accent: '#F97316', light: '#FFEDD5', text: '#431807', label: 'Dynamique' },
  minimal: { bg: '#181818', accent: '#525252', light: '#F5F5F5', text: '#181818', label: 'Épuré'     },
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function parseBullets(text, defaults, max = 4) {
  if (!text?.trim()) return defaults.slice(0, max)
  const lines = text.split(/[\n;]+/).map(s => s.trim()).filter(Boolean)
  return (lines.length ? lines : defaults).slice(0, max)
}

// ─────────────────────────────────────────────────────────────────────────────
// DÉFINITION DES TEMPLATES
// ─────────────────────────────────────────────────────────────────────────────
const PPTX_TEMPLATES = [
  {
    id: 'rapport_mensuel', name: 'Rapport Mensuel',
    desc: 'Synthèse des résultats commerciaux du mois',
    icon: '📊', gradient: 'from-blue-500 to-blue-700',
    fields: [
      { id: 'company',      label: 'Entreprise',         type: 'text',     placeholder: 'Ex : Acme SA' },
      { id: 'period',       label: 'Période',            type: 'text',     placeholder: 'Ex : Janvier 2025' },
      { id: 'highlights',   label: 'Points clés du mois',type: 'textarea', placeholder: 'CA, nouveaux clients, faits marquants…' },
      { id: 'next_actions', label: 'Actions à venir',    type: 'textarea', placeholder: 'Réunion équipe, lancement campagne…' },
    ],
    example: { company: 'Groupe Alboughaze', period: 'Mars 2025', highlights: 'CA mensuel 2,4M€ (+12% vs mars 2024)\n18 nouveaux clients signés\nMarge brute 38% — record historique\nLancement gamme Premium réussi', next_actions: 'Réunion direction le 10 avril\nDéploiement région Sud — 3 commerciaux\nLancement campagne email Q2\nSuivi top 5 prospects chauds' },
    getSlides: (fd) => [
      { type: 'title',   title: fd.company || 'Mon Entreprise', subtitle: `Rapport ${fd.period || 'Mensuel'}` },
      { type: 'agenda',  items: ['Résultats du mois', 'Analyse', 'Actions à venir'] },
      { type: 'content', title: 'Résultats du mois',   bullets: parseBullets(fd.highlights,   ['Chiffre d\'affaires', 'Nouveaux clients', 'Objectifs']) },
      { type: 'content', title: 'Analyse',              bullets: ['Tendances marché', 'Points d\'attention', 'Opportunités'] },
      { type: 'content', title: 'Actions à venir',      bullets: parseBullets(fd.next_actions, ['Action 1', 'Action 2', 'Suivi']) },
      { type: 'closing', message: 'Merci pour votre attention' },
    ],
  },
  {
    id: 'bilan_annuel', name: 'Bilan Annuel',
    desc: 'Revue complète des performances de l\'année',
    icon: '📈', gradient: 'from-indigo-500 to-purple-700',
    fields: [
      { id: 'company',    label: 'Entreprise',       type: 'text',     placeholder: 'Ex : Acme SA' },
      { id: 'year',       label: 'Année',            type: 'text',     placeholder: 'Ex : 2025' },
      { id: 'highlights', label: 'Points forts',     type: 'textarea', placeholder: 'Succès, réalisations majeures…' },
      { id: 'challenges', label: 'Défis rencontrés', type: 'textarea', placeholder: 'Difficultés, enseignements…' },
      { id: 'outlook',    label: 'Perspectives',     type: 'textarea', placeholder: 'Objectifs, ambitions pour l\'an prochain…' },
    ],
    example: { company: 'Groupe Alboughaze', year: '2024', highlights: 'CA annuel 28,5M€ (+18% vs 2023)\n220 nouveaux clients\nOuverture de 3 nouvelles régions\nLancement du portail client digital', challenges: 'Recrutement 12 postes — délais longs\nHausse des coûts matières premières\nConcurrence accrue sur segment PME', outlook: 'Objectif CA 34M€ pour 2025\nExpansion internationale — Belgique & Suisse\nRecrutement 20 collaborateurs\nDigitalisation complète des process commerciaux' },
    getSlides: (fd) => [
      { type: 'title',   title: fd.company || 'Mon Entreprise', subtitle: `Bilan ${fd.year || '2025'}` },
      { type: 'agenda',  items: ['Points forts', 'Défis', 'Résultats clés', 'Perspectives'] },
      { type: 'content', title: `Points forts ${fd.year || '2025'}`, bullets: parseBullets(fd.highlights, ['Croissance CA', 'Nouveaux clients', 'Innovation', 'Satisfaction client']) },
      { type: 'content', title: 'Défis & enseignements',           bullets: parseBullets(fd.challenges, ['Contexte marché', 'Pression marges', 'Recrutement', 'Concurrence']) },
      { type: 'section', title: 'Perspectives' },
      { type: 'content', title: 'Objectifs & perspectives',        bullets: parseBullets(fd.outlook,    ['Croissance +15%', 'Nouveaux marchés', 'Investissements', 'Recrutement']) },
      { type: 'closing', message: `Cap sur ${fd.year ? parseInt(fd.year)+1 : 'l\'avenir'} !` },
    ],
  },
  {
    id: 'pitch_client', name: 'Pitch Client',
    desc: 'Proposition commerciale percutante',
    icon: '🎯', gradient: 'from-orange-500 to-red-600',
    fields: [
      { id: 'company',    label: 'Votre entreprise',   type: 'text',     placeholder: 'Ex : Acme SA' },
      { id: 'client',     label: 'Nom du client',      type: 'text',     placeholder: 'Ex : Groupe Beta' },
      { id: 'project',    label: 'Solution proposée',  type: 'text',     placeholder: 'Ex : Plateforme de gestion' },
      { id: 'value_prop', label: 'Valeur ajoutée',     type: 'textarea', placeholder: 'Gain de temps, économies, performance…' },
      { id: 'next_steps', label: 'Prochaine étape',    type: 'text',     placeholder: 'Ex : Réunion de lancement' },
    ],
    example: { company: 'KAsoft', client: 'Groupe Meridian', project: 'OptiBoard — Reporting Commercial IA', value_prop: 'Gain de temps 60% sur les rapports mensuels\nVisibilité en temps réel sur le CA et les marges\nAlertes automatiques sur les anomalies\nExport PowerPoint & Excel en 1 clic', next_steps: 'Démo live le 15 avril — équipe direction' },
    getSlides: (fd) => [
      { type: 'title',   title: fd.client || 'Notre Client', subtitle: fd.project || 'Proposition Commerciale' },
      { type: 'agenda',  items: ['Qui sommes-nous', 'Votre besoin', 'Notre solution', 'Prochaines étapes'] },
      { type: 'content', title: `Qui sommes-nous — ${fd.company || 'Notre Entreprise'}`, bullets: ['Expert reconnu', 'Références solides', 'Équipe dédiée', 'Support inclus'] },
      { type: 'content', title: 'Votre besoin identifié',  bullets: parseBullets(fd.value_prop, ['Optimisation processus', 'Réduction coûts', 'Gain de temps', 'Performance']) },
      { type: 'content', title: fd.project || 'Notre Solution', bullets: ['Approche sur mesure', 'Déploiement rapide', 'ROI mesurable', 'Support dédié'] },
      { type: 'content', title: 'Prochaines étapes',       bullets: [fd.next_steps || 'Réunion lancement', 'Validation périmètre', 'Démarrage projet', 'Premiers résultats'] },
      { type: 'closing', message: 'Construisons ensemble votre succès' },
    ],
  },
  {
    id: 'presentation_produit', name: 'Lancement Produit',
    desc: 'Présentation d\'un nouveau produit ou service',
    icon: '🚀', gradient: 'from-emerald-500 to-teal-700',
    fields: [
      { id: 'company',  label: 'Entreprise',       type: 'text',     placeholder: 'Ex : Acme SA' },
      { id: 'product',  label: 'Nom du produit',   type: 'text',     placeholder: 'Ex : OptiBoard v5' },
      { id: 'target',   label: 'Cible clients',    type: 'text',     placeholder: 'Ex : PME du secteur retail' },
      { id: 'features', label: 'Fonctionnalités',  type: 'textarea', placeholder: 'Interface intuitive, intégrations, automatisation…' },
      { id: 'pricing',  label: 'Tarif (optionnel)',type: 'text',     placeholder: 'Ex : À partir de 99€/mois' },
    ],
    example: { company: 'KAsoft', product: 'OptiBoard v5', target: 'PME et ETI — secteurs commerce, distribution, industrie', features: 'Tableaux de bord temps réel connectés à Sage\nPivot & GridView sans formation\nGénération automatique de rapports PPTX & Excel par IA\nAlertes KPI et digest hebdomadaire direction\nDéploiement en 48h — zéro infrastructure', pricing: 'À partir de 290€/mois — essai gratuit 30 jours' },
    getSlides: (fd) => [
      { type: 'title',   title: fd.product || 'Notre Produit', subtitle: `Par ${fd.company || 'Notre Entreprise'}` },
      { type: 'agenda',  items: ['Le problème', 'Notre solution', 'Fonctionnalités', 'Tarifs & démarrage'] },
      { type: 'content', title: 'Le problème que nous résolvons', bullets: ['Processus trop longs', 'Manque de visibilité', 'Outils disparates', `Impact sur ${fd.target || 'votre activité'}`] },
      { type: 'content', title: `${fd.product || 'Notre Solution'} — en bref`, bullets: parseBullets(fd.features, ['Interface intuitive', 'Déploiement rapide', 'Intégration native', 'Support 7j/7']) },
      { type: 'section', title: 'Bénéfices & ROI' },
      { type: 'content', title: 'Pourquoi nous choisir',  bullets: [`Cible : ${fd.target || 'Toutes entreprises'}`, 'ROI dès le 1er mois', 'Satisfaction > 95%', fd.pricing || 'Tarif compétitif'] },
      { type: 'closing', message: 'Démarrez aujourd\'hui — essai gratuit 30 jours' },
    ],
  },
  {
    id: 'revue_performance', name: 'Revue de Performance',
    desc: 'Analyse KPIs et résultats d\'équipe',
    icon: '⚡', gradient: 'from-violet-500 to-purple-700',
    fields: [
      { id: 'company',      label: 'Entreprise',         type: 'text',     placeholder: 'Ex : Acme SA' },
      { id: 'team',         label: 'Équipe / Service',   type: 'text',     placeholder: 'Ex : Équipe commerciale' },
      { id: 'period',       label: 'Période',            type: 'text',     placeholder: 'Ex : T1 2025' },
      { id: 'kpis',         label: 'KPIs & résultats',   type: 'textarea', placeholder: 'CA +12%, NPS 72, Taux rétention 94%…' },
      { id: 'improvements', label: 'Points à améliorer', type: 'textarea', placeholder: 'Communication, délais, processus…' },
    ],
    example: { company: 'Groupe Alboughaze', team: 'Équipe Commerciale — 8 personnes', period: 'T1 2025', kpis: 'CA réalisé 6,8M€ — objectif 6,2M€ (+9,7%)\n28 nouveaux contrats signés\nNPS clients : 74 (objectif 68)\nTaux de rétention : 96%\nPanier moyen en hausse de 14%', improvements: 'Délais de réponse aux prospects (objectif < 4h)\nCoordination entre équipes sédentaire/terrain\nMise à jour CRM à systématiser' },
    getSlides: (fd) => [
      { type: 'title',   title: fd.team || 'Revue de Performance', subtitle: `${fd.company || ''} · ${fd.period || ''}`.replace(/^·|· ?$/g,'').trim() },
      { type: 'agenda',  items: ['KPIs & résultats', 'Points forts', 'Axes d\'amélioration', 'Plan d\'action'] },
      { type: 'content', title: 'KPIs & résultats',      bullets: parseBullets(fd.kpis,         ['Objectif 1 : atteint', 'Objectif 2 : en cours', 'Objectif 3 : à renforcer', 'NPS en hausse']) },
      { type: 'content', title: 'Points forts',          bullets: ['Cohésion d\'équipe', 'Délais respectés', 'Qualité de livraison', 'Initiatives prises'] },
      { type: 'section', title: 'Plan d\'amélioration' },
      { type: 'content', title: 'Axes d\'amélioration',  bullets: parseBullets(fd.improvements, ['Communication inter-équipes', 'Montée en compétences', 'Optimisation process', 'Suivi indicateurs']) },
      { type: 'closing', message: 'Continuons à progresser ensemble' },
    ],
  },
  {
    id: 'plan_strategique', name: 'Plan Stratégique',
    desc: 'Vision et axes stratégiques pluriannuels',
    icon: '🏆', gradient: 'from-slate-600 to-slate-800',
    fields: [
      { id: 'company', label: 'Entreprise',       type: 'text',     placeholder: 'Ex : Acme SA' },
      { id: 'horizon', label: 'Horizon',          type: 'text',     placeholder: 'Ex : 2025-2027' },
      { id: 'vision',  label: 'Vision',           type: 'textarea', placeholder: 'Ambition à long terme…' },
      { id: 'axes',    label: 'Axes stratégiques',type: 'textarea', placeholder: 'Commercial, Digital, RH, Innovation…' },
      { id: 'kpis',    label: 'Indicateurs clés', type: 'textarea', placeholder: 'CA cible, part de marché, NPS…' },
    ],
    example: { company: 'Groupe Alboughaze', horizon: '2025–2028', vision: 'Devenir le leader régional de la distribution spécialisée, reconnu pour l\'excellence de service et l\'innovation digitale', axes: 'Croissance commerciale — expansion géographique et nouveaux segments\nExcellence opérationnelle — digitalisation et automatisation\nCapital humain — attractivité, formation et fidélisation\nInnovation produit — gammes premium et services à valeur ajoutée', kpis: 'CA cible 2028 : 45M€\nPart de marché régionale : +8 points\nNPS > 80\nEffectif : 180 collaborateurs\nROI digital : x3 sur 3 ans' },
    getSlides: (fd) => [
      { type: 'title',   title: fd.company || 'Notre Entreprise', subtitle: `Plan Stratégique ${fd.horizon || '2025-2027'}` },
      { type: 'agenda',  items: ['Vision', 'Axes stratégiques', 'Feuille de route', 'Indicateurs'] },
      { type: 'content', title: 'Notre vision',             bullets: parseBullets(fd.vision, ['Leader sur notre marché', 'Croissance durable', 'Innovation continue', 'Satisfaction client']) },
      { type: 'content', title: 'Axes stratégiques',       bullets: parseBullets(fd.axes,   ['Développement commercial', 'Excellence opérationnelle', 'Innovation & digital', 'Talent & culture']) },
      { type: 'section', title: 'Feuille de route' },
      { type: 'content', title: 'Feuille de route',        bullets: ['Court terme : consolidation', 'Moyen terme : expansion', 'Long terme : leadership', 'Revue trimestrielle'] },
      { type: 'content', title: 'Indicateurs de succès',   bullets: parseBullets(fd.kpis,  ['CA cible défini', 'Part de marché', 'NPS > 70', 'Rétention > 90%']) },
      { type: 'closing', message: 'Ensemble vers notre vision' },
    ],
  },
]

const EXCEL_TEMPLATES = [
  {
    id: 'budget_previsionnel', name: 'Budget Prévisionnel',
    desc: 'Suivi budgétaire par catégorie avec écarts',
    icon: '💰', gradient: 'from-green-500 to-emerald-700',
    fields: [
      { id: 'company', label: 'Entreprise', type: 'text', placeholder: 'Ex : Acme SA' },
      { id: 'year',    label: 'Année',      type: 'text', placeholder: 'Ex : 2025' },
    ],
    example: { company: 'Groupe Alboughaze', year: '2025' },
    getPreview: (fd) => ({
      title: `Budget Prévisionnel ${fd.year || '2025'} — ${fd.company || 'Mon Entreprise'}`,
      columns: ['Catégorie', 'Budget N-1', 'Budget N', 'Évolution', 'Commentaire'],
      rows: [['Ressources Humaines','320 000 €','350 000 €','+9,4%','Recrutement'], ['Marketing','85 000 €','95 000 €','+11,8%','Digital'], ['Informatique','60 000 €','80 000 €','+33,3%','Cloud']],
    }),
  },
  {
    id: 'suivi_commercial', name: 'Suivi Commercial',
    desc: 'Performances et objectifs par commercial',
    icon: '📋', gradient: 'from-blue-500 to-cyan-600',
    fields: [
      { id: 'company', label: 'Entreprise', type: 'text', placeholder: 'Ex : Acme SA' },
      { id: 'period',  label: 'Période',   type: 'text', placeholder: 'Ex : T1 2025' },
    ],
    example: { company: 'Groupe Alboughaze', period: 'T1 2025' },
    getPreview: (fd) => ({
      title: `Suivi Commercial ${fd.period || 'T1 2025'} — ${fd.company || 'Mon Entreprise'}`,
      columns: ['Commercial', 'Objectif CA', 'CA Réalisé', 'Atteinte', 'Nb Clients'],
      rows: [['Jean Martin','150 000 €','162 000 €','108%','18'], ['Sophie D.','120 000 €','108 000 €','90%','14'], ['Pierre L.','180 000 €','195 000 €','108%','22']],
    }),
  },
  {
    id: 'analyse_clients', name: 'Analyse Clients',
    desc: 'CA, évolution et comportement d\'achat',
    icon: '👥', gradient: 'from-violet-500 to-indigo-700',
    fields: [
      { id: 'company', label: 'Entreprise', type: 'text', placeholder: 'Ex : Acme SA' },
      { id: 'period',  label: 'Période',   type: 'text', placeholder: 'Ex : 2025' },
    ],
    example: { company: 'Groupe Alboughaze', period: '2024' },
    getPreview: (fd) => ({
      title: `Analyse Clients ${fd.period || '2025'} — ${fd.company || 'Mon Entreprise'}`,
      columns: ['Client', 'Segment', 'CA Annuel', 'Évolution', 'Commandes'],
      rows: [['Groupe Alpha','Grand Compte','285 000 €','+12%','38'], ['Beta Ind.','ETI','142 000 €','+8%','24'], ['Gamma SARL','PME','68 000 €','+22%','18']],
    }),
  },
  {
    id: 'planning_projet', name: 'Planning Projet',
    desc: 'Phases, responsables et avancement',
    icon: '📅', gradient: 'from-orange-500 to-amber-600',
    fields: [
      { id: 'project', label: 'Nom du projet', type: 'text', placeholder: 'Ex : Migration ERP' },
      { id: 'team',    label: 'Équipe',        type: 'text', placeholder: 'Ex : Équipe IT' },
    ],
    example: { project: 'Déploiement OptiBoard', team: 'Équipe DSI / KAsoft' },
    getPreview: (fd) => ({
      title: `${fd.project || 'Mon Projet'} — Planning`,
      columns: ['Phase', 'Responsable', 'Début', 'Fin', 'Avancement', 'Statut'],
      rows: [['Cadrage', fd.team || 'Chef projet','06/01','17/01','100%','✅ Terminé'], ['Conception', fd.team || 'Équipe','20/01','07/02','80%','🔄 En cours'], ['Déploiement', fd.team || 'DevOps','07/04','11/04','0%','⏳ À venir']],
    }),
  },
]

// ─────────────────────────────────────────────────────────────────────────────
// COMPOSANT : SLIDE MINIATURE (HTML/CSS)
// ─────────────────────────────────────────────────────────────────────────────
function MiniSlide({ slide, pal, w = 280, h = 157 }) {
  const s = { width: w, height: h, position: 'relative', overflow: 'hidden', borderRadius: 4, fontFamily: 'system-ui,sans-serif', flexShrink: 0 }
  const sc = w / 280   // facteur d'échelle
  const px = n => n * sc

  if (slide.type === 'title') return (
    <div style={{ ...s, background: pal.bg }}>
      <div style={{ position:'absolute', left:0, top:0, width:px(8), height:h, background:pal.accent }} />
      <div style={{ position:'absolute', left:px(16), top:px(44), right:px(16), color:'#fff', fontSize:px(14), fontWeight:'bold', lineHeight:1.2 }}>
        {slide.title || 'Titre'}
      </div>
      {slide.subtitle && <div style={{ position:'absolute', left:px(16), top:px(65), right:px(16), color:'#BFDBFE', fontSize:px(8) }}>{slide.subtitle}</div>}
      <div style={{ position:'absolute', bottom:px(8), left:px(16), color:'#93C5FD', fontSize:px(6), fontStyle:'italic' }}>OptiBoard</div>
    </div>
  )

  if (slide.type === 'agenda') return (
    <div style={{ ...s, background:'#F9FAFB' }}>
      <div style={{ position:'absolute', left:0, top:0, right:0, height:px(22), background:pal.bg, display:'flex', alignItems:'center', paddingLeft:px(8) }}>
        <span style={{ color:'#fff', fontSize:px(9), fontWeight:'bold' }}>Sommaire</span>
      </div>
      <div style={{ position:'absolute', top:px(28), left:px(8), right:px(8) }}>
        {(slide.items || []).map((item, i) => (
          <div key={i} style={{ display:'flex', alignItems:'center', gap:px(4), marginBottom:px(5) }}>
            <div style={{ width:px(10), height:px(10), background:pal.accent, borderRadius:px(2), flexShrink:0, display:'flex', alignItems:'center', justifyContent:'center' }}>
              <span style={{ color:'#fff', fontSize:px(6), fontWeight:'bold' }}>{i+1}</span>
            </div>
            <span style={{ fontSize:px(7), color:pal.text }}>{item}</span>
          </div>
        ))}
      </div>
    </div>
  )

  if (slide.type === 'section') return (
    <div style={{ ...s, background:pal.light }}>
      <div style={{ position:'absolute', left:0, top:0, width:px(6), height:h, background:pal.accent }} />
      <div style={{ position:'absolute', left:0, right:0, top:'38%', height:px(30), background:pal.bg, display:'flex', alignItems:'center', justifyContent:'center' }}>
        <span style={{ color:'#fff', fontSize:px(11), fontWeight:'bold' }}>{slide.title}</span>
      </div>
    </div>
  )

  if (slide.type === 'content') return (
    <div style={{ ...s, background:'#F9FAFB' }}>
      <div style={{ position:'absolute', left:0, top:0, right:0, height:px(22), background:pal.bg, display:'flex', alignItems:'center', paddingLeft:px(8) }}>
        <span style={{ color:'#fff', fontSize:px(9), fontWeight:'bold', overflow:'hidden', whiteSpace:'nowrap', textOverflow:'ellipsis', maxWidth:'90%' }}>{slide.title}</span>
      </div>
      <div style={{ position:'absolute', top:px(26), left:px(8), right:px(8) }}>
        {(slide.bullets || []).slice(0,5).map((b, i) => (
          <div key={i} style={{ display:'flex', gap:px(4), marginBottom:px(5), alignItems:'flex-start' }}>
            <div style={{ width:px(4), height:px(4), background:pal.accent, borderRadius:'50%', marginTop:px(3), flexShrink:0 }} />
            <span style={{ fontSize:px(7), color:pal.text, lineHeight:1.3 }}>{b}</span>
          </div>
        ))}
      </div>
    </div>
  )

  if (slide.type === 'closing') return (
    <div style={{ ...s, background:pal.bg }}>
      <div style={{ position:'absolute', left:0, top:0, width:px(8), height:h, background:pal.accent }} />
      <div style={{ position:'absolute', left:px(16), top:px(52), right:px(16), color:'#fff', fontSize:px(12), fontWeight:'bold', lineHeight:1.3 }}>
        {slide.message || 'Merci'}
      </div>
      <div style={{ position:'absolute', bottom:px(8), left:px(16), color:'#BFDBFE', fontSize:px(6), fontStyle:'italic' }}>Questions & Échanges</div>
    </div>
  )

  return <div style={{ ...s, background:'#E5E7EB' }} />
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPOSANT : APERÇU EXCEL MINIATURE
// ─────────────────────────────────────────────────────────────────────────────
function ExcelPreview({ preview, w = 280 }) {
  if (!preview) return null
  const { title, columns, rows } = preview
  const sc = w / 280
  const px = n => n * sc
  return (
    <div style={{ width: w, fontFamily: 'system-ui,sans-serif', borderRadius: 4, overflow: 'hidden', border: '1px solid #E5E7EB' }}>
      <div style={{ background: '#1E3A8A', padding: `${px(6)}px ${px(8)}px`, color: '#fff', fontSize: px(9), fontWeight: 'bold' }}>{title}</div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th key={i} style={{ background: '#2563EB', color: '#fff', padding: `${px(3)}px ${px(4)}px`, fontSize: px(7), fontWeight: 'bold', textAlign: 'left', borderRight: '1px solid #1D4ED8' }}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} style={{ background: ri % 2 === 0 ? '#F9FAFB' : '#fff' }}>
              {row.map((cell, ci) => (
                <td key={ci} style={{ padding: `${px(3)}px ${px(4)}px`, fontSize: px(7), color: '#374151', borderBottom: '1px solid #E5E7EB', borderRight: '1px solid #E5E7EB', whiteSpace: 'nowrap', overflow: 'hidden', maxWidth: px(60) }}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ background: '#EFF6FF', padding: `${px(4)}px ${px(8)}px`, color: '#6B7280', fontSize: px(6), fontStyle: 'italic' }}>
        + lignes générées par l'IA
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPOSANT : CARTE TEMPLATE (galerie)
// ─────────────────────────────────────────────────────────────────────────────
function TemplateCard({ tpl, docType, onSelect, isHovered, onHover, onLeave }) {
  const previewSlides = docType === 'pptx' ? tpl.getSlides({}) : null
  const pal = PALETTES.formal

  return (
    <div
      onMouseEnter={onHover} onMouseLeave={onLeave}
      onClick={() => onSelect(tpl)}
      className="group relative bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-500 cursor-pointer transition-all hover:shadow-md overflow-hidden"
    >
      {/* Thumbnail */}
      <div className="relative overflow-hidden bg-gray-100 dark:bg-gray-700" style={{ height: 90 }}>
        <div className={`absolute inset-0 bg-gradient-to-br ${tpl.gradient} opacity-90`} />
        <div className="absolute inset-0 flex items-center justify-center">
          <span style={{ fontSize: 32 }}>{tpl.icon}</span>
        </div>
        {/* Mini slide preview en overlay (au hover) */}
        {isHovered && docType === 'pptx' && previewSlides?.length > 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/30">
            <div style={{ transform: 'scale(0.48)', transformOrigin: 'center' }}>
              <MiniSlide slide={previewSlides[0]} pal={pal} w={280} h={157} />
            </div>
          </div>
        )}
        {isHovered && docType === 'excel' && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/30 p-2">
            <div style={{ transform: 'scale(0.48)', transformOrigin: 'center' }}>
              <ExcelPreview preview={tpl.getPreview({})} w={280} />
            </div>
          </div>
        )}
      </div>

      {/* Infos */}
      <div className="p-3">
        <div className="font-semibold text-sm text-gray-900 dark:text-white">{tpl.name}</div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">{tpl.desc}</div>
      </div>

      {/* Badge Aperçu */}
      {isHovered && (
        <div className="absolute top-2 right-2 flex items-center gap-1 bg-black/50 text-white text-[10px] px-1.5 py-0.5 rounded-full">
          <Eye className="w-2.5 h-2.5" /> Aperçu
        </div>
      )}

      {/* Flèche CTA */}
      <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center">
          <ChevronRight className="w-3.5 h-3.5 text-white" />
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// PAGE PRINCIPALE
// ─────────────────────────────────────────────────────────────────────────────
export default function AIPresentationBuilder() {
  const [docType,  setDocType]  = useState('pptx')
  const [screen,   setScreen]   = useState('gallery')   // 'gallery' | 'form' | 'success'
  const [template, setTemplate] = useState(null)
  const [formData, setFormData] = useState({})
  const [style,    setStyle]    = useState('formal')
  const [previewIdx, setPreviewIdx] = useState(0)
  const [hoveredId, setHoveredId]   = useState(null)

  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError]               = useState(null)
  const [downloadName, setDownloadName] = useState(null)

  const templates = docType === 'pptx' ? PPTX_TEMPLATES : EXCEL_TEMPLATES
  const pal       = PALETTES[style] || PALETTES.formal

  // Slides de preview en temps réel
  const liveSlides  = template && docType === 'pptx' ? template.getSlides({ ...formData, style }) : []
  const livePreview = template && docType === 'excel' ? template.getPreview(formData) : null

  const selectTemplate = useCallback((tpl) => {
    setTemplate(tpl); setFormData({}); setStyle('formal'); setPreviewIdx(0); setError(null); setDownloadName(null); setScreen('form')
  }, [])

  const handleField = (id, val) => {
    setFormData(p => ({ ...p, [id]: val }))
    setPreviewIdx(0)
  }

  const generate = async () => {
    setIsGenerating(true); setError(null)
    try {
      const res = await aiGenerateDocument(template.id, { ...formData, style }, docType)
      const cd  = res.headers?.['content-disposition'] || ''
      const m   = cd.match(/filename="?([^"]+)"?/)
      const filename = m ? m[1] : (docType === 'pptx' ? 'presentation.pptx' : 'rapport.xlsx')
      const url = URL.createObjectURL(res.data)
      const a   = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url)
      setDownloadName(filename); setScreen('success')
    } catch (err) {
      setError("Erreur lors de la génération. Vérifiez que le backend est démarré (port 8084).")
    } finally {
      setIsGenerating(false)
    }
  }

  const reset = () => { setScreen('gallery'); setTemplate(null); setFormData({}); setError(null); setDownloadName(null) }

  // ── ÉCRAN 1 : GALERIE ─────────────────────────────────────────────────────
  if (screen === 'gallery') return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="max-w-5xl mx-auto w-full px-4 py-5 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 dark:text-white">Créateur de Documents IA</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">Choisissez un modèle, remplissez le formulaire, téléchargez</p>
            </div>
          </div>
        </div>

        {/* Sélecteur type */}
        <div className="flex gap-3">
          {[
            { id: 'pptx',  label: 'Présentation PowerPoint', icon: Presentation,    count: PPTX_TEMPLATES.length },
            { id: 'excel', label: 'Fichier Excel',            icon: FileSpreadsheet, count: EXCEL_TEMPLATES.length },
          ].map(({ id, label, icon: Icon, count }) => (
            <button key={id} onClick={() => setDocType(id)}
              className={`flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-sm font-medium border-2 transition-all ${
                docType === id
                  ? id === 'pptx' ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                                  : 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                  : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-300'
              }`}>
              <Icon className="w-4 h-4" />
              {label}
              <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-500">{count}</span>
            </button>
          ))}
        </div>

        {/* Grille de templates */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {templates.map(tpl => (
            <TemplateCard
              key={tpl.id} tpl={tpl} docType={docType}
              onSelect={selectTemplate}
              isHovered={hoveredId === tpl.id}
              onHover={() => setHoveredId(tpl.id)}
              onLeave={() => setHoveredId(null)}
            />
          ))}
        </div>

        <p className="text-center text-xs text-gray-400 dark:text-gray-600 pb-4">
          Survolez un modèle pour voir l'aperçu · L'IA enrichit automatiquement le contenu
        </p>
      </div>
    </div>
  )

  // ── ÉCRAN 2 : FORMULAIRE + APERÇU ─────────────────────────────────────────
  if (screen === 'form') return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Barre du haut */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex-shrink-0">
        <button onClick={() => setScreen('gallery')} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
          <ChevronLeft className="w-4 h-4" /> Modèles
        </button>
        <div className="w-px h-5 bg-gray-200 dark:bg-gray-700" />
        <span className="text-base font-semibold text-gray-800 dark:text-white flex items-center gap-2">
          <span>{template?.icon}</span> {template?.name}
        </span>
        <div className="ml-auto flex items-center gap-2">
          {error && (
            <div className="flex items-center gap-1.5 text-red-600 dark:text-red-400 text-xs">
              <AlertCircle className="w-3.5 h-3.5" /> {error}
            </div>
          )}
          <button onClick={generate} disabled={isGenerating}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-lg text-sm font-medium transition-colors shadow-sm">
            {isGenerating
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Génération…</>
              : <><FileDown className="w-4 h-4" /> Générer {docType === 'pptx' ? 'la Présentation' : 'le fichier Excel'}</>
            }
          </button>
        </div>
      </div>

      {/* Corps : formulaire + aperçu */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Formulaire (gauche) */}
        <div className="w-72 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 overflow-y-auto bg-gray-50 dark:bg-gray-900 p-4 space-y-4">
          {/* Bouton exemple */}
          {template?.example && (
            <button
              onClick={() => { setFormData(template.example); setPreviewIdx(0) }}
              className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg border border-dashed border-indigo-300 dark:border-indigo-700 text-xs text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors"
            >
              <Wand2 className="w-3.5 h-3.5" /> Remplir avec un exemple
            </button>
          )}

          {/* Champs du template */}
          {template?.fields?.map(field => (
            <div key={field.id}>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">{field.label}</label>
              {field.type === 'textarea' ? (
                <textarea value={formData[field.id] || ''} onChange={e => handleField(field.id, e.target.value)}
                  placeholder={field.placeholder} rows={3}
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none" />
              ) : (
                <input type="text" value={formData[field.id] || ''} onChange={e => handleField(field.id, e.target.value)}
                  placeholder={field.placeholder}
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              )}
            </div>
          ))}

          {/* Style (PPTX seulement) */}
          {docType === 'pptx' && (
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Style</label>
              <div className="flex gap-1.5">
                {Object.entries(PALETTES).map(([key, p]) => (
                  <button key={key} onClick={() => { setStyle(key); setPreviewIdx(0) }}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-medium border-2 transition-all ${
                      style === key ? 'border-indigo-500 text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/20' : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400'
                    }`}>
                    <div className="w-3 h-3 rounded-full mx-auto mb-0.5" style={{ background: p.bg }} />
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="pt-2 text-xs text-gray-400 dark:text-gray-600 text-center">
            ✨ L'IA enrichit automatiquement le contenu
          </div>
        </div>

        {/* Aperçu (droite) */}
        <div className="flex-1 flex flex-col overflow-hidden bg-gray-100 dark:bg-gray-950">
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex-shrink-0">
            <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
              <Eye className="w-3.5 h-3.5" /> Aperçu en direct
              {docType === 'pptx' && <span className="text-gray-400"> · Slide {previewIdx + 1} / {liveSlides.length}</span>}
            </div>
            {docType === 'pptx' && (
              <div className="flex items-center gap-1">
                <button onClick={() => setPreviewIdx(i => Math.max(0, i-1))} disabled={previewIdx === 0}
                  className="w-6 h-6 rounded flex items-center justify-center text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30 transition-colors">
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button onClick={() => setPreviewIdx(i => Math.min(liveSlides.length-1, i+1))} disabled={previewIdx >= liveSlides.length-1}
                  className="w-6 h-6 rounded flex items-center justify-center text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30 transition-colors">
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          <div className="flex-1 flex items-center justify-center p-6 overflow-auto">
            {docType === 'pptx' && liveSlides.length > 0 ? (
              <div className="flex flex-col items-center gap-4">
                {/* Slide principal agrandi */}
                <div className="shadow-xl rounded-lg overflow-hidden ring-1 ring-black/10">
                  <MiniSlide slide={liveSlides[previewIdx]} pal={pal} w={480} h={270} />
                </div>
                {/* Pellicule de slides */}
                <div className="flex gap-2 flex-wrap justify-center">
                  {liveSlides.map((sl, i) => (
                    <button key={i} onClick={() => setPreviewIdx(i)}
                      className={`rounded overflow-hidden transition-all ${previewIdx === i ? 'ring-2 ring-indigo-500 scale-105' : 'opacity-60 hover:opacity-90'}`}
                      title={sl.title || sl.type}>
                      <MiniSlide slide={sl} pal={pal} w={80} h={45} />
                    </button>
                  ))}
                </div>
              </div>
            ) : docType === 'excel' && livePreview ? (
              <div className="shadow-xl rounded-lg overflow-hidden bg-white" style={{ maxWidth: 560 }}>
                <ExcelPreview preview={livePreview} w={520} />
              </div>
            ) : (
              <div className="text-gray-400 dark:text-gray-600 text-sm">Remplissez le formulaire pour voir l'aperçu</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )

  // ── ÉCRAN 3 : SUCCÈS ─────────────────────────────────────────────────────
  if (screen === 'success') return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto w-full px-4 py-5 space-y-5">
        {/* Header succès */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">Fichier généré avec succès !</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">{downloadName} a été téléchargé</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={generate} disabled={isGenerating}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-indigo-600 dark:text-indigo-400 border border-indigo-300 dark:border-indigo-700 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
              {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              Retélécharger
            </button>
            <button onClick={reset}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
              <RotateCcw className="w-3.5 h-3.5" /> Nouveau document
            </button>
          </div>
        </div>

        {/* Aperçu de la présentation générée */}
        {docType === 'pptx' && liveSlides.length > 0 && (
          <>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Aperçu des slides générés</h3>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
              {liveSlides.map((sl, i) => (
                <div key={i} className="flex flex-col gap-1">
                  <div className="shadow rounded-lg overflow-hidden ring-1 ring-black/5">
                    <MiniSlide slide={sl} pal={pal} w={160} h={90} />
                  </div>
                  <p className="text-[10px] text-gray-400 dark:text-gray-600 text-center truncate">
                    {i+1}. {sl.title || sl.type}
                  </p>
                </div>
              ))}
            </div>
          </>
        )}

        {docType === 'excel' && livePreview && (
          <>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Aperçu du fichier généré</h3>
            <div className="shadow rounded-lg overflow-hidden bg-white dark:bg-gray-800">
              <ExcelPreview preview={livePreview} w={600} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
