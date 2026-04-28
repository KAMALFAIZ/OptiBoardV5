import { useState, useEffect, useCallback } from 'react'
import { useDWH } from '../context/DWHContext'
import {
  Shield, Plus, Trash2, ChevronRight, Users, Key, Database,
  Eye, EyeOff, Check, X, Save, Settings, RefreshCw, AlertCircle,
  CheckCircle, LayoutDashboard, Table2, BarChart3,
  Sparkles, Bot, TrendingUp, Bell, Wrench, ToggleLeft, ToggleRight,
  ShoppingCart, Package, CreditCard, Calendar, Layers, Zap, Activity,
  ChevronDown, ChevronUp, Lock, Unlock,
} from 'lucide-react'
import api from '../services/api'

// ─── Constantes ───────────────────────────────────────────────────────────────

const PRESET_COLORS = [
  { value: '#3B82F6', label: 'Bleu' },
  { value: '#8B5CF6', label: 'Violet' },
  { value: '#10B981', label: 'Vert' },
  { value: '#F59E0B', label: 'Ambre' },
  { value: '#EF4444', label: 'Rouge' },
  { value: '#6B7280', label: 'Gris' },
]

const EMPTY_ROLE_FORM = { nom: '', description: '', couleur: '#3B82F6', is_admin: false }

const REPORT_TYPES = [
  { key: 'dashboards', label: 'Dashboards', icon: LayoutDashboard },
  { key: 'gridviews', label: 'GridViews', icon: Table2 },
  { key: 'pivots', label: 'Pivots', icon: BarChart3 },
]

// ─── Catalogue complet des fonctionnalités OptiBoard ──────────────────────────
const FEATURE_CATEGORIES = [
  {
    id: 'reporting',
    label: 'Rapports & Analyses',
    icon: TrendingUp,
    color: '#3B82F6',
    features: [
      { code: 'ventes',       label: 'Analyse des Ventes',    desc: 'Ventes, évolution, top clients et produits' },
      { code: 'stocks',       label: 'Gestion des Stocks',    desc: 'Niveaux de stock, rotations, alertes' },
      { code: 'recouvrement', label: 'Recouvrement & DSO',    desc: 'Créances, encours clients, jours de retard' },
      { code: 'analyse_ca',   label: 'Analyse CA & Créances', desc: 'Comparatif chiffre d\'affaires et créances' },
      { code: 'liste_ventes', label: 'Liste Ventes Détail',   desc: 'Détail ligne par ligne des transactions' },
      { code: 'pic',          label: 'Plan Industriel & Commercial', desc: 'PIC annuel et suivi objectifs' },
    ],
  },
  {
    id: 'ai',
    label: 'Intelligence Artificielle',
    icon: Sparkles,
    color: '#8B5CF6',
    features: [
      { code: 'ai_assistant',  label: 'Assistant IA',               desc: 'Chat IA pour analyse et questions sur les données' },
      { code: 'ai_resume',     label: 'Résumé Exécutif IA',         desc: 'Synthèse automatique des KPIs et performances' },
      { code: 'ai_anomalies',  label: 'Détection d\'Anomalies',     desc: 'Alertes automatiques sur données anormales' },
      { code: 'ai_forecast',   label: 'Forecasting / Prévision',    desc: 'Prévisions de ventes et tendances par IA' },
      { code: 'ai_insights',   label: 'AI Insights Automatiques',   desc: 'Recommandations et observations en temps réel' },
      { code: 'ai_sql',        label: 'Requêtes SQL Naturelles',    desc: 'Générer des requêtes SQL en langage naturel' },
    ],
  },
  {
    id: 'builders',
    label: 'Outils & Builders',
    icon: Wrench,
    color: '#10B981',
    features: [
      { code: 'builder',          label: 'Dashboard Builder',      desc: 'Créer et modifier des tableaux de bord' },
      { code: 'pivot_builder',    label: 'Pivot Builder',          desc: 'Créer et modifier des tableaux croisés dynamiques' },
      { code: 'gridview_builder', label: 'GridView Builder',       desc: 'Créer et modifier des grilles de données' },
      { code: 'datasources',      label: 'DataSource Templates',   desc: 'Gérer les templates de sources de données SQL/API' },
      { code: 'drillthrough',     label: 'Drill-through Config',   desc: 'Configurer la navigation en profondeur' },
    ],
  },
  {
    id: 'subscriptions',
    label: 'Abonnements & Alertes',
    icon: Bell,
    color: '#F59E0B',
    features: [
      { code: 'abonnements',  label: 'Mes Abonnements',    desc: 'S\'abonner et gérer les alertes personnelles' },
      { code: 'alertes_kpi',  label: 'Alertes KPI',        desc: 'Configurer des seuils d\'alerte sur indicateurs' },
      { code: 'scheduler',    label: 'Envois Planifiés',   desc: 'Planifier l\'envoi automatique de rapports par email' },
    ],
  },
  {
    id: 'administration',
    label: 'Administration',
    icon: Settings,
    color: '#EF4444',
    features: [
      { code: 'menus',         label: 'Gestion Menus',          desc: 'Configurer les menus de navigation personnalisés' },
      { code: 'themes',        label: 'Gestion Thèmes',         desc: 'Personnaliser les couleurs et l\'apparence' },
      { code: 'etl_admin',     label: 'ETL Administration',     desc: 'Gérer la synchronisation des données ETL' },
      { code: 'client_users',  label: 'Gestion Utilisateurs',   desc: 'Créer, modifier et supprimer des utilisateurs' },
      { code: 'roles_admin',   label: 'Rôles & Permissions',    desc: 'Gérer les rôles et les droits d\'accès' },
      { code: 'settings',      label: 'Paramètres Système',     desc: 'Configuration globale de l\'application' },
      { code: 'updates',       label: 'Gestionnaire MàJ',       desc: 'Gérer les mises à jour de l\'application' },
      { code: 'client_dwh',    label: 'Mon DWH',                desc: 'Accéder à la configuration de son entrepôt de données' },
    ],
  },
]

// Tous les codes de fonctionnalités
const ALL_FEATURE_CODES = FEATURE_CATEGORIES.flatMap(c => c.features.map(f => f.code))

// ─── Helpers ──────────────────────────────────────────────────────────────────

function colorBadgeStyle(color) {
  return {
    backgroundColor: color + '20',
    color: color,
    border: `1px solid ${color}40`,
  }
}

function extractError(e, fallback = 'Erreur') {
  return e?.response?.data?.detail || e?.response?.data?.message || e?.response?.data?.error || e?.message || fallback
}

// ─── Composant principal ───────────────────────────────────────────────────────

export default function RolesAdmin() {
  const { currentDWH } = useDWH()
  const dwhCode = currentDWH?.code || null
  const headers = dwhCode ? { 'X-DWH-Code': dwhCode } : {}

  // Onglets
  const [activeTab, setActiveTab] = useState('roles')

  // Rôles
  const [roles, setRoles] = useState([])
  const [loadingRoles, setLoadingRoles] = useState(true)
  const [selectedRole, setSelectedRole] = useState(null)

  // Modal nouveau rôle
  const [showRoleModal, setShowRoleModal] = useState(false)
  const [roleForm, setRoleForm] = useState(EMPTY_ROLE_FORM)
  const [savingRole, setSavingRole] = useState(false)
  const [roleFormError, setRoleFormError] = useState(null)

  // Permissions — DWH
  const [permDwhInput, setPermDwhInput] = useState('')
  const [permDwhList, setPermDwhList] = useState([])
  const [savingDwh, setSavingDwh] = useState(false)
  const [availableDwh, setAvailableDwh] = useState([])         // liste DWH depuis l'API
  const [availableReports, setAvailableReports] = useState({   // rapports par type
    dashboards: [], gridviews: [], pivots: []
  })

  // Permissions — Rapports
  const [reportTab, setReportTab] = useState('dashboards')
  const [reportsByType, setReportsByType] = useState({ dashboards: [], gridviews: [], pivots: [] })
  const [newReportForm, setNewReportForm] = useState({ id: '', name: '', can_view: true, can_export: false, can_schedule: false })
  const [showAddReport, setShowAddReport] = useState(false)
  const [savingReport, setSavingReport] = useState(false)
  const [reportSearch, setReportSearch] = useState('')

  // Permissions — Colonnes masquées
  const [maskReportId, setMaskReportId] = useState('')
  const [maskColumns, setMaskColumns] = useState('')   // gardé pour fallback
  const [savingMasks, setSavingMasks] = useState(false)
  const [reportColumns, setReportColumns] = useState([])     // colonnes du rapport sélectionné
  const [loadingColumns, setLoadingColumns] = useState(false)
  const [checkedColumns, setCheckedColumns] = useState({})

  // Utilisateurs
  const [users, setUsers] = useState([])
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [assignDropdown, setAssignDropdown] = useState(null) // user id with open dropdown

  // Fonctionnalités
  const [featureCodes, setFeatureCodes]           = useState([])       // codes activés pour le rôle sélectionné
  const [savingFeatures, setSavingFeatures]       = useState(false)
  const [expandedCats, setExpandedCats]           = useState({})       // catégories ouvertes/fermées

  // Seed standard
  const [seedingStandard, setSeedingStandard] = useState(false)

  // Notifications
  const [toast, setToast] = useState(null)
  const [globalError, setGlobalError] = useState(null)

  // ── Toast helper ─────────────────────────────────────────────────────────────
  const showToast = useCallback((msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }, [])

  // ── Chargement rôles ─────────────────────────────────────────────────────────
  const loadRoles = useCallback(async () => {
    if (!dwhCode) { setRoles([]); setLoadingRoles(false); return }
    setLoadingRoles(true)
    setGlobalError(null)
    try {
      const res = await api.get('/roles', { headers })
      setRoles(res.data?.data || [])
    } catch (e) {
      setGlobalError(extractError(e, 'Impossible de charger les rôles'))
    } finally {
      setLoadingRoles(false)
    }
  }, [dwhCode])

  useEffect(() => { loadRoles() }, [loadRoles])

  // Charger DWH + rapports disponibles
  useEffect(() => {
    const loadResources = async () => {
      // DWH
      try {
        const res = await api.get('/dwh-admin/list', { headers })
        setAvailableDwh(res.data?.data || [])
      } catch { /* silencieux */ }

      // Rapports (dashboards, gridviews, pivots)
      try {
        const [dashRes, gvRes, pivRes] = await Promise.allSettled([
          api.get('/builder/dashboards', { headers }),
          api.get('/gridview/grids',     { headers }),
          api.get('/v2/pivots',          { headers }),
        ])
        setAvailableReports({
          dashboards: dashRes.status === 'fulfilled' ? (dashRes.value.data?.data || []) : [],
          gridviews:  gvRes.status  === 'fulfilled' ? (gvRes.value.data?.data  || []) : [],
          pivots:     pivRes.status === 'fulfilled' ? (pivRes.value.data?.data  || []) : [],
        })
      } catch { /* silencieux */ }
    }
    loadResources()
  }, [dwhCode])

  // ── Chargement permissions du rôle sélectionné ───────────────────────────────
  const loadRolePermissions = useCallback(async (role) => {
    if (!role) return
    try {
      const [dwhRes, reportsRes, featuresRes] = await Promise.all([
        api.get(`/roles/${role.id}/dwh`, { headers }),
        api.get(`/roles/${role.id}/reports`, { headers }),
        api.get(`/roles/${role.id}/features`, { headers }),
      ])
      // DWH — extraire dwh_code depuis les objets {id, dwh_code}
      const dwhRaw = dwhRes.data?.data || []
      setPermDwhList(dwhRaw.map(d => typeof d === 'string' ? d : d.dwh_code))
      // Rapports — grouper par type (dashboard/gridview/pivot → pluriel)
      const reports = reportsRes.data?.data || []
      const toItem = r => ({
        id:          String(r.report_id),
        report_type: r.report_type,                    // conservé pour le lookup à l'affichage
        name:        `${r.report_type} #${r.report_id}`, // fallback si availableReports pas encore chargé
        can_view:    r.can_view,
        can_export:  r.can_export,
        can_schedule: r.can_schedule,
      })
      setReportsByType({
        dashboards: reports.filter(r => r.report_type === 'dashboard').map(toItem),
        gridviews:  reports.filter(r => r.report_type === 'gridview').map(toItem),
        pivots:     reports.filter(r => r.report_type === 'pivot').map(toItem),
      })
      setFeatureCodes(featuresRes.data?.data || [])
    } catch {
      setPermDwhList([])
      setReportsByType({ dashboards: [], gridviews: [], pivots: [] })
      setFeatureCodes([])
    }
  }, [dwhCode])

  useEffect(() => {
    if (selectedRole) loadRolePermissions(selectedRole)
  }, [selectedRole, loadRolePermissions])

  // ── Chargement utilisateurs ──────────────────────────────────────────────────
  const loadUsers = useCallback(async () => {
    setLoadingUsers(true)
    try {
      const res = await api.get('/client-admin/users', { headers })
      setUsers(res.data?.data || res.data || [])
    } catch (e) {
      setGlobalError(extractError(e, 'Impossible de charger les utilisateurs'))
    } finally {
      setLoadingUsers(false)
    }
  }, [dwhCode])

  useEffect(() => {
    if (activeTab === 'users') loadUsers()
  }, [activeTab, loadUsers])

  // ─────────────────────────────────────────────────────────────────────────────
  // ONGLET 1 — RÔLES
  // ─────────────────────────────────────────────────────────────────────────────

  const openRoleModal = () => {
    setRoleForm(EMPTY_ROLE_FORM)
    setRoleFormError(null)
    setShowRoleModal(true)
  }

  const closeRoleModal = () => {
    setShowRoleModal(false)
    setRoleFormError(null)
  }

  const handleCreateRole = async (e) => {
    e.preventDefault()
    if (!roleForm.nom.trim()) {
      setRoleFormError('Le nom du rôle est obligatoire')
      return
    }
    setSavingRole(true)
    setRoleFormError(null)
    try {
      await api.post('/roles', { nom: roleForm.nom, description: roleForm.description, couleur: roleForm.couleur, is_admin: roleForm.is_admin }, { headers })
      showToast('Rôle créé avec succès')
      closeRoleModal()
      loadRoles()
    } catch (e) {
      setRoleFormError(extractError(e, 'Erreur lors de la création'))
    } finally {
      setSavingRole(false)
    }
  }

  const handleDeleteRole = async (role) => {
    if (!window.confirm(`Supprimer le rôle "${role.nom}" ? Cette action est irréversible.`)) return
    try {
      await api.delete(`/roles/${role.id}`, { headers })
      showToast('Rôle supprimé')
      if (selectedRole?.id === role.id) setSelectedRole(null)
      loadRoles()
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur lors de la suppression'))
    }
  }

  const handleSelectRole = (role) => {
    setSelectedRole(role)
    setMaskReportId('')
    setMaskColumns('')
    setShowAddReport(false)
    setActiveTab('permissions')
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ONGLET 2 — PERMISSIONS
  // ─────────────────────────────────────────────────────────────────────────────

  // Section A — DWH
  const handleAddDwh = () => {
    const code = permDwhInput.trim()
    if (!code || permDwhList.includes(code)) return
    setPermDwhList(prev => [...prev, code])
    setPermDwhInput('')
  }

  const handleRemoveDwh = (code) => {
    setPermDwhList(prev => prev.filter(c => c !== code))
  }

  const handleSaveDwh = async () => {
    if (!selectedRole) return
    setSavingDwh(true)
    try {
      await api.post(
        `/roles/${selectedRole.id}/dwh`,
        { dwh_codes: permDwhList },
        { headers }
      )
      showToast('DWH enregistrés')
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur enregistrement DWH'))
    } finally {
      setSavingDwh(false)
    }
  }

  // Section B — Rapports
  // Map clé plurielle → type singulier pour l'API
  const typeMap = { dashboards: 'dashboard', gridviews: 'gridview', pivots: 'pivot' }

  const handleAddReport = async (e) => {
    e.preventDefault()
    if (!newReportForm.id) return
    setSavingReport(true)
    try {
      await api.post(
        `/roles/${selectedRole.id}/reports`,
        { report_type: typeMap[reportTab], report_id: parseInt(newReportForm.id), can_view: newReportForm.can_view, can_export: newReportForm.can_export, can_schedule: newReportForm.can_schedule },
        { headers }
      )
      const selectedReport = availableReports[reportTab]?.find(r => String(r.id) === String(newReportForm.id))
      const newItem = { ...newReportForm, name: selectedReport?.nom || newReportForm.name || `#${newReportForm.id}` }
      setReportsByType(prev => ({ ...prev, [reportTab]: [...(prev[reportTab] || []), newItem] }))
      setNewReportForm({ id: '', name: '', can_view: true, can_export: false, can_schedule: false })
      setShowAddReport(false)
      showToast('Rapport ajouté')
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur ajout rapport'))
    } finally {
      setSavingReport(false)
    }
  }

  const handleRemoveReport = async (type, reportId) => {
    try {
      await api.delete(`/roles/${selectedRole.id}/reports/${typeMap[type]}/${reportId}`, { headers })
      setReportsByType(prev => ({ ...prev, [type]: (prev[type] || []).filter(r => r.id !== reportId) }))
      showToast('Rapport retiré')
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur suppression rapport'))
    }
  }

  const handleToggleReportPerm = async (type, reportId, perm) => {
    const updated = (reportsByType[type] || []).map(r =>
      r.id === reportId ? { ...r, [perm]: !r[perm] } : r
    )
    setReportsByType(prev => ({ ...prev, [type]: updated }))
    try {
      const item = updated.find(r => r.id === reportId)
      await api.post(
        `/roles/${selectedRole.id}/reports`,
        { report_type: typeMap[type], report_id: parseInt(reportId), can_view: item.can_view, can_export: item.can_export, can_schedule: item.can_schedule },
        { headers }
      )
    } catch (e) {
      setReportsByType(prev => ({ ...prev, [type]: reportsByType[type] }))
      setGlobalError(extractError(e, 'Erreur mise à jour permission'))
    }
  }

  // Helper — résout le vrai nom d'un rapport depuis availableReports
  // reportType : 'dashboard' | 'gridview' | 'pivot'   (singulier, comme stocké dans APP_Role_Reports)
  // reportId   : number | string
  const getReportName = (reportType, reportId) => {
    const typeKey = reportType === 'dashboard' ? 'dashboards'
                  : reportType === 'gridview'  ? 'gridviews'
                  : reportType === 'pivot'     ? 'pivots'
                  : reportType  // clé directe si déjà au pluriel
    const list = availableReports[typeKey] || []
    const found = list.find(x => String(x.id) === String(reportId))
    return found?.nom || found?.name || `${reportType} #${reportId}`
  }

  // Tous les rapports toutes sections confondues (pour le sélecteur de masques)
  const allReports = [
    ...(reportsByType.dashboards || []).map(r => ({ ...r, type: 'dashboards' })),
    ...(reportsByType.gridviews || []).map(r => ({ ...r, type: 'gridviews' })),
    ...(reportsByType.pivots || []).map(r => ({ ...r, type: 'pivots' })),
  ]

  // Section C — Colonnes masquées

  // Charger les colonnes du rapport sélectionné + pré-cocher celles déjà masquées
  const loadReportColumns = useCallback(async (reportKey) => {
    if (!reportKey) { setReportColumns([]); setCheckedColumns({}); return }
    const [rType, rId] = reportKey.split(':')
    const singularType = { dashboards: 'dashboard', gridviews: 'gridview', pivots: 'pivot' }[rType] || rType
    setLoadingColumns(true)
    setReportColumns([])
    try {
      // ── 1. Charger la liste des colonnes disponibles ──────────────────────
      let cols = []
      if (rType === 'gridviews') {
        const res = await api.get(`/gridview/grids/${rId}`, { headers })
        const grid = res.data?.data || res.data || {}
        cols = (grid.columns || []).map(c => ({ field: c.field, label: c.header || c.field }))
      } else if (rType === 'pivots') {
        const res = await api.get(`/v2/pivots/${rId}`, { headers })
        const piv = res.data?.data || res.data || {}
        const rows    = Array.isArray(piv.rows_config)    ? piv.rows_config    : JSON.parse(piv.rows_config    || '[]')
        const colsCfg = Array.isArray(piv.columns_config) ? piv.columns_config : JSON.parse(piv.columns_config || '[]')
        cols = [...rows, ...colsCfg].map(c => ({ field: c.field || c, label: c.label || c.field || c }))
      } else if (rType === 'dashboards') {
        const res = await api.get(`/builder/dashboards/${rId}`, { headers })
        const dash = res.data?.data || res.data || {}
        const widgets = Array.isArray(dash.widgets) ? dash.widgets : JSON.parse(dash.widgets || '[]')
        const fieldsSet = new Set()
        widgets.forEach(w => {
          const cfg = typeof w.config === 'string' ? JSON.parse(w.config || '{}') : (w.config || {})
          ;(cfg.columns || cfg.fields || []).forEach(f => fieldsSet.add(typeof f === 'string' ? f : f.field))
        })
        cols = [...fieldsSet].map(f => ({ field: f, label: f }))
      }
      setReportColumns(cols)

      // ── 2. Charger les colonnes DÉJÀ masquées depuis l'API ────────────────
      const init = {}
      cols.forEach(c => { init[c.field] = false })

      if (selectedRole) {
        try {
          const maskRes = await api.get(`/roles/${selectedRole.id}/columns`, { headers })
          const saved   = maskRes.data?.data || []
          saved
            .filter(m =>
              m.report_type === singularType &&
              String(m.report_id) === String(rId) &&
              m.is_hidden
            )
            .forEach(m => {
              if (m.column_name in init) init[m.column_name] = true
            })
        } catch { /* silencieux — aucune colonne masquée enregistrée */ }
      }

      setCheckedColumns(init)
    } catch { setReportColumns([]) }
    finally { setLoadingColumns(false) }
  }, [dwhCode, selectedRole])

  const handleMaskReportChange = (val) => {
    setMaskReportId(val)
    loadReportColumns(val)
  }

  const toggleColumn = (field) => {
    setCheckedColumns(prev => ({ ...prev, [field]: !prev[field] }))
  }

  const handleSaveMasks = async () => {
    if (!maskReportId) return
    setSavingMasks(true)
    const [rType, rId] = maskReportId.split(':')
    // Si colonnes chargées → utiliser les cases cochées, sinon fallback textarea
    const cols = reportColumns.length > 0
      ? Object.entries(checkedColumns).filter(([, v]) => v).map(([k]) => k)
      : maskColumns.split('\n').map(c => c.trim()).filter(Boolean)
    try {
      await api.post(
        `/roles/${selectedRole.id}/columns`,
        { report_type: typeMap[rType] || rType, report_id: parseInt(rId), hidden_columns: cols },
        { headers }
      )
      showToast(`${cols.length} colonne(s) masquée(s) enregistrée(s)`)
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur enregistrement masques'))
    } finally {
      setSavingMasks(false)
    }
  }

  // Section D — Fonctionnalités
  const isFeatureEnabled = (code) => featureCodes.includes(code)

  const toggleFeature = (code) => {
    setFeatureCodes(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    )
  }

  const toggleCategoryAll = (cat) => {
    const codes = cat.features.map(f => f.code)
    const allOn = codes.every(c => featureCodes.includes(c))
    if (allOn) {
      setFeatureCodes(prev => prev.filter(c => !codes.includes(c)))
    } else {
      setFeatureCodes(prev => [...new Set([...prev, ...codes])])
    }
  }

  const handleSaveFeatures = async () => {
    if (!selectedRole) return
    setSavingFeatures(true)
    try {
      await api.post(`/roles/${selectedRole.id}/features`, { feature_codes: featureCodes }, { headers })
      showToast(`${featureCodes.length} fonctionnalité(s) enregistrée(s)`)
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur enregistrement fonctionnalités'))
    } finally {
      setSavingFeatures(false)
    }
  }

  const toggleExpandCat = (id) => setExpandedCats(prev => ({ ...prev, [id]: !prev[id] }))

  // ─────────────────────────────────────────────────────────────────────────────
  // ONGLET 3 — UTILISATEURS
  // ─────────────────────────────────────────────────────────────────────────────

  const handleSeedStandard = async () => {
    setSeedingStandard(true)
    try {
      const res = await api.post('/roles/seed-standard', {}, { headers })
      showToast(res.data?.message || 'Rôles standard créés')
      loadRoles()
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur création rôles standard'))
    } finally {
      setSeedingStandard(false)
    }
  }

  const handleAssignRole = async (userId, roleId) => {
    try {
      await api.post(
        `/users/${userId}/roles`,
        { role_id: roleId },
        { headers }
      )
      showToast('Rôle assigné')
      setAssignDropdown(null)
      loadUsers()
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur assignation rôle'))
    }
  }

  const handleRemoveUserRole = async (userId, roleId) => {
    try {
      await api.delete(
        `/users/${userId}/roles/${roleId}`,
        { headers }
      )
      showToast('Rôle retiré')
      loadUsers()
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur suppression rôle'))
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDU
  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <div className="p-6 space-y-6 min-h-screen bg-gray-50 dark:bg-gray-900">

      {/* ── En-tête ───────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Gestion des rôles</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Définissez les rôles, permissions et accès des utilisateurs
            </p>
          </div>
        </div>
        <button
          onClick={loadRoles}
          className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
          title="Actualiser"
        >
          <RefreshCw className={`w-4 h-4 ${loadingRoles ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* ── Notifications globales ────────────────────────────────────────────── */}
      {globalError && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="flex-1">{globalError}</span>
          <button onClick={() => setGlobalError(null)}><X className="w-4 h-4" /></button>
        </div>
      )}

      {/* ── Toast ────────────────────────────────────────────────────────────── */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm font-medium
          ${toast.type === 'success'
            ? 'bg-green-50 dark:bg-green-900/80 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-700'
            : 'bg-red-50 dark:bg-red-900/80 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-700'
          }`}
        >
          {toast.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {toast.msg}
        </div>
      )}

      {/* ── Navigation onglets ───────────────────────────────────────────────── */}
      <div className="flex gap-1 bg-white dark:bg-gray-800 rounded-xl p-1 border border-gray-200 dark:border-gray-700 w-fit">
        {[
          { key: 'roles', label: 'Rôles', icon: Shield },
          { key: 'permissions', label: selectedRole ? `Permissions: ${selectedRole.nom}` : 'Permissions', icon: Key, disabled: !selectedRole },
          { key: 'users', label: 'Utilisateurs', icon: Users },
        ].map(({ key, label, icon: Icon, disabled }) => (
          <button
            key={key}
            onClick={() => !disabled && setActiveTab(key)}
            disabled={disabled}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
              ${activeTab === key
                ? 'bg-blue-600 text-white shadow-sm'
                : disabled
                  ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ONGLET 1 — RÔLES                                                      */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'roles' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-800 dark:text-gray-100">Rôles définis</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={handleSeedStandard}
                disabled={seedingStandard || !dwhCode}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                title="Insère les rôles standard manquants (Commercial, Finance, Direction…)"
              >
                {seedingStandard ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                Rôles standard
              </button>
              <button
                onClick={openRoleModal}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                Nouveau rôle
              </button>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
            {loadingRoles ? (
              <div className="flex items-center justify-center h-40 text-gray-400">
                <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement...
              </div>
            ) : !dwhCode ? (
              <div className="flex flex-col items-center justify-center h-40 text-gray-400 gap-2">
                <Database className="w-10 h-10 opacity-30" />
                <p className="text-sm">Sélectionnez un DWH pour gérer les rôles</p>
              </div>
            ) : roles.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 text-gray-400 gap-2">
                <Shield className="w-10 h-10 opacity-30" />
                <p className="text-sm">Aucun rôle configuré</p>
                <button onClick={openRoleModal} className="text-blue-500 text-sm hover:underline">
                  Créer le premier rôle
                </button>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Rôle</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Description</th>
                    <th className="px-4 py-3 text-center font-medium text-gray-600 dark:text-gray-300">Utilisateurs</th>
                    <th className="px-4 py-3 text-center font-medium text-gray-600 dark:text-gray-300">Admin</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {roles.map(role => (
                    <tr
                      key={role.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700/30 cursor-pointer group"
                      onClick={() => handleSelectRole(role)}
                    >
                      <td className="px-4 py-3">
                        <span
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
                          style={colorBadgeStyle(role.couleur || '#3B82F6')}
                        >
                          <span
                            className="w-2 h-2 rounded-full inline-block"
                            style={{ backgroundColor: role.couleur || '#3B82F6' }}
                          />
                          {role.nom}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500 dark:text-gray-400">
                        {role.description || <span className="italic opacity-50">—</span>}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="inline-flex items-center gap-1 text-gray-600 dark:text-gray-300">
                          <Users className="w-3.5 h-3.5" />
                          {role.users_count ?? 0}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {role.is_admin && (
                          <span className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-xs rounded-full font-medium">
                            Admin
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={e => { e.stopPropagation(); handleSelectRole(role) }}
                            className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                            title="Configurer les permissions"
                          >
                            <Settings className="w-4 h-4" />
                          </button>
                          <button
                            onClick={e => { e.stopPropagation(); handleDeleteRole(role) }}
                            className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                            title="Supprimer ce rôle"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                          <ChevronRight className="w-4 h-4 text-gray-300 dark:text-gray-600 group-hover:text-blue-500 transition-colors" />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ONGLET 2 — PERMISSIONS                                                */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'permissions' && selectedRole && (
        <div className="space-y-5">

          {/* Breadcrumb rôle */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('roles')}
              className="text-sm text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400"
            >
              Rôles
            </button>
            <ChevronRight className="w-4 h-4 text-gray-400" />
            <span
              className="text-sm font-semibold px-2.5 py-1 rounded-full"
              style={colorBadgeStyle(selectedRole.color || '#3B82F6')}
            >
              {selectedRole.nom}
            </span>
          </div>

          {/* ── Section A — DWH autorisés ─────────────────────────────────────── */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 space-y-4">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold text-gray-800 dark:text-gray-100">DWH autorisés</h3>
            </div>

            {/* Tags DWH existants */}
            <div className="flex flex-wrap gap-2 min-h-[36px]">
              {permDwhList.length === 0 ? (
                <span className="text-xs text-gray-400 italic">Aucun DWH assigné — accès universel</span>
              ) : (
                permDwhList.map(code => (
                  <span key={code} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 text-xs rounded-full border border-blue-200 dark:border-blue-700">
                    <Database className="w-3 h-3" />
                    {code}
                    <button onClick={() => handleRemoveDwh(code)} className="hover:text-red-500">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))
              )}
            </div>

            {/* Ajouter un DWH — combobox */}
            <div className="flex gap-2">
              {availableDwh.length > 0 ? (
                <select
                  value={permDwhInput}
                  onChange={e => setPermDwhInput(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">— Sélectionner un DWH —</option>
                  {availableDwh
                    .filter(d => !permDwhList.includes(d.code || d))
                    .map(d => (
                      <option key={d.code || d} value={d.code || d}>
                        {d.code || d}{d.nom ? ` — ${d.nom}` : ''}
                      </option>
                    ))}
                </select>
              ) : (
                <input
                  value={permDwhInput}
                  onChange={e => setPermDwhInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), handleAddDwh())}
                  placeholder="Code DWH (ex: CLIENT01)"
                  className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              )}
              <button
                onClick={handleAddDwh}
                disabled={!permDwhInput}
                className="px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-40 text-sm"
              >
                <Plus className="w-4 h-4" />
              </button>
              <button
                onClick={handleSaveDwh}
                disabled={savingDwh}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium disabled:opacity-60"
              >
                {savingDwh ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Enregistrer DWH
              </button>
            </div>
          </div>

          {/* ── Section B — Rapports autorisés ───────────────────────────────── */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 space-y-4">
            <div className="flex items-center gap-2">
              <LayoutDashboard className="w-5 h-5 text-purple-500" />
              <h3 className="font-semibold text-gray-800 dark:text-gray-100">Rapports autorisés</h3>
            </div>

            {/* Sous-onglets type de rapport */}
            <div className="flex gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-1 w-fit">
              {REPORT_TYPES.map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => { setReportTab(key); setShowAddReport(false) }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all
                    ${reportTab === key
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                    }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                  <span className="ml-0.5 px-1.5 py-0.5 bg-gray-200 dark:bg-gray-500 rounded-full text-xs leading-none">
                    {(reportsByType[key] || []).length}
                  </span>
                </button>
              ))}
            </div>

            {/* Liste des rapports */}
            {(reportsByType[reportTab] || []).length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-gray-400 gap-2">
                <LayoutDashboard className="w-8 h-8 opacity-30" />
                <p className="text-sm">Aucun rapport assigné pour ce type</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700/40 border-b border-gray-200 dark:border-gray-700">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-gray-600 dark:text-gray-300">ID</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600 dark:text-gray-300">Nom</th>
                    <th className="px-3 py-2 text-center font-medium text-gray-600 dark:text-gray-300">
                      <span className="flex items-center justify-center gap-1"><Eye className="w-3.5 h-3.5" /> Voir</span>
                    </th>
                    <th className="px-3 py-2 text-center font-medium text-gray-600 dark:text-gray-300">Exporter</th>
                    <th className="px-3 py-2 text-center font-medium text-gray-600 dark:text-gray-300">Planifier</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-600 dark:text-gray-300"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {(reportsByType[reportTab] || []).map(report => (
                    <tr key={report.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                      <td className="px-3 py-2 font-mono text-xs text-gray-500 dark:text-gray-400">#{report.id}</td>
                      <td className="px-3 py-2 text-gray-800 dark:text-gray-200 font-medium">
                        {getReportName(report.report_type, report.id)}
                      </td>
                      {['can_view', 'can_export', 'can_schedule'].map(perm => (
                        <td key={perm} className="px-3 py-2 text-center">
                          <button
                            onClick={() => handleToggleReportPerm(reportTab, report.id, perm)}
                            className={`w-5 h-5 rounded flex items-center justify-center mx-auto transition-colors
                              ${report[perm]
                                ? 'bg-green-500 text-white'
                                : 'bg-gray-200 dark:bg-gray-600 text-gray-400'
                              }`}
                          >
                            {report[perm] && <Check className="w-3 h-3" />}
                          </button>
                        </td>
                      ))}
                      <td className="px-3 py-2 text-right">
                        <button
                          onClick={() => handleRemoveReport(reportTab, report.id)}
                          className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {/* Formulaire ajout rapport */}
            {showAddReport ? (
              <form onSubmit={handleAddReport} className="border border-dashed border-blue-300 dark:border-blue-700 rounded-lg p-4 space-y-3 bg-blue-50/50 dark:bg-blue-900/10">
                <p className="text-xs font-medium text-blue-700 dark:text-blue-300">Ajouter un rapport ({REPORT_TYPES.find(r => r.key === reportTab)?.label})</p>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                    Rapport *
                  </label>
                  {availableReports[reportTab]?.length > 0 ? (
                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                      {/* Barre de recherche */}
                      <div className="flex items-center gap-2 px-2 py-1.5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                        <svg className="w-3.5 h-3.5 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                        </svg>
                        <input
                          type="text"
                          value={reportSearch}
                          onChange={e => setReportSearch(e.target.value)}
                          placeholder="Rechercher un rapport..."
                          className="flex-1 text-xs bg-transparent outline-none text-gray-700 dark:text-gray-300 placeholder-gray-400"
                        />
                        {reportSearch && (
                          <button type="button" onClick={() => setReportSearch('')} className="text-gray-400 hover:text-gray-600">
                            <X className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                      {/* Grille des rapports */}
                      <div className="max-h-52 overflow-y-auto">
                        <table className="w-full text-xs">
                          <thead className="bg-gray-50 dark:bg-gray-700/60 sticky top-0 z-10">
                            <tr>
                              <th className="px-2 py-1.5 text-left font-medium text-gray-500 dark:text-gray-400 w-14">ID</th>
                              <th className="px-2 py-1.5 text-left font-medium text-gray-500 dark:text-gray-400">Nom</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100 dark:divide-gray-700/50">
                            {availableReports[reportTab]
                              .filter(r => !(reportsByType[reportTab] || []).some(x => String(x.id) === String(r.id)))
                              .filter(r =>
                                !reportSearch ||
                                r.nom.toLowerCase().includes(reportSearch.toLowerCase()) ||
                                String(r.id).includes(reportSearch)
                              )
                              .map(r => (
                                <tr
                                  key={r.id}
                                  onClick={() => {
                                    setNewReportForm(f => ({ ...f, id: String(r.id), name: r.nom }))
                                    setReportSearch('')
                                  }}
                                  className={`cursor-pointer transition-colors
                                    ${String(newReportForm.id) === String(r.id)
                                      ? 'bg-blue-50 dark:bg-blue-900/30'
                                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/30'
                                    }`}
                                >
                                  <td className="px-2 py-1.5 font-mono text-gray-400 dark:text-gray-500">#{r.id}</td>
                                  <td className={`px-2 py-1.5 font-medium
                                    ${String(newReportForm.id) === String(r.id)
                                      ? 'text-blue-700 dark:text-blue-300'
                                      : 'text-gray-700 dark:text-gray-300'
                                    }`}>
                                    {r.nom}
                                    {String(newReportForm.id) === String(r.id) && (
                                      <Check className="w-3 h-3 inline ml-1.5 text-blue-500" />
                                    )}
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                      {/* Rapport sélectionné */}
                      {newReportForm.id && (
                        <div className="px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border-t border-blue-100 dark:border-blue-800 flex items-center justify-between">
                          <span className="text-xs text-blue-700 dark:text-blue-300 font-medium">
                            Sélectionné : #{newReportForm.id} — {newReportForm.name}
                          </span>
                          <button type="button" onClick={() => setNewReportForm(f => ({ ...f, id: '', name: '' }))}
                            className="text-blue-400 hover:text-blue-600">
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <input
                      value={newReportForm.id}
                      onChange={e => setNewReportForm(f => ({ ...f, id: e.target.value }))}
                      placeholder="ID du rapport (ex: 42)"
                      required
                      className="w-full px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                    />
                  )}
                </div>
                <div className="flex items-center gap-5">
                  {[
                    { key: 'can_view', label: 'Voir' },
                    { key: 'can_export', label: 'Exporter' },
                    { key: 'can_schedule', label: 'Planifier' },
                  ].map(({ key, label }) => (
                    <label key={key} className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 dark:text-gray-300">
                      <input
                        type="checkbox"
                        checked={newReportForm[key]}
                        onChange={e => setNewReportForm(f => ({ ...f, [key]: e.target.checked }))}
                        className="rounded border-gray-300 text-blue-600"
                      />
                      {label}
                    </label>
                  ))}
                </div>
                <div className="flex gap-2 pt-1">
                  <button
                    type="submit"
                    disabled={savingReport}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg disabled:opacity-60"
                  >
                    {savingReport ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                    Ajouter
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAddReport(false)}
                    className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    Annuler
                  </button>
                </div>
              </form>
            ) : (
              <button
                onClick={() => setShowAddReport(true)}
                className="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-500 dark:text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors w-full justify-center"
              >
                <Plus className="w-4 h-4" />
                Ajouter un rapport
              </button>
            )}
          </div>

          {/* ── Section C — Colonnes masquées ────────────────────────────────── */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 space-y-4">
            <div className="flex items-center gap-2">
              <EyeOff className="w-5 h-5 text-orange-500" />
              <h3 className="font-semibold text-gray-800 dark:text-gray-100">Colonnes masquées</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Pour quel rapport ?
                </label>
                <select
                  value={maskReportId}
                  onChange={e => handleMaskReportChange(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                >
                  <option value="">— Choisir un rapport —</option>
                  {allReports.map(r => (
                    <option key={`${r.type}:${r.id}`} value={`${r.type}:${r.id}`}>
                      [{REPORT_TYPES.find(t => t.key === r.type)?.label}] {getReportName(r.type, r.id)}
                    </option>
                  ))}
                </select>
                {allReports.length === 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                    Ajoutez d'abord des rapports dans la section ci-dessus.
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Colonnes à masquer
                </label>

                {/* Spinner chargement */}
                {loadingColumns && (
                  <div className="flex items-center gap-2 text-sm text-gray-400 py-4">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Chargement des colonnes…
                  </div>
                )}

                {/* Grille de cases à cocher */}
                {!loadingColumns && reportColumns.length > 0 && (
                  <div className="border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 dark:bg-gray-700/50 px-3 py-1.5 flex items-center justify-between border-b border-gray-200 dark:border-gray-600">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {reportColumns.length} colonne(s) — {Object.values(checkedColumns).filter(Boolean).length} masquée(s)
                      </span>
                      <div className="flex gap-3">
                        <button
                          type="button"
                          onClick={() => {
                            const all = {}
                            reportColumns.forEach(c => { all[c.field] = true })
                            setCheckedColumns(all)
                          }}
                          className="text-xs text-orange-600 hover:underline"
                        >
                          Tout masquer
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            const none = {}
                            reportColumns.forEach(c => { none[c.field] = false })
                            setCheckedColumns(none)
                          }}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Tout afficher
                        </button>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-0 max-h-56 overflow-y-auto">
                      {reportColumns.map(col => (
                        <label
                          key={col.field}
                          className={`flex items-center gap-2 px-3 py-2 cursor-pointer text-sm border-b border-r border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors ${
                            checkedColumns[col.field]
                              ? 'bg-orange-50 dark:bg-orange-900/10 text-orange-700 dark:text-orange-300'
                              : 'text-gray-700 dark:text-gray-300'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={!!checkedColumns[col.field]}
                            onChange={() => toggleColumn(col.field)}
                            className="rounded border-gray-300 text-orange-500 focus:ring-orange-400"
                          />
                          <span className="truncate" title={col.field}>
                            {col.label !== col.field ? (
                              <><span className="font-medium">{col.label}</span><span className="ml-1 text-xs text-gray-400">({col.field})</span></>
                            ) : col.field}
                          </span>
                          {checkedColumns[col.field] && <EyeOff className="w-3.5 h-3.5 ml-auto flex-shrink-0" />}
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {/* Fallback textarea si pas de colonnes détectées */}
                {!loadingColumns && reportColumns.length === 0 && (
                  <textarea
                    value={maskColumns}
                    onChange={e => setMaskColumns(e.target.value)}
                    disabled={!maskReportId}
                    placeholder={"colonne_montant\ncolonne_marge\ncolonne_client"}
                    rows={4}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm font-mono resize-y disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                )}
              </div>
            </div>

            {/* Aperçu colonnes masquées (fallback textarea) */}
            {!loadingColumns && reportColumns.length === 0 && maskColumns && maskReportId && (
              <div className="flex flex-wrap gap-1">
                {maskColumns.split('\n').filter(c => c.trim()).map(col => (
                  <span key={col} className="inline-flex items-center gap-1 px-2 py-0.5 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 text-xs rounded border border-orange-200 dark:border-orange-700">
                    <EyeOff className="w-3 h-3" />
                    {col.trim()}
                  </span>
                ))}
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={handleSaveMasks}
                disabled={savingMasks || !maskReportId}
                className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white text-sm rounded-lg disabled:opacity-50"
              >
                {savingMasks ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Enregistrer les masques
              </button>
            </div>
          </div>

          {/* ── Section D — Fonctionnalités OptiBoard ────────────────────────── */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-violet-500" />
                <h3 className="font-semibold text-gray-800 dark:text-gray-100">Fonctionnalités OptiBoard</h3>
                <span className="px-2 py-0.5 text-xs rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 font-medium">
                  {featureCodes.length} / {ALL_FEATURE_CODES.length} activées
                </span>
              </div>
              <div className="flex items-center gap-2">
                {selectedRole?.is_admin && (
                  <span className="text-xs text-amber-600 dark:text-amber-400 font-medium flex items-center gap-1">
                    <Unlock className="w-3.5 h-3.5" />
                    Administrateur — accès total
                  </span>
                )}
                <button
                  onClick={() => setFeatureCodes(ALL_FEATURE_CODES)}
                  className="text-xs text-violet-600 hover:underline"
                >
                  Tout activer
                </button>
                <span className="text-gray-300 dark:text-gray-600">|</span>
                <button
                  onClick={() => setFeatureCodes([])}
                  className="text-xs text-gray-400 hover:underline"
                >
                  Tout désactiver
                </button>
              </div>
            </div>

            {/* Catégories */}
            <div className="space-y-3">
              {FEATURE_CATEGORIES.map(cat => {
                const Icon = cat.icon
                const isExpanded = expandedCats[cat.id] !== false  // ouvert par défaut
                const catCodes = cat.features.map(f => f.code)
                const enabledCount = catCodes.filter(c => featureCodes.includes(c)).length
                const allEnabled = enabledCount === catCodes.length
                const someEnabled = enabledCount > 0 && !allEnabled

                return (
                  <div key={cat.id} className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                    {/* En-tête catégorie */}
                    <div
                      className="flex items-center justify-between px-4 py-3 cursor-pointer select-none hover:bg-gray-50 dark:hover:bg-gray-700/40"
                      onClick={() => toggleExpandCat(cat.id)}
                      style={{ borderLeft: `4px solid ${cat.color}` }}
                    >
                      <div className="flex items-center gap-3">
                        <Icon className="w-4 h-4" style={{ color: cat.color }} />
                        <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">{cat.label}</span>
                        <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                          style={{ backgroundColor: cat.color + '20', color: cat.color }}>
                          {enabledCount}/{catCodes.length}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        {/* Toggle tout la catégorie */}
                        <button
                          type="button"
                          onClick={e => { e.stopPropagation(); toggleCategoryAll(cat) }}
                          className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors ${
                            allEnabled
                              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200'
                              : someEnabled
                                ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 hover:bg-yellow-200'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200'
                          }`}
                        >
                          {allEnabled ? 'Tout désactiver' : 'Tout activer'}
                        </button>
                        {isExpanded
                          ? <ChevronUp className="w-4 h-4 text-gray-400" />
                          : <ChevronDown className="w-4 h-4 text-gray-400" />
                        }
                      </div>
                    </div>

                    {/* Features de la catégorie */}
                    {isExpanded && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-0 divide-y divide-x-0 sm:divide-x divide-gray-100 dark:divide-gray-700/50">
                        {cat.features.map(feat => {
                          const enabled = featureCodes.includes(feat.code)
                          return (
                            <label
                              key={feat.code}
                              className={`flex items-start gap-3 p-3 cursor-pointer transition-colors border-b border-gray-100 dark:border-gray-700/50 ${
                                enabled
                                  ? 'bg-green-50/60 dark:bg-green-900/10'
                                  : 'hover:bg-gray-50 dark:hover:bg-gray-700/20'
                              }`}
                            >
                              {/* Toggle switch */}
                              <div className="relative shrink-0 mt-0.5" onClick={() => toggleFeature(feat.code)}>
                                <div className={`w-10 h-5 rounded-full transition-colors ${enabled ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'}`} />
                                <div className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${enabled ? 'translate-x-5' : 'translate-x-0'}`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className={`text-sm font-medium leading-tight ${enabled ? 'text-green-800 dark:text-green-300' : 'text-gray-700 dark:text-gray-300'}`}>
                                  {feat.label}
                                </p>
                                <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 leading-snug">{feat.desc}</p>
                              </div>
                            </label>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Bouton enregistrer */}
            <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-700">
              <p className="text-xs text-gray-400">
                {featureCodes.length === 0
                  ? 'Aucune fonctionnalité activée — les utilisateurs n\'auront accès à rien'
                  : `${featureCodes.length} fonctionnalité(s) activée(s) pour ce rôle`
                }
              </p>
              <button
                onClick={handleSaveFeatures}
                disabled={savingFeatures}
                className="flex items-center gap-2 px-5 py-2 rounded-lg text-white text-sm font-medium disabled:opacity-60 transition-colors"
                style={{ backgroundColor: '#8B5CF6' }}
              >
                {savingFeatures ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Enregistrer les fonctionnalités
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ONGLET 3 — UTILISATEURS                                               */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-800 dark:text-gray-100">Utilisateurs</h2>
            <button
              onClick={loadUsers}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 text-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingUsers ? 'animate-spin' : ''}`} />
              Actualiser
            </button>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
            {loadingUsers ? (
              <div className="flex items-center justify-center h-40 text-gray-400">
                <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement...
              </div>
            ) : users.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 text-gray-400 gap-2">
                <Users className="w-10 h-10 opacity-30" />
                <p className="text-sm">Aucun utilisateur trouvé</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Utilisateur</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Email</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Rôles assignés</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {users.map(user => {
                    const userRoles = user.roles || []
                    const isDropdownOpen = assignDropdown === user.id
                    const availableRoles = roles.filter(r => !userRoles.some(ur => (ur.id || ur) === r.id))

                    return (
                      <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center text-blue-600 dark:text-blue-400 font-semibold text-xs">
                              {(user.prenom?.[0] || user.username?.[0] || '?').toUpperCase()}
                            </div>
                            <div>
                              <p className="font-medium text-gray-900 dark:text-white">
                                {[user.prenom, user.nom].filter(Boolean).join(' ') || user.username}
                              </p>
                              {(user.prenom || user.nom) && (
                                <p className="text-xs text-gray-400">{user.username}</p>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-500 dark:text-gray-400">
                          {user.email || '—'}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {userRoles.length === 0 ? (
                              <span className="text-xs text-gray-400 italic">Aucun rôle</span>
                            ) : (
                              userRoles.map(ur => {
                                const roleData = roles.find(r => r.id === (ur.id || ur)) || ur
                                return (
                                  <span
                                    key={ur.id || ur}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                                    style={colorBadgeStyle(roleData.couleur || '#6B7280')}
                                  >
                                    {roleData.nom || ur}
                                    <button
                                      onClick={() => handleRemoveUserRole(user.id, ur.id || ur)}
                                      className="hover:opacity-70 ml-0.5"
                                      title="Retirer ce rôle"
                                    >
                                      <X className="w-3 h-3" />
                                    </button>
                                  </span>
                                )
                              })
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex justify-end">
                            <div className="relative">
                              <button
                                onClick={() => setAssignDropdown(isDropdownOpen ? null : user.id)}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 text-xs font-medium transition-colors"
                              >
                                <Plus className="w-3.5 h-3.5" />
                                Assigner un rôle
                              </button>

                              {isDropdownOpen && (
                                <>
                                  {/* Overlay transparent pour fermer */}
                                  <div
                                    className="fixed inset-0 z-10"
                                    onClick={() => setAssignDropdown(null)}
                                  />
                                  <div className="absolute right-0 top-full mt-1 z-20 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg min-w-[180px] py-1 overflow-hidden">
                                    {availableRoles.length === 0 ? (
                                      <p className="px-4 py-2 text-xs text-gray-400 italic">
                                        Tous les rôles sont assignés
                                      </p>
                                    ) : (
                                      availableRoles.map(role => (
                                        <button
                                          key={role.id}
                                          onClick={() => handleAssignRole(user.id, role.id)}
                                          className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-left"
                                        >
                                          <span
                                            className="w-2.5 h-2.5 rounded-full shrink-0"
                                            style={{ backgroundColor: role.couleur || '#6B7280' }}
                                          />
                                          {role.nom}
                                          {role.is_admin && (
                                            <span className="ml-auto text-xs text-amber-500">Admin</span>
                                          )}
                                        </button>
                                      ))
                                    )}
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* MODAL — Nouveau rôle                                                  */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {showRoleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-blue-600" />
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Nouveau rôle</h2>
              </div>
              <button onClick={closeRoleModal} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateRole} className="p-6 space-y-4">
              {roleFormError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {roleFormError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Nom du rôle <span className="text-red-500">*</span>
                </label>
                <input
                  value={roleForm.nom}
                  onChange={e => setRoleForm(f => ({ ...f, nom: e.target.value }))}
                  placeholder="ex: Responsable commercial"
                  required
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  value={roleForm.description}
                  onChange={e => setRoleForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Décrivez les responsabilités de ce rôle…"
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Couleur du badge
                </label>
                <div className="flex items-center gap-3">
                  {PRESET_COLORS.map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      title={label}
                      onClick={() => setRoleForm(f => ({ ...f, couleur: value }))}
                      className={`w-8 h-8 rounded-full transition-transform hover:scale-110 ${
                        roleForm.couleur === value ? 'ring-2 ring-offset-2 ring-gray-500 scale-110' : ''
                      }`}
                      style={{ backgroundColor: value }}
                    />
                  ))}
                  <div className="flex items-center gap-2 ml-2">
                    <span className="text-xs text-gray-400">ou</span>
                    <input
                      type="color"
                      value={roleForm.couleur}
                      onChange={e => setRoleForm(f => ({ ...f, couleur: e.target.value }))}
                      className="w-8 h-8 rounded cursor-pointer border border-gray-300"
                      title="Couleur personnalisée"
                    />
                  </div>
                </div>

                {/* Aperçu */}
                <div className="mt-3">
                  <span
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
                    style={colorBadgeStyle(roleForm.couleur)}
                  >
                    <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: roleForm.couleur }} />
                    {roleForm.nom || 'Aperçu du rôle'}
                  </span>
                </div>
              </div>

              <div>
                <label className="flex items-center gap-3 cursor-pointer">
                  <div
                    onClick={() => setRoleForm(f => ({ ...f, is_admin: !f.is_admin }))}
                    className={`relative w-10 h-5 rounded-full transition-colors ${
                      roleForm.is_admin ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                  >
                    <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                      roleForm.is_admin ? 'translate-x-5' : 'translate-x-0'
                    }`} />
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Rôle administrateur</span>
                    <p className="text-xs text-gray-400">Les admins ont accès aux paramètres de gestion</p>
                  </div>
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeRoleModal}
                  className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={savingRole}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium disabled:opacity-60"
                >
                  {savingRole ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Créer le rôle
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
