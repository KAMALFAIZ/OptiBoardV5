import { useState, useEffect, useCallback } from 'react'
import { useDWH } from '../context/DWHContext'
import { useAuth } from '../context/AuthContext'
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
  const { user } = useAuth()
  const dwhCode = currentDWH?.code || null
  const headers = dwhCode ? { 'X-DWH-Code': dwhCode } : {}
  const isSuperAdmin = user?.role_global === 'superadmin'

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

  // Colonnes masquées — par item de navigation
  const [expandedItemCols, setExpandedItemCols]   = useState({})  // itemId → bool
  const [itemColDefs, setItemColDefs]             = useState({})  // 'type:id' → [{field,label}]
  const [itemColChecked, setItemColChecked]       = useState({})  // 'type:id' → {field:bool}
  const [loadingItemCols, setLoadingItemCols]     = useState({})  // 'type:id' → bool
  const [savingItemCols, setSavingItemCols]       = useState({})  // 'type:id' → bool

  // Utilisateurs
  const [users, setUsers] = useState([])
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [assignDropdown, setAssignDropdown] = useState(null) // user id with open dropdown

  // Fonctionnalités
  const [featureCodes, setFeatureCodes]           = useState([])       // codes activés pour le rôle sélectionné
  const [savingFeatures, setSavingFeatures]       = useState(false)
  const [expandedCats, setExpandedCats]           = useState({})       // catégories ouvertes/fermées

  // Navigation menus dynamiques
  const [navMenus, setNavMenus]                   = useState([])
  const [loadingNavMenus, setLoadingNavMenus]     = useState(false)
  const [expandedMenuDetails, setExpandedMenuDetails] = useState({})   // sous-menus ouverts

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
      // DWH — filtrés selon le rôle : superadmin voit tout, admin_client voit uniquement son DWH
      try {
        const res = await api.get('/dwh-admin/list', { headers })
        const all = res.data?.data || []
        setAvailableDwh(isSuperAdmin ? all : all.filter(d => d.code === dwhCode))
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
  }, [dwhCode, isSuperAdmin])

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

  // ── Chargement des menus de navigation (pour section dynamique) ─────────────
  const loadNavMenus = useCallback(async () => {
    setLoadingNavMenus(true)
    try {
      const res = await api.get('/menus/', { headers })
      const menus = (res.data?.data || []).filter(m => m.actif !== false && m.is_active !== false)
      setNavMenus(menus)
    } catch { setNavMenus([]) }
    finally { setLoadingNavMenus(false) }
  }, [dwhCode])

  useEffect(() => {
    if (selectedRole) {
      loadRolePermissions(selectedRole)
      loadNavMenus()
    }
  }, [selectedRole, loadRolePermissions, loadNavMenus])

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
    if (activeTab === 'users') {
      loadUsers()
      loadRoles() // Rafraîchir les rôles pour que le dropdown d'assignation soit à jour
    }
  }, [activeTab, loadUsers, loadRoles])

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
    setExpandedItemCols({})
    setItemColDefs({})
    setItemColChecked({})
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

  // Section C — Colonnes masquées inline par item de navigation

  const loadItemColumns = useCallback(async (item, existingCols) => {
    if (!item.target_id) return
    const sType = item.type === 'pivot-v2' ? 'pivot' : item.type
    const ik = `${sType}:${item.target_id}`

    setLoadingItemCols(prev => ({ ...prev, [ik]: true }))
    try {
      // ── 1. Colonnes du rapport (utilise le cache si déjà chargé) ────────────
      let cols = existingCols || []
      if (!cols.length) {
        if (item.type === 'gridview') {
          const res = await api.get(`/gridview/grids/${item.target_id}`, { headers })
          const grid = res.data?.data || res.data || {}
          cols = (grid.columns || []).map(c => ({ field: c.field, label: c.header || c.field }))
        } else if (item.type === 'pivot-v2' || item.type === 'pivot') {
          const res = await api.get(`/v2/pivots/${item.target_id}`, { headers })
          const piv = res.data?.data || res.data || {}
          const rowsCfg = Array.isArray(piv.rows_config)    ? piv.rows_config    : JSON.parse(piv.rows_config    || '[]')
          const colsCfg = Array.isArray(piv.columns_config) ? piv.columns_config : JSON.parse(piv.columns_config || '[]')
          cols = [...rowsCfg, ...colsCfg].map(c => ({ field: c.field || c, label: c.label || c.field || c }))
        } else if (item.type === 'dashboard') {
          const res = await api.get(`/builder/dashboards/${item.target_id}`, { headers })
          const dash = res.data?.data || res.data || {}
          const widgets = Array.isArray(dash.widgets) ? dash.widgets : JSON.parse(dash.widgets || '[]')
          const fieldsSet = new Set()
          widgets.forEach(w => {
            const cfg = typeof w.config === 'string' ? JSON.parse(w.config || '{}') : (w.config || {})
            ;(cfg.columns || cfg.fields || []).forEach(f => fieldsSet.add(typeof f === 'string' ? f : f.field))
          })
          cols = [...fieldsSet].map(f => ({ field: f, label: f }))
        }
        setItemColDefs(prev => ({ ...prev, [ik]: cols }))
      }

      // ── 2. Masques sauvegardés — TOUJOURS rechargés depuis le serveur ───────
      // Convention : true = visible (coché), false = masqué (décoché)
      const init = Object.fromEntries(cols.map(c => [c.field, true]))
      if (selectedRole) {
        try {
          const maskRes = await api.get(`/roles/${selectedRole.id}/columns`, { headers })
          const saved = maskRes.data?.data || []
          const colFieldsLower = Object.fromEntries(cols.map(c => [c.field.toLowerCase(), c.field]))
          saved
            .filter(m =>
              m.report_type === sType &&
              String(m.report_id) === String(item.target_id) &&
              (m.is_hidden === true || m.is_hidden === 1)
            )
            .forEach(m => {
              // Matching exact puis insensible à la casse
              if (m.column_name in init) {
                init[m.column_name] = false  // décoché = masqué
              } else {
                const matched = colFieldsLower[m.column_name.toLowerCase()]
                if (matched) init[matched] = false
              }
            })
        } catch { /* silencieux */ }
      }
      setItemColChecked(prev => ({ ...prev, [ik]: init }))
    } catch {
      setItemColDefs(prev => ({ ...prev, [ik]: [] }))
    } finally {
      setLoadingItemCols(prev => ({ ...prev, [ik]: false }))
    }
  }, [dwhCode, selectedRole])

  const toggleItemColPanel = (item) => {
    const isOpen = expandedItemCols[item.id]
    setExpandedItemCols(prev => ({ ...prev, [item.id]: !isOpen }))
    if (!isOpen && item.target_id) loadItemColumns(item)
  }

  const saveItemColumns = async (item) => {
    if (!selectedRole || !item.target_id) return
    const sType = item.type === 'pivot-v2' ? 'pivot' : item.type
    const ik = `${sType}:${item.target_id}`
    const hiddenCols = Object.entries(itemColChecked[ik] || {}).filter(([, v]) => !v).map(([k]) => k)
    setSavingItemCols(prev => ({ ...prev, [ik]: true }))
    try {
      await api.post(
        `/roles/${selectedRole.id}/columns`,
        { report_type: sType, report_id: parseInt(item.target_id), hidden_columns: hiddenCols },
        { headers }
      )
      showToast(`${hiddenCols.length} colonne(s) masquée(s) enregistrée(s)`)
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur enregistrement masques'))
    } finally {
      setSavingItemCols(prev => ({ ...prev, [ik]: false }))
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
      const res = await api.post(`/roles/${selectedRole.id}/features`, { feature_codes: featureCodes }, { headers })
      // Recharger les permissions pour synchroniser la section Colonnes masquées
      await loadRolePermissions(selectedRole)
      showToast(res.data?.message || `${featureCodes.length} fonctionnalité(s) enregistrée(s)`)
    } catch (e) {
      setGlobalError(extractError(e, 'Erreur enregistrement fonctionnalités'))
    } finally {
      setSavingFeatures(false)
    }
  }

  const toggleExpandCat = (id) => setExpandedCats(prev => ({ ...prev, [id]: !prev[id] }))

  // ── Helpers menus de navigation dynamiques ───────────────────────────────────
  const navMenuCode = (id) => `nav_menu_${id}`
  const navItemCode = (id) => `nav_item_${id}`
  const isNavMenuOn = (id) => featureCodes.includes(navMenuCode(id))
  const isNavItemOn = (id) => featureCodes.includes(navItemCode(id))

  // Collecte récursivement tous les IDs des nœuds feuilles (type !== folder ou sans enfants)
  const collectLeafIds = (nodes) => {
    const ids = []
    for (const node of (nodes || [])) {
      const children = node.children || []
      if (node.type !== 'folder' || children.length === 0) {
        ids.push(node.id)
      } else {
        ids.push(...collectLeafIds(children))
      }
    }
    return ids
  }

  // Toggle menu parent : active/désactive le parent + TOUS les rapports feuilles récursivement
  const toggleNavMenu = (menu) => {
    const mCode    = navMenuCode(menu.id)
    const leafIds  = collectLeafIds(menu.children || [])
    const allCodes = [mCode, ...leafIds.map(navItemCode)]
    if (isNavMenuOn(menu.id)) {
      setFeatureCodes(prev => prev.filter(c => !allCodes.includes(c)))
    } else {
      setFeatureCodes(prev => [...new Set([...prev, ...allCodes])])
    }
  }

  // Toggle rapport individuel : active le menu parent si besoin, le retire si dernier rapport désactivé
  const toggleNavItem = (menu, item) => {
    const iCode   = navItemCode(item.id)
    const mCode   = navMenuCode(menu.id)
    const leafIds = collectLeafIds(menu.children || [])
    if (featureCodes.includes(iCode)) {
      const othersOn = leafIds.filter(id => id !== item.id && featureCodes.includes(navItemCode(id)))
      setFeatureCodes(prev => {
        const next = prev.filter(c => c !== iCode)
        return othersOn.length === 0 ? next.filter(c => c !== mCode) : next
      })
    } else {
      setFeatureCodes(prev => [...new Set([...prev, iCode, mCode])])
    }
  }

  // Tout activer / désactiver toute la section navigation (rapports feuilles uniquement)
  const toggleAllNavMenus = () => {
    const allNavCodes = navMenus.flatMap(m => [
      navMenuCode(m.id),
      ...collectLeafIds(m.children || []).map(navItemCode),
    ])
    const allOn = navMenus.length > 0 && navMenus.every(m => isNavMenuOn(m.id))
    if (allOn) {
      setFeatureCodes(prev => prev.filter(c => !allNavCodes.includes(c)))
    } else {
      setFeatureCodes(prev => [...new Set([...prev, ...allNavCodes])])
    }
  }

  const toggleMenuDetails = (menuId) =>
    setExpandedMenuDetails(prev => ({ ...prev, [menuId]: !prev[menuId] }))

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

          {/* Section B supprimée — rapports synchronisés automatiquement depuis Navigation & Menus */}
          {false && <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                  <LayoutDashboard className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">Rapports autorisés</h3>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                    {Object.values(reportsByType).reduce((s, a) => s + (a?.length || 0), 0)} rapport{Object.values(reportsByType).reduce((s, a) => s + (a?.length || 0), 0) !== 1 ? 's' : ''} assigné{Object.values(reportsByType).reduce((s, a) => s + (a?.length || 0), 0) !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
              {!showAddReport && (
                <button
                  onClick={() => setShowAddReport(true)}
                  className="flex items-center gap-1.5 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-lg transition-colors shadow-sm"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Ajouter
                </button>
              )}
            </div>

            {/* Type tabs */}
            <div className="flex border-b border-gray-100 dark:border-gray-700/60 bg-gray-50/70 dark:bg-gray-800/50">
              {REPORT_TYPES.map(({ key, label, icon: Icon }) => {
                const count = (reportsByType[key] || []).length
                return (
                  <button
                    key={key}
                    onClick={() => { setReportTab(key); setShowAddReport(false); setReportSearch(''); setNewReportForm({ id: '', name: '', can_view: true, can_export: false, can_schedule: false }) }}
                    className={`relative flex items-center gap-2 px-5 py-3 text-xs font-medium transition-all
                      ${reportTab === key
                        ? 'text-purple-700 dark:text-purple-300 bg-white dark:bg-gray-800'
                        : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/50 dark:hover:bg-gray-800/30'
                      }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {label}
                    <span className={`px-1.5 py-0.5 rounded-full text-xs leading-none font-semibold
                      ${reportTab === key
                        ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300'
                        : 'bg-gray-200 dark:bg-gray-600/60 text-gray-500 dark:text-gray-400'
                      }`}>
                      {count}
                    </span>
                    {reportTab === key && (
                      <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-600 dark:bg-purple-400 rounded-t-full" />
                    )}
                  </button>
                )
              })}
            </div>

            {/* Content */}
            <div className="p-4 space-y-3">

              {/* Assigned reports list */}
              {(reportsByType[reportTab] || []).length === 0 && !showAddReport ? (
                <div className="flex flex-col items-center justify-center py-10 text-gray-400">
                  <div className="p-3 bg-gray-100 dark:bg-gray-700/40 rounded-xl mb-3">
                    <LayoutDashboard className="w-6 h-6 opacity-40" />
                  </div>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Aucun rapport assigné</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Cliquez sur "Ajouter" pour assigner des rapports</p>
                </div>
              ) : (reportsByType[reportTab] || []).length > 0 && (
                <div className="space-y-1.5">
                  {(reportsByType[reportTab] || []).map(report => (
                    <div
                      key={report.id}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/20 hover:bg-gray-100/80 dark:hover:bg-gray-700/40 group transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-600/50"
                    >
                      {/* ID badge */}
                      <span className="text-xs font-mono font-semibold text-gray-400 dark:text-gray-500 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 px-1.5 py-0.5 rounded shrink-0">
                        #{report.id}
                      </span>
                      {/* Name */}
                      <span className="flex-1 text-sm font-medium text-gray-800 dark:text-gray-200 truncate min-w-0">
                        {getReportName(report.report_type, report.id)}
                      </span>
                      {/* Permission pills */}
                      <div className="flex items-center gap-1 shrink-0">
                        {[
                          { key: 'can_view',     label: 'Voir',    on: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 border-blue-200 dark:border-blue-700/60',    off: 'bg-gray-100 text-gray-400 dark:bg-gray-700/50 dark:text-gray-500 border-gray-200 dark:border-gray-600' },
                          { key: 'can_export',   label: 'Export',  on: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-700/60', off: 'bg-gray-100 text-gray-400 dark:bg-gray-700/50 dark:text-gray-500 border-gray-200 dark:border-gray-600' },
                          { key: 'can_schedule', label: 'Planif.', on: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300 border-orange-200 dark:border-orange-700/60',   off: 'bg-gray-100 text-gray-400 dark:bg-gray-700/50 dark:text-gray-500 border-gray-200 dark:border-gray-600' },
                        ].map(({ key, label, on, off }) => (
                          <button
                            key={key}
                            onClick={() => handleToggleReportPerm(reportTab, report.id, key)}
                            title={key === 'can_view' ? 'Voir' : key === 'can_export' ? 'Exporter' : 'Planifier'}
                            className={`px-2 py-0.5 rounded-full text-xs font-semibold border transition-all cursor-pointer
                              ${report[key] ? on : off}`}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                      {/* Remove */}
                      <button
                        onClick={() => handleRemoveReport(reportTab, report.id)}
                        className="p-1 rounded-md text-transparent group-hover:text-gray-300 dark:group-hover:text-gray-500 hover:!text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all shrink-0"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add form */}
              {showAddReport && (
                <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                  {/* Form header */}
                  <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 dark:bg-gray-700/40 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-2">
                      <Plus className="w-3.5 h-3.5 text-purple-500" />
                      <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                        Ajouter — {REPORT_TYPES.find(r => r.key === reportTab)?.label}
                      </span>
                    </div>
                    <button
                      onClick={() => { setShowAddReport(false); setReportSearch(''); setNewReportForm({ id: '', name: '', can_view: true, can_export: false, can_schedule: false }) }}
                      className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <form onSubmit={handleAddReport} className="p-4 space-y-3">
                    {availableReports[reportTab]?.length > 0 ? (
                      <>
                        {/* Search */}
                        <div className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus-within:border-purple-400 focus-within:ring-2 focus-within:ring-purple-100 dark:focus-within:ring-purple-900/30 transition-all">
                          <svg className="w-3.5 h-3.5 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                          </svg>
                          <input
                            type="text"
                            value={reportSearch}
                            onChange={e => setReportSearch(e.target.value)}
                            placeholder="Rechercher un rapport..."
                            className="flex-1 text-xs bg-transparent outline-none text-gray-700 dark:text-gray-300 placeholder-gray-400"
                            autoFocus
                          />
                          {reportSearch && (
                            <button type="button" onClick={() => setReportSearch('')} className="text-gray-400 hover:text-gray-600">
                              <X className="w-3 h-3" />
                            </button>
                          )}
                        </div>

                        {/* Report list */}
                        <div className="max-h-56 overflow-y-auto rounded-lg border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700/40">
                          {(() => {
                            const filtered = availableReports[reportTab]
                              .filter(r => !(reportsByType[reportTab] || []).some(x => String(x.id) === String(r.id)))
                              .filter(r =>
                                !reportSearch ||
                                r.nom.toLowerCase().includes(reportSearch.toLowerCase()) ||
                                String(r.id).includes(reportSearch)
                              )
                            if (filtered.length === 0) return (
                              <div className="flex flex-col items-center justify-center py-6 text-gray-400">
                                <p className="text-xs">Aucun rapport disponible</p>
                              </div>
                            )
                            return filtered.map(r => (
                              <button
                                key={r.id}
                                type="button"
                                onClick={() => { setNewReportForm(f => ({ ...f, id: String(r.id), name: r.nom })); setReportSearch('') }}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors
                                  ${String(newReportForm.id) === String(r.id)
                                    ? 'bg-purple-50 dark:bg-purple-900/20'
                                    : 'bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/30'
                                  }`}
                              >
                                <span className="text-xs font-mono font-semibold text-gray-400 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded shrink-0">
                                  #{r.id}
                                </span>
                                <span className={`flex-1 text-xs font-medium truncate
                                  ${String(newReportForm.id) === String(r.id)
                                    ? 'text-purple-700 dark:text-purple-300'
                                    : 'text-gray-700 dark:text-gray-300'
                                  }`}>
                                  {r.nom}
                                </span>
                                {String(newReportForm.id) === String(r.id) && (
                                  <Check className="w-3.5 h-3.5 text-purple-500 shrink-0" />
                                )}
                              </button>
                            ))
                          })()}
                        </div>
                      </>
                    ) : (
                      <input
                        value={newReportForm.id}
                        onChange={e => setNewReportForm(f => ({ ...f, id: e.target.value }))}
                        placeholder="ID du rapport (ex: 42)"
                        required
                        className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                      />
                    )}

                    {/* Selected report chip */}
                    {newReportForm.id && (
                      <div className="flex items-center gap-2 px-3 py-2 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700/50 rounded-lg">
                        <Check className="w-3.5 h-3.5 text-purple-500 shrink-0" />
                        <span className="text-xs font-semibold text-purple-700 dark:text-purple-300 truncate flex-1">
                          #{newReportForm.id} — {newReportForm.name}
                        </span>
                        <button type="button" onClick={() => setNewReportForm(f => ({ ...f, id: '', name: '' }))} className="text-purple-400 hover:text-purple-600 shrink-0">
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    )}

                    {/* Permission toggles */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mr-1">Permissions :</span>
                      {[
                        { key: 'can_view',     label: 'Voir',     on: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 border-blue-300 dark:border-blue-600',       off: 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 border-gray-300 dark:border-gray-600' },
                        { key: 'can_export',   label: 'Exporter', on: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-300 dark:border-emerald-600', off: 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 border-gray-300 dark:border-gray-600' },
                        { key: 'can_schedule', label: 'Planifier', on: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300 border-orange-300 dark:border-orange-600',  off: 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 border-gray-300 dark:border-gray-600' },
                      ].map(({ key, label, on, off }) => (
                        <button
                          key={key}
                          type="button"
                          onClick={() => setNewReportForm(f => ({ ...f, [key]: !f[key] }))}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all
                            ${newReportForm[key] ? on : off}`}
                        >
                          {newReportForm[key] && <Check className="w-3 h-3 shrink-0" />}
                          {label}
                        </button>
                      ))}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 pt-1 border-t border-gray-100 dark:border-gray-700">
                      <button
                        type="submit"
                        disabled={savingReport || !newReportForm.id}
                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold rounded-lg transition-colors shadow-sm"
                      >
                        {savingReport ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                        Ajouter le rapport
                      </button>
                      <button
                        type="button"
                        onClick={() => { setShowAddReport(false); setReportSearch(''); setNewReportForm({ id: '', name: '', can_view: true, can_export: false, can_schedule: false }) }}
                        className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 text-xs font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                      >
                        Annuler
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {/* Bottom "add" shortcut when list is not empty and form is hidden */}
              {!showAddReport && (reportsByType[reportTab] || []).length > 0 && (
                <button
                  onClick={() => setShowAddReport(true)}
                  className="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-xs font-medium text-gray-400 dark:text-gray-500 hover:border-purple-400 hover:text-purple-500 dark:hover:text-purple-400 dark:hover:border-purple-600 transition-colors w-full justify-center"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Ajouter un rapport
                </button>
              )}
            </div>
          </div>}

          {/* ── Section D — Fonctionnalités OptiBoard ────────────────────────── */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 space-y-4">
            {(() => {
              const allNavCodes = navMenus.flatMap(m => [navMenuCode(m.id), ...(m.children || []).map(c => navItemCode(c.id))])
              const totalAvailable = ALL_FEATURE_CODES.length + allNavCodes.length
              const totalActive = featureCodes.filter(c => ALL_FEATURE_CODES.includes(c) || allNavCodes.includes(c)).length
              return (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-violet-500" />
                <h3 className="font-semibold text-gray-800 dark:text-gray-100">Fonctionnalités OptiBoard</h3>
                <span className="px-2 py-0.5 text-xs rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 font-medium">
                  {totalActive} / {totalAvailable} activées
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
                  onClick={() => { setFeatureCodes([...ALL_FEATURE_CODES, ...allNavCodes]) }}
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
              )
            })()}

            {/* Catégories */}
            <div className="space-y-3">

              {/* ── Section Navigation & Menus (dynamique) ── */}
              {(() => {
                const isExpanded = expandedCats['nav_menus'] === true
                const activeCount = navMenus.filter(m => isNavMenuOn(m.id)).length
                const allNavOn = navMenus.length > 0 && navMenus.every(m => isNavMenuOn(m.id))
                const someNavOn = activeCount > 0 && !allNavOn
                return (
                  <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                    {/* En-tête catégorie */}
                    <div
                      className="flex items-center justify-between px-4 py-3 cursor-pointer select-none hover:bg-gray-50 dark:hover:bg-gray-700/40"
                      onClick={() => toggleExpandCat('nav_menus')}
                      style={{ borderLeft: '4px solid #3B82F6' }}
                    >
                      <div className="flex items-center gap-3">
                        <Layers className="w-4 h-4 text-blue-500" />
                        <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">Navigation & Menus</span>
                        <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                          style={{ backgroundColor: '#3B82F620', color: '#3B82F6' }}>
                          {activeCount}/{navMenus.length}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={e => { e.stopPropagation(); toggleAllNavMenus() }}
                          className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors ${
                            allNavOn
                              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200'
                              : someNavOn
                                ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 hover:bg-yellow-200'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200'
                          }`}
                        >
                          {allNavOn ? 'Tout désactiver' : 'Tout activer'}
                        </button>
                        {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                      </div>
                    </div>

                    {/* Corps */}
                    {isExpanded && (
                      <div className="divide-y divide-gray-100 dark:divide-gray-700/50">
                        {loadingNavMenus ? (
                          <div className="flex items-center justify-center py-6 text-gray-400 text-sm gap-2">
                            <RefreshCw className="w-4 h-4 animate-spin" /> Chargement des menus…
                          </div>
                        ) : navMenus.length === 0 ? (
                          <div className="flex items-center justify-center py-6 text-gray-400 text-sm">
                            Aucun menu configuré
                          </div>
                        ) : (
                          navMenus.map(menu => {
                            const hasChildren       = (menu.children || []).length > 0
                            const menuOn            = isNavMenuOn(menu.id)
                            const isDetailed        = !!expandedMenuDetails[menu.id]
                            const menuLeafIds       = collectLeafIds(menu.children || [])
                            const enabledChildCount = menuLeafIds.filter(id => isNavItemOn(id)).length
                            const totalLeafCount    = menuLeafIds.length

                            return (
                              <div key={menu.id} className={menuOn ? 'bg-blue-50/40 dark:bg-blue-900/10' : ''}>
                                {/* Ligne menu principal */}
                                <div className="flex items-center gap-3 px-4 py-3">
                                  {/* Toggle switch */}
                                  <div
                                    className="relative shrink-0 cursor-pointer"
                                    onClick={() => toggleNavMenu(menu)}
                                  >
                                    <div className={`w-10 h-5 rounded-full transition-colors ${menuOn ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'}`} />
                                    <div className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${menuOn ? 'translate-x-5' : 'translate-x-0'}`} />
                                  </div>

                                  {/* Nom + sous-titre */}
                                  <div className="flex-1 min-w-0">
                                    <p className={`text-sm font-medium leading-tight ${menuOn ? 'text-blue-800 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300'}`}>
                                      {menu.nom}
                                    </p>
                                    {hasChildren && (
                                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                                        {menuOn
                                          ? `${enabledChildCount}/${totalLeafCount} rapports actifs`
                                          : `${totalLeafCount} rapport${totalLeafCount > 1 ? 's' : ''}`
                                        }
                                      </p>
                                    )}
                                  </div>

                                  {/* Bouton détail sous-menus */}
                                  {hasChildren && (
                                    <button
                                      type="button"
                                      onClick={() => toggleMenuDetails(menu.id)}
                                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                                        isDetailed
                                          ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700 text-blue-600 dark:text-blue-300'
                                          : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:border-blue-300 hover:text-blue-600'
                                      }`}
                                    >
                                      {isDetailed ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                      Sous-menus
                                    </button>
                                  )}
                                </div>

                                {/* Détail sous-menus (dépliable) — affiche les rapports feuilles groupés par dossier */}
                                {hasChildren && isDetailed && (() => {
                                  const TYPE_META = {
                                    gridview:   { label: 'GridView',  cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',       Icon: Table2 },
                                    dashboard:  { label: 'Dashboard', cls: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',  Icon: LayoutDashboard },
                                    pivot:      { label: 'Pivot',     cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300', Icon: BarChart3 },
                                    'pivot-v2': { label: 'Pivot V2',  cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300', Icon: BarChart3 },
                                    page:       { label: 'Page',      cls: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',            Icon: Activity },
                                    url:        { label: 'Lien',      cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',  Icon: Zap },
                                    folder:     { label: 'Dossier',   cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',  Icon: Layers },
                                  }

                                  // Aplatir récursivement : collecter tous les nœuds feuilles groupés par section
                                  const collectItems = (nodes, sectionLabel = null) => {
                                    const groups = []
                                    for (const node of nodes) {
                                      const children = node.children || []
                                      const isLeaf = node.type !== 'folder' || children.length === 0
                                      if (isLeaf) {
                                        // Nœud feuille direct — rattacher à la section courante
                                        if (groups.length === 0) groups.push({ label: sectionLabel, items: [] })
                                        groups[groups.length - 1].items.push(node)
                                      } else {
                                        // Dossier intermédiaire → créer une section
                                        const subItems = []
                                        for (const child of children) {
                                          const subChildren = child.children || []
                                          if (child.type !== 'folder' || subChildren.length === 0) {
                                            subItems.push(child)
                                          } else {
                                            // Niveau encore plus profond : aplatir
                                            subChildren.forEach(sc => subItems.push(sc))
                                          }
                                        }
                                        groups.push({ label: node.nom, nodeId: node.id, items: subItems })
                                      }
                                    }
                                    return groups
                                  }

                                  const groups = collectItems(menu.children || [])
                                  const allLeafIds = groups.flatMap(g => g.items.map(i => i.id))
                                  const allLeafCodes = allLeafIds.map(id => navItemCode(id))
                                  const allLeafOn = allLeafIds.every(id => isNavItemOn(id))

                                  return (
                                    <div className="border-t border-blue-100 dark:border-blue-900/30 bg-white/50 dark:bg-gray-800/50">
                                      {/* En-tête */}
                                      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-700/30 border-b border-gray-100 dark:border-gray-700/40 sticky top-0 z-10">
                                        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                                          {allLeafIds.length} rapport{allLeafIds.length > 1 ? 's' : ''}
                                          <span className="ml-2 text-blue-600 dark:text-blue-400 font-normal">
                                            ({allLeafIds.filter(id => isNavItemOn(id)).length} actifs)
                                          </span>
                                        </span>
                                        <div className="flex items-center gap-3">
                                          <button type="button"
                                            onClick={() => setFeatureCodes(prev => [...new Set([...prev, navMenuCode(menu.id), ...allLeafCodes])])}
                                            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                                          >Tout activer</button>
                                          <button type="button"
                                            onClick={() => setFeatureCodes(prev => prev.filter(c => !allLeafCodes.includes(c) && c !== navMenuCode(menu.id)))}
                                            className="text-xs text-gray-400 hover:underline"
                                          >Tout désactiver</button>
                                          <span className="w-px h-3 bg-gray-300 dark:bg-gray-600" />
                                          <button type="button"
                                            onClick={() => toggleMenuDetails(menu.id)}
                                            className="flex items-center gap-1 px-2 py-1 rounded-md text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                                            title="Fermer le détail"
                                          >
                                            <X className="w-3.5 h-3.5" />
                                            Fermer
                                          </button>
                                        </div>
                                      </div>

                                      {/* Groupes de rapports */}
                                      {groups.map((group, gi) => (
                                        <div key={gi}>
                                          {/* En-tête dossier */}
                                          {group.label && (
                                            <div className="flex items-center gap-2 px-4 py-1.5 bg-gray-50/70 dark:bg-gray-700/20 border-b border-gray-100 dark:border-gray-700/30">
                                              <Layers className="w-3 h-3 text-gray-400" />
                                              <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">{group.label}</span>
                                              <span className="text-xs text-gray-400 ml-1">
                                                ({group.items.filter(i => isNavItemOn(i.id)).length}/{group.items.length})
                                              </span>
                                            </div>
                                          )}

                                          {/* Rapports du groupe */}
                                          {group.items.length === 0 ? (
                                            <div className="px-4 py-2 text-xs text-gray-400 italic">Aucun rapport dans cette section</div>
                                          ) : (
                                            <div className="divide-y divide-gray-100 dark:divide-gray-700/30">
                                              {group.items.map(item => {
                                                const itemOn = isNavItemOn(item.id)
                                                const meta = TYPE_META[item.type] || { label: item.type || '—', cls: 'bg-gray-100 text-gray-500', Icon: Layers }
                                                const TypeIcon = meta.Icon
                                                const hasColSupport = item.target_id && ['gridview','pivot','pivot-v2','dashboard'].includes(item.type)
                                                const sType = item.type === 'pivot-v2' ? 'pivot' : item.type
                                                const ik = `${sType}:${item.target_id}`
                                                const hCount = Object.values(itemColChecked[ik] || {}).filter(v => !v).length
                                                const colPanelOpen = !!expandedItemCols[item.id]
                                                return (
                                                  <div key={item.id}>
                                                    {/* Ligne item */}
                                                    <div
                                                      className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors ${
                                                        itemOn
                                                          ? 'bg-blue-50/50 dark:bg-blue-900/10 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                                                          : 'hover:bg-gray-50 dark:hover:bg-gray-700/20'
                                                      }`}
                                                      onClick={() => toggleNavItem(menu, item)}
                                                    >
                                                      {/* Toggle mini */}
                                                      <div className="relative shrink-0">
                                                        <div className={`rounded-full transition-colors ${itemOn ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'}`}
                                                          style={{ width: '2rem', height: '1rem' }} />
                                                        <div className="absolute rounded-full bg-white shadow transition-transform"
                                                          style={{ width: '0.75rem', height: '0.75rem', top: '0.125rem', left: itemOn ? '1.125rem' : '0.125rem' }} />
                                                      </div>

                                                      {/* Badge type */}
                                                      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-semibold shrink-0 ${meta.cls}`}>
                                                        <TypeIcon className="w-2.5 h-2.5" />
                                                        {meta.label}
                                                      </span>

                                                      {/* Nom rapport */}
                                                      <div className="flex-1 min-w-0">
                                                        <span className={`text-sm font-medium truncate block ${itemOn ? 'text-blue-800 dark:text-blue-200' : 'text-gray-700 dark:text-gray-300'}`}>
                                                          {item.nom}
                                                        </span>
                                                        {item.target_name && (
                                                          <span className="text-xs text-gray-400 dark:text-gray-500 truncate block" title={item.target_name}>
                                                            #{item.target_id} — {item.target_name}
                                                          </span>
                                                        )}
                                                        {item.type === 'url' && item.url && (
                                                          <span className="text-xs text-gray-400 truncate block">{item.url}</span>
                                                        )}
                                                      </div>

                                                      {/* ID badge */}
                                                      {item.target_id && (
                                                        <span className="text-xs font-mono text-gray-300 dark:text-gray-600 shrink-0">#{item.target_id}</span>
                                                      )}

                                                      {/* Bouton Colonnes masquées */}
                                                      {hasColSupport && (
                                                        <button
                                                          onClick={e => { e.stopPropagation(); toggleItemColPanel(item) }}
                                                          title="Colonnes masquées"
                                                          className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border transition-colors shrink-0 ${
                                                            colPanelOpen
                                                              ? 'bg-orange-100 dark:bg-orange-900/30 border-orange-300 dark:border-orange-700 text-orange-600 dark:text-orange-400'
                                                              : hCount > 0
                                                                ? 'bg-orange-50 dark:bg-orange-900/10 border-orange-200 dark:border-orange-800 text-orange-500'
                                                                : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-600 text-gray-400 hover:border-orange-300 hover:text-orange-500'
                                                          }`}
                                                        >
                                                          <EyeOff className="w-3 h-3" />
                                                          {hCount > 0 && <span>{hCount}</span>}
                                                        </button>
                                                      )}

                                                      {!itemOn && !hasColSupport && <Lock className="w-3.5 h-3.5 text-gray-300 dark:text-gray-600 shrink-0" />}
                                                    </div>

                                                    {/* Panneau colonnes masquées */}
                                                    {colPanelOpen && hasColSupport && (() => {
                                                      const cols = itemColDefs[ik] || []
                                                      const checked = itemColChecked[ik] || {}
                                                      const isLoading = loadingItemCols[ik]
                                                      const isSaving = savingItemCols[ik]
                                                      const hidden = Object.values(checked).filter(v => !v).length
                                                      return (
                                                        <div className="border-t border-orange-100 dark:border-orange-900/30 bg-orange-50/20 dark:bg-orange-900/5 px-4 py-3 space-y-2">
                                                          {isLoading ? (
                                                            <div className="flex items-center gap-2 text-xs text-gray-400 py-1">
                                                              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                                              Chargement des colonnes…
                                                            </div>
                                                          ) : cols.length === 0 ? (
                                                            <p className="text-xs text-gray-400 italic">Aucune colonne disponible pour ce rapport</p>
                                                          ) : (
                                                            <>
                                                              {/* Barre d'actions */}
                                                              <div className="flex items-center justify-between">
                                                                <span className="text-xs font-medium text-orange-700 dark:text-orange-400">
                                                                  {cols.length} col. — <span className="font-semibold">{hidden} masquée{hidden !== 1 ? 's' : ''}</span>
                                                                </span>
                                                                <div className="flex items-center gap-3">
                                                                  <button type="button"
                                                                    onClick={() => setItemColChecked(prev => ({ ...prev, [ik]: Object.fromEntries(cols.map(c => [c.field, false])) }))}
                                                                    className="text-xs text-orange-600 dark:text-orange-400 hover:underline"
                                                                  >Tout masquer</button>
                                                                  <button type="button"
                                                                    onClick={() => setItemColChecked(prev => ({ ...prev, [ik]: Object.fromEntries(cols.map(c => [c.field, true])) }))}
                                                                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                                                                  >Tout afficher</button>
                                                                </div>
                                                              </div>

                                                              {/* Grille cases à cocher */}
                                                              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden max-h-44 overflow-y-auto">
                                                                {cols.map(col => (
                                                                  <label
                                                                    key={col.field}
                                                                    className={`flex items-center gap-2 px-2.5 py-1.5 cursor-pointer text-xs border-b border-r border-gray-100 dark:border-gray-700 transition-colors ${
                                                                      !checked[col.field]
                                                                        ? 'bg-orange-50 dark:bg-orange-900/10 text-orange-700 dark:text-orange-300'
                                                                        : 'hover:bg-gray-50 dark:hover:bg-gray-700/30 text-gray-700 dark:text-gray-300'
                                                                    }`}
                                                                  >
                                                                    <input
                                                                      type="checkbox"
                                                                      checked={!!checked[col.field]}
                                                                      onChange={() => setItemColChecked(prev => ({
                                                                        ...prev,
                                                                        [ik]: { ...(prev[ik] || {}), [col.field]: !prev[ik]?.[col.field] }
                                                                      }))}
                                                                      className="rounded border-gray-300 text-blue-500 focus:ring-blue-400 w-3 h-3 shrink-0"
                                                                    />
                                                                    <span className="truncate" title={col.field}>
                                                                      {col.label !== col.field
                                                                        ? <><span className="font-medium">{col.label}</span><span className="ml-1 text-gray-400">({col.field})</span></>
                                                                        : col.field
                                                                      }
                                                                    </span>
                                                                    {!checked[col.field] && <EyeOff className="w-2.5 h-2.5 ml-auto shrink-0 text-orange-500" />}
                                                                  </label>
                                                                ))}
                                                              </div>

                                                              {/* Bouton enregistrer */}
                                                              <div className="flex justify-end">
                                                                <button
                                                                  onClick={() => saveItemColumns(item)}
                                                                  disabled={isSaving}
                                                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-600 hover:bg-orange-700 text-white text-xs font-medium rounded-lg disabled:opacity-60"
                                                                >
                                                                  {isSaving ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                                                                  Enregistrer
                                                                </button>
                                                              </div>
                                                            </>
                                                          )}
                                                        </div>
                                                      )
                                                    })()}
                                                  </div>
                                                )
                                              })}
                                            </div>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  )
                                })()}
                              </div>
                            )
                          })
                        )}
                      </div>
                    )}
                  </div>
                )
              })()}

              {/* ── Catégories statiques (IA, Builders, Alertes, Admin) ── */}
              {FEATURE_CATEGORIES.map(cat => {
                const Icon = cat.icon
                const isExpanded = expandedCats[cat.id] === true
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
                  ? "Aucune fonctionnalité activée — les utilisateurs n'auront accès à rien"
                  : `${featureCodes.length} entrée(s) activée(s) pour ce rôle (menus + fonctionnalités)`
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

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
            {loadingUsers ? (
              <div className="flex items-center justify-center h-40 text-gray-400 rounded-xl overflow-hidden">
                <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement...
              </div>
            ) : users.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 text-gray-400 gap-2 rounded-xl overflow-hidden">
                <Users className="w-10 h-10 opacity-30" />
                <p className="text-sm">Aucun utilisateur trouvé</p>
              </div>
            ) : (
              <table className="w-full text-sm overflow-visible">
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
