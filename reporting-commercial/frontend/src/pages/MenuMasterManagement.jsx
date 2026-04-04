import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import {
  Plus, Save, Trash2, Edit2, X, ChevronRight, ChevronDown,
  Folder, Table, Table2, LayoutDashboard, FileSpreadsheet, Link,
  Users, Check, Search, GripVertical, Settings, Lock, Filter,
  Eye, EyeOff, RefreshCw, MoreVertical, Copy, FolderOpen,
  Globe, Send, CheckCircle, AlertCircle, XCircle, Loader2,
  // Icones metier
  FileText, Truck, ClipboardList, FileQuestion, RotateCcw, PackageCheck,
  Receipt, TrendingUp, TrendingDown, PieChart, Target, MapPin, Layers,
  Activity, DollarSign, Percent, ShoppingBag, ShoppingCart, BarChart2,
  BarChart3, LineChart, Award, AlertTriangle, Clock, Repeat, GitCompare,
  UserCheck, UserX, User, Gauge, Crosshair, Star, Zap, ArrowUpDown,
  CircleDollarSign, BadgePercent, Scale, Package, Wallet, Boxes,
  Database, Calendar, Mail, CreditCard, ArrowRightLeft,
} from 'lucide-react'
import {
  getMasterMenus, getMasterMenusFlat, createMasterMenu, updateMasterMenu,
  deleteMasterMenu, getMasterMenuTargets, getMasterClients,
  publishEntities, publishAllEntities, getMenusSyncStatus, cleanupClientMenus
} from '../services/api'

const ICONS = [
  // Generiques
  { value: 'Folder', icon: Folder, label: 'Dossier' },
  { value: 'FolderOpen', icon: FolderOpen, label: 'Dossier ouvert' },
  { value: 'Table2', icon: Table2, label: 'Table' },
  { value: 'LayoutDashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { value: 'FileSpreadsheet', icon: FileSpreadsheet, label: 'Feuille' },
  { value: 'Database', icon: Database, label: 'Base de donnees' },
  // Documents
  { value: 'FileText', icon: FileText, label: 'Document' },
  { value: 'Receipt', icon: Receipt, label: 'Facture' },
  { value: 'ClipboardList', icon: ClipboardList, label: 'Bon de commande' },
  { value: 'FileQuestion', icon: FileQuestion, label: 'Devis' },
  { value: 'Truck', icon: Truck, label: 'Livraison' },
  { value: 'PackageCheck', icon: PackageCheck, label: 'Preparation' },
  { value: 'RotateCcw', icon: RotateCcw, label: 'Retour' },
  // Ventes & Commerce
  { value: 'ShoppingCart', icon: ShoppingCart, label: 'Ventes' },
  { value: 'ShoppingBag', icon: ShoppingBag, label: 'Panier' },
  { value: 'Target', icon: Target, label: 'Objectif' },
  { value: 'Crosshair', icon: Crosshair, label: 'Ciblage' },
  // Analyse
  { value: 'BarChart3', icon: BarChart3, label: 'Graphique barres' },
  { value: 'BarChart2', icon: BarChart2, label: 'Analyse' },
  { value: 'LineChart', icon: LineChart, label: 'Courbe' },
  { value: 'PieChart', icon: PieChart, label: 'Camembert' },
  { value: 'TrendingUp', icon: TrendingUp, label: 'Tendance hausse' },
  { value: 'TrendingDown', icon: TrendingDown, label: 'Tendance baisse' },
  { value: 'Activity', icon: Activity, label: 'Activite' },
  { value: 'GitCompare', icon: GitCompare, label: 'Comparatif' },
  // Finance
  { value: 'Wallet', icon: Wallet, label: 'Finance' },
  { value: 'DollarSign', icon: DollarSign, label: 'Montant' },
  { value: 'CircleDollarSign', icon: CircleDollarSign, label: 'CA' },
  { value: 'CreditCard', icon: CreditCard, label: 'Paiement' },
  { value: 'BadgePercent', icon: BadgePercent, label: 'Remise' },
  { value: 'Percent', icon: Percent, label: 'Pourcentage' },
  { value: 'Scale', icon: Scale, label: 'Marge' },
  // Logistique
  { value: 'Package', icon: Package, label: 'Stock' },
  { value: 'Boxes', icon: Boxes, label: 'Stock multi' },
  // Geographie
  { value: 'MapPin', icon: MapPin, label: 'Geographie' },
  { value: 'Layers', icon: Layers, label: 'Couches' },
  // Clients
  { value: 'Users', icon: Users, label: 'Clients' },
  { value: 'UserCheck', icon: UserCheck, label: 'Client fidele' },
  { value: 'UserX', icon: UserX, label: 'Client perdu' },
  { value: 'Star', icon: Star, label: 'Top/Classement' },
  { value: 'Award', icon: Award, label: 'Performance' },
  // Alertes & Temps
  { value: 'AlertTriangle', icon: AlertTriangle, label: 'Alerte' },
  { value: 'Clock', icon: Clock, label: 'Temps/Delai' },
  { value: 'Zap', icon: Zap, label: 'Urgence' },
  { value: 'Gauge', icon: Gauge, label: 'Jauge/KPI' },
  // Divers
  { value: 'Repeat', icon: Repeat, label: 'Recurrence' },
  { value: 'ArrowUpDown', icon: ArrowUpDown, label: 'Tri/Classement' },
  { value: 'Settings', icon: Settings, label: 'Parametres' },
]

const MENU_TYPES = [
  { value: 'folder', label: 'Dossier', icon: Folder, color: 'text-amber-600', bg: 'bg-amber-100' },
  { value: 'pivot-v2', label: 'Pivot Table', icon: Table2, color: 'text-blue-600', bg: 'bg-blue-100' },
  { value: 'gridview', label: 'GridView', icon: FileSpreadsheet, color: 'text-green-600', bg: 'bg-green-100' },
  { value: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, color: 'text-purple-600', bg: 'bg-purple-100' },
  { value: 'page', label: 'Page/Lien', icon: Link, color: 'text-gray-600', bg: 'bg-gray-100' },
]

const getTypeStyle = (type) => {
  const lookupType = type === 'pivot' ? 'pivot-v2' : type
  const typeInfo = MENU_TYPES.find(t => t.value === lookupType)
  return typeInfo || { color: 'text-gray-600', bg: 'bg-gray-100', label: type }
}

const IconComponent = ({ name, className }) => {
  const iconMap = {
    Folder, FolderOpen, Table2, LayoutDashboard, FileSpreadsheet, Link, Users, Database,
    Settings, Table,
    FileText, Receipt, ClipboardList, FileQuestion, Truck, PackageCheck, RotateCcw,
    ShoppingCart, ShoppingBag, Target, Crosshair,
    BarChart3, BarChart2, LineChart, PieChart, TrendingUp, TrendingDown, Activity,
    GitCompare, ArrowUpDown,
    Wallet, DollarSign, CircleDollarSign, CreditCard, BadgePercent, Percent, Scale,
    Package, Boxes,
    MapPin, Layers,
    UserCheck, UserX, User, Star, Award,
    AlertTriangle, Clock, Zap, Gauge,
    Repeat, Filter, ArrowRightLeft, Calendar, Mail,
  }
  const Icon = iconMap[name]
  return Icon ? <Icon className={className} /> : <Folder className={className} />
}

export default function MenuMasterManagement() {
  const [menus, setMenus] = useState([])
  const [flatMenus, setFlatMenus] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('structure') // structure, publish

  // Modal edition
  const [showModal, setShowModal] = useState(false)
  const [editingMenu, setEditingMenu] = useState(null)
  const [formData, setFormData] = useState({
    parent_id: null, nom: '', code: '', icon: 'Folder',
    type: 'folder', target_id: null, url: '', ordre: 0, is_active: true
  })
  const [targets, setTargets] = useState([])
  const [saving, setSaving] = useState(false)

  // Menus ouverts
  const [openMenus, setOpenMenus] = useState({})

  // Highlight + scroll
  const [highlightedMenuId, setHighlightedMenuId] = useState(null)
  const menuRefs = useRef({})

  // Recherche et filtres
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [showInactive, setShowInactive] = useState(true)

  // Publication
  const [syncStatus, setSyncStatus] = useState(null)
  const [loadingSyncStatus, setLoadingSyncStatus] = useState(false)
  const [selectedClients, setSelectedClients] = useState([])
  const [publishing, setPublishing] = useState(false)
  const [publishResult, setPublishResult] = useState(null)
  const [cleaningClient, setCleaningClient] = useState(null)  // code du client en cours de nettoyage
  const [cleanupResults, setCleanupResults] = useState({})    // code → résultat

  useEffect(() => { loadData() }, [])

  useEffect(() => {
    if (formData.type && formData.type !== 'folder' && formData.type !== 'page') {
      loadTargets(formData.type)
    }
  }, [formData.type])

  useEffect(() => {
    if (activeTab === 'publish') loadSyncStatus()
  }, [activeTab])

  const loadData = async () => {
    setLoading(true)
    try {
      const [menusRes, flatRes] = await Promise.all([
        getMasterMenus(),
        getMasterMenusFlat(),
      ])

      // Menus réservés client/DWH — masqués en mode master
      const CLIENT_ONLY_MENUS = [
        /^mon\s/i,                          // "Mon …" (espace perso)
        /^mon\s*espace\s*client$/i,         // "Mon Espace Client"
        /^gestion\s+des\s+r[oô]les?$/i,    // "Gestion des rôles"
        /^utilisateurs?\s*[-—]\s*client$/i, // "Utilisateurs — Client"
        /^gestion\s+des\s+menus?$/i,        // "Gestion des Menus"
      ]
      const isClientOnlyMenu = (m) => {
        const nom = m.nom?.trim() || ''
        return CLIENT_ONLY_MENUS.some(re => re.test(nom))
      }
      const filterTree = (list) =>
        (list || [])
          .filter(m => !isClientOnlyMenu(m))
          .map(m => ({ ...m, children: filterTree(m.children) }))

      setMenus(filterTree(menusRes.data.data || []))
      setFlatMenus((flatRes.data.data || []).filter(m => !isClientOnlyMenu(m)))
    } catch (err) {
      console.error('Erreur chargement menus maitre:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadTargets = async (type) => {
    try {
      const response = await getMasterMenuTargets(type)
      setTargets(response.data.data || [])
    } catch (err) {
      console.error('Erreur chargement targets:', err)
      setTargets([])
    }
  }

  const loadSyncStatus = async () => {
    setLoadingSyncStatus(true)
    try {
      const response = await getMenusSyncStatus()
      setSyncStatus(response.data.data || null)
    } catch (err) {
      console.error('Erreur chargement sync status:', err)
    } finally {
      setLoadingSyncStatus(false)
    }
  }

  const toggleMenu = (menuId) => {
    setOpenMenus(prev => ({ ...prev, [menuId]: !prev[menuId] }))
  }

  // Filtrage
  const filterMenus = useCallback((menuList, query, type, showInactiveMenus) => {
    const filterMenu = (menu) => {
      const matchesSearch = !query ||
        menu.nom?.toLowerCase().includes(query.toLowerCase()) ||
        menu.code?.toLowerCase().includes(query.toLowerCase())
      const matchesType = type === 'all' || menu.type === type || (type === 'pivot-v2' && menu.type === 'pivot')
      const matchesActive = showInactiveMenus || menu.is_active
      const filteredChildren = menu.children
        ? menu.children.map(filterMenu).filter(Boolean)
        : []
      if ((matchesSearch && matchesType && matchesActive) || filteredChildren.length > 0) {
        return { ...menu, children: filteredChildren, _matchesSearch: matchesSearch && matchesType && matchesActive }
      }
      return null
    }
    return menuList.map(filterMenu).filter(Boolean)
  }, [])

  const filteredMenus = useMemo(() => {
    return filterMenus(menus, searchQuery, filterType, showInactive)
  }, [menus, searchQuery, filterType, showInactive, filterMenus])

  const menuCounts = useMemo(() => {
    const counts = { all: 0, folder: 0, 'pivot-v2': 0, gridview: 0, dashboard: 0, page: 0 }
    const countMenus = (menuList) => {
      menuList.forEach(menu => {
        counts.all++
        const countType = menu.type === 'pivot' ? 'pivot-v2' : menu.type
        counts[countType] = (counts[countType] || 0) + 1
        if (menu.children) countMenus(menu.children)
      })
    }
    countMenus(menus)
    return counts
  }, [menus])

  const expandAll = () => {
    const allIds = {}
    const collectIds = (menuList) => {
      menuList.forEach(menu => {
        if (menu.children && menu.children.length > 0) {
          allIds[menu.id] = true
          collectIds(menu.children)
        }
      })
    }
    collectIds(menus)
    setOpenMenus(allIds)
  }

  const collapseAll = () => setOpenMenus({})

  const openCreateModal = (parentId = null) => {
    setEditingMenu(null)
    setFormData({
      parent_id: parentId, nom: '', code: '', icon: 'Folder',
      type: 'folder', target_id: null, url: '', ordre: 0, is_active: true
    })
    setShowModal(true)
  }

  const openEditModal = (menu) => {
    setEditingMenu(menu)
    setFormData({
      parent_id: menu.parent_id, nom: menu.nom, code: menu.code,
      icon: menu.icon || 'Folder',
      type: menu.type === 'pivot' ? 'pivot-v2' : menu.type,
      target_id: menu.target_id, url: menu.url || '',
      ordre: menu.ordre, is_active: menu.is_active
    })
    setShowModal(true)
  }

  const scrollToAndHighlight = useCallback((menuId) => {
    setHighlightedMenuId(menuId)
    setTimeout(() => {
      const element = menuRefs.current[menuId]
      if (element) element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setTimeout(() => setHighlightedMenuId(null), 3000)
    }, 100)
  }, [])

  const handleSave = async () => {
    if (!formData.nom || !formData.code) {
      alert('Nom et code requis')
      return
    }
    setSaving(true)
    try {
      let newMenuId = null
      const parentId = formData.parent_id
      if (editingMenu) {
        await updateMasterMenu(editingMenu.id, formData)
        newMenuId = editingMenu.id
      } else {
        const response = await createMasterMenu(formData)
        if (response.data.success) newMenuId = response.data.id
      }
      setShowModal(false)
      await loadData()
      if (newMenuId && parentId) setOpenMenus(prev => ({ ...prev, [parentId]: true }))
      if (newMenuId) setTimeout(() => scrollToAndHighlight(newMenuId), 200)
    } catch (err) {
      console.error('Erreur sauvegarde:', err)
      alert('Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (menuId) => {
    if (!confirm('Supprimer ce menu maitre?')) return
    try {
      const response = await deleteMasterMenu(menuId)
      if (response.data.success) {
        await loadData()
      } else {
        alert(response.data.error || 'Erreur suppression')
      }
    } catch (err) {
      console.error('Erreur suppression:', err)
      alert('Erreur lors de la suppression')
    }
  }

  // --- Publication ---
  const toggleClientSelection = (clientCode) => {
    setSelectedClients(prev =>
      prev.includes(clientCode) ? prev.filter(c => c !== clientCode) : [...prev, clientCode]
    )
  }

  const selectAllClients = () => {
    if (!syncStatus?.clients) return
    setSelectedClients(syncStatus.clients.map(c => c.code))
  }

  const deselectAllClients = () => setSelectedClients([])

  const handlePublish = async () => {
    if (selectedClients.length === 0) {
      alert('Selectionnez au moins un client')
      return
    }
    // Recuperer tous les codes menus maitre
    const allCodes = []
    const collectCodes = (menuList) => {
      menuList.forEach(menu => {
        if (menu.code) allCodes.push(menu.code)
        if (menu.children) collectCodes(menu.children)
      })
    }
    collectCodes(menus)

    if (allCodes.length === 0) {
      alert('Aucun menu avec code a publier')
      return
    }

    setPublishing(true)
    setPublishResult(null)
    try {
      const response = await publishEntities({
        entities: [{ type: 'menus', codes: allCodes }],
        clients: selectedClients,
        mode: 'upsert'
      })
      setPublishResult(response.data)
      // Recharger le statut
      await loadSyncStatus()
    } catch (err) {
      console.error('Erreur publication:', err)
      setPublishResult({ success: false, error: err.message })
    } finally {
      setPublishing(false)
    }
  }

  const handlePublishAll = async () => {
    if (!confirm('Publier les menus maitre vers TOUS les clients?')) return
    setPublishing(true)
    setPublishResult(null)
    try {
      const response = await publishAllEntities({
        entity_types: ['menus']
      })
      setPublishResult(response.data)
      await loadSyncStatus()
    } catch (err) {
      console.error('Erreur publication:', err)
      setPublishResult({ success: false, error: err.message })
    } finally {
      setPublishing(false)
    }
  }

  const handleCleanupClient = async (clientCode) => {
    if (!confirm(`Nettoyer les menus en double pour le client ${clientCode} ?`)) return
    setCleaningClient(clientCode)
    try {
      const res = await cleanupClientMenus(clientCode)
      setCleanupResults(prev => ({ ...prev, [clientCode]: res.data?.data || res.data }))
      await loadSyncStatus()
    } catch (err) {
      setCleanupResults(prev => ({ ...prev, [clientCode]: { error: err.message } }))
    } finally {
      setCleaningClient(null)
    }
  }

  // --- Render menu tree item ---
  const renderMenuItem = (menu, depth = 0) => {
    const hasChildren = menu.children && menu.children.length > 0
    const isOpen = openMenus[menu.id]
    const isHighlighted = highlightedMenuId === menu.id
    const typeStyle = getTypeStyle(menu.type)
    const childrenCount = menu.children?.length || 0

    return (
      <div key={menu.id} className="group/item">
        <div
          ref={(el) => { menuRefs.current[menu.id] = el }}
          className={`
            flex items-center gap-2 py-2.5 px-3 rounded-lg
            transition-all duration-200 border border-transparent
            ${isHighlighted
              ? 'bg-green-100 dark:bg-green-900/30 ring-2 ring-green-500 ring-opacity-50 border-green-300'
              : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 hover:border-gray-200 dark:hover:border-gray-600'
            }
            ${!menu.is_active ? 'opacity-60' : ''}
            ${menu._matchesSearch === false ? 'opacity-40' : ''}
          `}
          style={{ marginLeft: depth * 24 }}
        >
          {/* Expand/Collapse */}
          <button
            onClick={() => hasChildren && toggleMenu(menu.id)}
            className={`w-5 h-5 flex items-center justify-center rounded transition-colors
              ${hasChildren ? 'hover:bg-gray-200 dark:hover:bg-gray-600' : ''}`}
          >
            {hasChildren ? (
              isOpen ? <ChevronDown className="w-4 h-4 text-gray-500" />
                     : <ChevronRight className="w-4 h-4 text-gray-400" />
            ) : <span className="w-4" />}
          </button>

          {/* Icon */}
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${typeStyle.bg} dark:bg-opacity-20`}>
            <IconComponent name={menu.icon} className={`w-4 h-4 ${typeStyle.color}`} />
          </div>

          {/* Nom */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-medium truncate ${!menu.is_active ? 'line-through text-gray-400' : 'text-gray-900 dark:text-white'}`}>
                {menu.nom}
              </span>
              {hasChildren && (
                <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded-full">
                  {childrenCount}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-gray-400 font-mono">{menu.code}</span>
            </div>
          </div>

          {/* Badges */}
          <div className="flex items-center gap-1.5">
            <span className={`text-xs px-2 py-1 rounded-md font-medium ${typeStyle.bg} ${typeStyle.color} dark:bg-opacity-20`}>
              {typeStyle.label}
            </span>
            {!menu.is_active && (
              <span className="text-xs text-orange-600 dark:text-orange-400 px-2 py-1 bg-orange-100 dark:bg-orange-900/30 rounded-md flex items-center gap-1">
                <EyeOff className="w-3 h-3" />
                Masque
              </span>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-0.5 opacity-0 group-hover/item:opacity-100 transition-opacity">
            <button
              onClick={() => openCreateModal(menu.id)}
              className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
              title="Ajouter un sous-menu"
            >
              <Plus className="w-4 h-4 text-gray-500" />
            </button>
            <button
              onClick={() => openEditModal(menu)}
              className="p-1.5 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-md transition-colors"
              title="Modifier"
            >
              <Edit2 className="w-4 h-4 text-blue-500" />
            </button>
            <button
              onClick={() => handleDelete(menu.id)}
              className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-md transition-colors"
              title="Supprimer"
            >
              <Trash2 className="w-4 h-4 text-red-500" />
            </button>
          </div>
        </div>

        {/* Children */}
        {hasChildren && isOpen && (
          <div className="relative">
            <div
              className="absolute left-[22px] top-0 bottom-2 w-px bg-gray-200 dark:bg-gray-700"
              style={{ marginLeft: depth * 24 }}
            />
            {menu.children.map(child => renderMenuItem(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  // --- Render sync status badge ---
  const getStatusBadge = (status) => {
    switch (status) {
      case 'synced':
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 font-medium">
            <CheckCircle className="w-3.5 h-3.5" /> Synchronise
          </span>
        )
      case 'partial':
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 font-medium">
            <AlertCircle className="w-3.5 h-3.5" /> Partiel
          </span>
        )
      case 'outdated':
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 font-medium">
            <AlertTriangle className="w-3.5 h-3.5" /> Obsolete
          </span>
        )
      case 'error':
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 font-medium">
            <XCircle className="w-3.5 h-3.5" /> Erreur
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-500 font-medium">
            Inconnu
          </span>
        )
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-slate-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Globe className="w-6 h-6 text-indigo-500" />
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                Menus Maitre
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Base centrale — Publication vers les clients
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('structure')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'structure'
                  ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
              }`}
            >
              <Folder className="w-4 h-4 inline mr-2" />
              Structure
            </button>
            <button
              onClick={() => setActiveTab('publish')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'publish'
                  ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
              }`}
            >
              <Send className="w-4 h-4 inline mr-2" />
              Publication
            </button>
          </div>
        </div>
      </div>

      {/* Contenu */}
      <div className="flex-1 p-6 overflow-auto">
        {activeTab === 'structure' ? (
          /* ==================== ONGLET STRUCTURE ==================== */
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm">
            {/* Barre d'outils */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Globe className="w-5 h-5 text-indigo-500" />
                  Arborescence Maitre
                  <span className="text-sm font-normal text-gray-400">
                    ({menuCounts.all} elements)
                  </span>
                </h2>
                <button
                  onClick={() => openCreateModal(null)}
                  className="btn-primary flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Nouveau Menu
                </button>
              </div>

              {/* Recherche et filtres */}
              <div className="flex items-center gap-3 flex-wrap">
                <div className="relative flex-1 min-w-[200px] max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Rechercher un menu..."
                    className="w-full pl-10 pr-4 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg
                             bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  {searchQuery && (
                    <button onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                  <button
                    onClick={() => setFilterType('all')}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      filterType === 'all'
                        ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
                    }`}
                  >
                    Tous ({menuCounts.all})
                  </button>
                  {MENU_TYPES.map(type => (
                    <button
                      key={type.value}
                      onClick={() => setFilterType(type.value)}
                      className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center gap-1 ${
                        filterType === type.value
                          ? `bg-white dark:bg-gray-600 shadow-sm ${type.color}`
                          : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
                      }`}
                    >
                      {type.label} ({menuCounts[type.value] || 0})
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => setShowInactive(!showInactive)}
                  className={`flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                    showInactive
                      ? 'bg-gray-100 dark:bg-gray-700 border-primary-300 dark:border-primary-600 text-gray-700 dark:text-gray-300'
                      : 'bg-orange-100 border-orange-300 text-orange-700'
                  }`}
                >
                  {showInactive ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  {showInactive ? 'Inactifs visibles' : 'Inactifs masques'}
                </button>

                <div className="flex items-center gap-1 border-l border-primary-300 dark:border-primary-600 pl-3">
                  <button onClick={expandAll}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    title="Tout deployer">
                    <FolderOpen className="w-4 h-4 text-gray-500" />
                  </button>
                  <button onClick={collapseAll}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    title="Tout replier">
                    <Folder className="w-4 h-4 text-gray-500" />
                  </button>
                  <button onClick={loadData}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    title="Rafraichir">
                    <RefreshCw className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              </div>
            </div>

            {/* Liste des menus */}
            <div className="p-4">
              {menus.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Globe className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Aucun menu maitre configure</p>
                  <button onClick={() => openCreateModal(null)}
                    className="mt-4 text-indigo-600 hover:underline">
                    Creer le premier menu maitre
                  </button>
                </div>
              ) : filteredMenus.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Search className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Aucun menu ne correspond a votre recherche</p>
                  <button onClick={() => { setSearchQuery(''); setFilterType('all') }}
                    className="mt-4 text-indigo-600 hover:underline">
                    Reinitialiser les filtres
                  </button>
                </div>
              ) : (
                <div className="space-y-0.5">
                  {filteredMenus.map(menu => renderMenuItem(menu))}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* ==================== ONGLET PUBLICATION ==================== */
          <div className="space-y-6">
            {/* Resume Maitre */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Globe className="w-5 h-5 text-indigo-500" />
                  Resume des menus maitre
                </h2>
                <button
                  onClick={loadSyncStatus}
                  disabled={loadingSyncStatus}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <RefreshCw className={`w-4 h-4 ${loadingSyncStatus ? 'animate-spin' : ''}`} />
                  Actualiser
                </button>
              </div>

              {syncStatus && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-indigo-50 dark:bg-indigo-900/20 p-4 rounded-xl text-center">
                    <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                      {syncStatus.master_count || 0}
                    </div>
                    <div className="text-sm text-indigo-600/70 dark:text-indigo-400/70">Menus maitre</div>
                  </div>
                  <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-xl text-center">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {syncStatus.clients?.filter(c => c.status === 'synced').length || 0}
                    </div>
                    <div className="text-sm text-green-600/70 dark:text-green-400/70">Clients synchronises</div>
                  </div>
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-xl text-center">
                    <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                      {syncStatus.clients?.filter(c => c.status === 'partial').length || 0}
                    </div>
                    <div className="text-sm text-yellow-600/70 dark:text-yellow-400/70">Partiellement synced</div>
                  </div>
                  <div className="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-xl text-center">
                    <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                      {syncStatus.clients?.filter(c => c.status === 'outdated').length || 0}
                    </div>
                    <div className="text-sm text-orange-600/70 dark:text-orange-400/70">Obsoletes</div>
                  </div>
                </div>
              )}
            </div>

            {/* Tableau des clients */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                    <Database className="w-5 h-5 text-indigo-500" />
                    Statut par client
                  </h2>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={selectAllClients}
                      className="text-xs text-indigo-600 hover:underline"
                    >
                      Tout selectionner
                    </button>
                    <span className="text-gray-300">|</span>
                    <button
                      onClick={deselectAllClients}
                      className="text-xs text-gray-500 hover:underline"
                    >
                      Deselectionner
                    </button>
                  </div>
                </div>
              </div>

              {loadingSyncStatus ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
                </div>
              ) : syncStatus?.clients?.length > 0 ? (
                <div className="divide-y divide-gray-100 dark:divide-gray-700">
                  {syncStatus.clients.map(client => (
                    <div key={client.code}>
                    <div
                      className={`flex items-center gap-4 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                        selectedClients.includes(client.code) ? 'bg-indigo-50/50 dark:bg-indigo-900/10' : ''
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedClients.includes(client.code)}
                        onChange={() => toggleClientSelection(client.code)}
                        className="rounded border-primary-300 text-indigo-600 focus:ring-indigo-500"
                      />

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900 dark:text-white text-sm">
                            {client.nom}
                          </span>
                          <span className="text-xs text-gray-400 font-mono">{client.code}</span>
                        </div>
                      </div>

                      {/* Stats */}
                      <div className="flex items-center gap-3 text-xs">
                        {client.status !== 'error' && (
                          <>
                            <span className="text-green-600" title="Synchronises">
                              <CheckCircle className="w-3.5 h-3.5 inline mr-1" />{client.synced}
                            </span>
                            <span className="text-yellow-600" title="Personnalises (proteges)">
                              <Lock className="w-3.5 h-3.5 inline mr-1" />{client.customized}
                            </span>
                            <span className="text-red-600" title="Manquants">
                              <XCircle className="w-3.5 h-3.5 inline mr-1" />{client.missing}
                            </span>
                            {client.client_only > 0 && (
                              <span className="text-blue-600" title="Locaux uniquement">
                                <Plus className="w-3.5 h-3.5 inline mr-1" />{client.client_only}
                              </span>
                            )}
                          </>
                        )}
                      </div>

                      {getStatusBadge(client.status)}

                      {/* Bouton nettoyer */}
                      <button
                        onClick={() => handleCleanupClient(client.code)}
                        disabled={cleaningClient === client.code}
                        title="Supprimer les menus en double dans cette base client"
                        className="ml-2 flex items-center gap-1 px-2 py-1 text-xs font-medium text-orange-700 bg-orange-50 border border-orange-200 rounded hover:bg-orange-100 disabled:opacity-50 transition-colors dark:text-orange-300 dark:bg-orange-900/20 dark:border-orange-700"
                      >
                        {cleaningClient === client.code
                          ? <Loader2 className="w-3 h-3 animate-spin" />
                          : <RefreshCw className="w-3 h-3" />
                        }
                        Nettoyer
                      </button>
                    </div>

                    {/* Résultat nettoyage */}
                    {cleanupResults[client.code] && (
                      <div className={`mx-4 mb-2 px-3 py-2 rounded-lg text-xs ${
                        cleanupResults[client.code].error
                          ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
                          : 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                      }`}>
                        {cleanupResults[client.code].error
                          ? `Erreur : ${cleanupResults[client.code].error}`
                          : `Nettoyage OK — ${cleanupResults[client.code].total_supprime} supprimé(s) `
                            + `(doublons: ${cleanupResults[client.code].supprimes_doublons}, `
                            + `vides: ${cleanupResults[client.code].supprimes_vides}) `
                            + `| ${cleanupResults[client.code].apres} menus restants`
                        }
                      </div>
                    )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <Database className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Aucun client configure</p>
                </div>
              )}

              {/* Actions de publication */}
              {syncStatus?.clients?.length > 0 && (
                <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-500">
                      {selectedClients.length} client(s) selectionne(s)
                    </p>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={handlePublishAll}
                        disabled={publishing}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white dark:bg-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                      >
                        {publishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        Publier vers tous
                      </button>
                      <button
                        onClick={handlePublish}
                        disabled={publishing || selectedClients.length === 0}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors disabled:opacity-50"
                      >
                        {publishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        Publier vers selection
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Resultat de publication */}
            {publishResult && (
              <div className={`rounded-xl shadow-sm p-6 ${
                publishResult.success !== false
                  ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                  : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
              }`}>
                <h3 className={`font-semibold mb-3 flex items-center gap-2 ${
                  publishResult.success !== false ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'
                }`}>
                  {publishResult.success !== false
                    ? <><CheckCircle className="w-5 h-5" /> Publication terminee</>
                    : <><XCircle className="w-5 h-5" /> Erreur de publication</>
                  }
                </h3>

                {publishResult.error ? (
                  <p className="text-sm text-red-600">{publishResult.error}</p>
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-green-700 dark:text-green-400">
                        <Plus className="w-4 h-4 inline mr-1" />{publishResult.total_published || 0} inseres
                      </span>
                      <span className="text-blue-700 dark:text-blue-400">
                        <RefreshCw className="w-4 h-4 inline mr-1" />{publishResult.total_updated || 0} mis a jour
                      </span>
                      {publishResult.total_failed > 0 && (
                        <span className="text-red-700 dark:text-red-400">
                          <XCircle className="w-4 h-4 inline mr-1" />{publishResult.total_failed} erreurs
                        </span>
                      )}
                    </div>

                    {/* Details par client */}
                    {publishResult.details && publishResult.details.length > 0 && (
                      <div className="mt-3 space-y-1">
                        {publishResult.details
                          .filter(d => d.entity_type === 'menus')
                          .map((detail, idx) => (
                          <div key={idx} className="flex items-center gap-3 text-xs bg-white/50 dark:bg-gray-800/50 px-3 py-2 rounded-lg">
                            <span className="font-medium text-gray-700 dark:text-gray-300 min-w-[120px]">
                              {detail.client_nom || detail.client_code}
                            </span>
                            <span className="text-green-600">+{detail.published}</span>
                            <span className="text-blue-600">~{detail.updated}</span>
                            {detail.failed > 0 && <span className="text-red-600">x{detail.failed}</span>}
                            {detail.errors?.length > 0 && (
                              <span className="text-red-500 text-xs truncate">{detail.errors[0]}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal creation/edition */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowModal(false)} />
          <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                {editingMenu ? 'Modifier le menu maitre' : 'Nouveau menu maitre'}
              </h2>
              <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom *</label>
                  <input type="text" value={formData.nom}
                    onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                    className="input" placeholder="Ex: Analyse Ventes" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Code *</label>
                  <input type="text" value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                    className="input" placeholder="Ex: analyse-ventes" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Parent</label>
                  <select value={formData.parent_id || ''}
                    onChange={(e) => setFormData({ ...formData, parent_id: e.target.value ? parseInt(e.target.value) : null })}
                    className="input">
                    <option value="">-- Racine --</option>
                    {flatMenus.filter(m => m.id !== editingMenu?.id).map(m => (
                      <option key={m.id} value={m.id}>
                        {m.parent_name ? `${m.parent_name} > ` : ''}{m.nom}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Type</label>
                  <select value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value, target_id: null })}
                    className="input">
                    {MENU_TYPES.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {(formData.type === 'pivot-v2' || formData.type === 'gridview' || formData.type === 'dashboard') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {formData.type === 'pivot-v2' ? 'Pivot Table' :
                     formData.type === 'gridview' ? 'GridView' : 'Dashboard'}
                  </label>
                  <select value={formData.target_id || ''}
                    onChange={(e) => setFormData({ ...formData, target_id: e.target.value ? parseInt(e.target.value) : null })}
                    className="input">
                    <option value="">-- Selectionner --</option>
                    {targets.map(t => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>
              )}

              {formData.type === 'page' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">URL</label>
                  <input type="text" value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    className="input" placeholder="Ex: /ventes" />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Icone</label>
                  <select value={formData.icon}
                    onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                    className="input">
                    {ICONS.map(i => (
                      <option key={i.value} value={i.value}>{i.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ordre</label>
                  <input type="number" value={formData.ordre}
                    onChange={(e) => setFormData({ ...formData, ordre: parseInt(e.target.value) || 0 })}
                    className="input" />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" id="is_active_master" checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="rounded border-primary-300" />
                <label htmlFor="is_active_master" className="text-sm text-gray-700 dark:text-gray-300">
                  Menu actif
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button onClick={() => setShowModal(false)} className="btn-secondary">Annuler</button>
              <button onClick={handleSave} disabled={saving} className="btn-primary">
                {saving ? 'Enregistrement...' : (editingMenu ? 'Modifier' : 'Creer')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
