import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import {
  Plus, Save, Trash2, Edit2, X, ChevronRight, ChevronDown,
  Folder, Table, Table2, LayoutDashboard, FileSpreadsheet, Link,
  Users, Check, Search, GripVertical, Settings, Lock, Filter,
  Eye, EyeOff, RefreshCw, MoreVertical, Copy, FolderOpen, Download, Globe,
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
  getAllMenus, getMenusFlat, createMenu, updateMenu, deleteMenu,
  getMenuTargets, getUsers, getUserMenuAccess, setBulkUserMenuAccess,
  pullBuilderMenus
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

// Fonction pour obtenir le style du type
const getTypeStyle = (type) => {
  const lookupType = type === 'pivot' ? 'pivot-v2' : type
  const typeInfo = MENU_TYPES.find(t => t.value === lookupType)
  return typeInfo || { color: 'text-gray-600', bg: 'bg-gray-100', label: type }
}

const IconComponent = ({ name, className }) => {
  const iconMap = {
    // Generiques
    Folder, FolderOpen, Table2, LayoutDashboard, FileSpreadsheet, Link, Users, Database,
    Settings, Table,
    // Documents
    FileText, Receipt, ClipboardList, FileQuestion, Truck, PackageCheck, RotateCcw,
    // Ventes & Commerce
    ShoppingCart, ShoppingBag, Target, Crosshair,
    // Analyse
    BarChart3, BarChart2, LineChart, PieChart, TrendingUp, TrendingDown, Activity,
    GitCompare, ArrowUpDown,
    // Finance
    Wallet, DollarSign, CircleDollarSign, CreditCard, BadgePercent, Percent, Scale,
    // Logistique
    Package, Boxes,
    // Geographie
    MapPin, Layers,
    // Clients
    UserCheck, UserX, User, Star, Award,
    // Alertes & Temps
    AlertTriangle, Clock, Zap, Gauge,
    // Divers
    Repeat, Filter, ArrowRightLeft, Calendar, Mail,
  }

  const Icon = iconMap[name]
  if (Icon) {
    return <Icon className={className} />
  }

  return <Folder className={className} />
}

export default function MenuManagement() {
  const [menus, setMenus] = useState([])
  const [flatMenus, setFlatMenus] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('structure') // structure, access

  // Modal edition
  const [showModal, setShowModal] = useState(false)
  const [editingMenu, setEditingMenu] = useState(null)
  const [formData, setFormData] = useState({
    parent_id: null,
    nom: '',
    code: '',
    icon: 'Folder',
    type: 'folder',
    target_id: null,
    url: '',
    ordre: 0,
    is_active: true
  })
  const [targets, setTargets] = useState([])
  const [saving, setSaving] = useState(false)

  // Droits utilisateurs
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState(null)
  const [userAccess, setUserAccess] = useState([])
  const [selectedMenuIds, setSelectedMenuIds] = useState([])
  const [savingAccess, setSavingAccess] = useState(false)

  // Menus ouverts
  const [openMenus, setOpenMenus] = useState({})

  // Pour le highlight et scroll après création
  const [highlightedMenuId, setHighlightedMenuId] = useState(null)
  const menuRefs = useRef({})

  // Recherche et filtres
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [showInactive, setShowInactive] = useState(true)

  // Pull depuis base maître
  const [pulling, setPulling] = useState(false)
  const [pullResult, setPullResult] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (formData.type && formData.type !== 'folder' && formData.type !== 'page') {
      loadTargets(formData.type)
    }
  }, [formData.type])

  useEffect(() => {
    if (selectedUser) {
      loadUserAccess(selectedUser.id)
    }
  }, [selectedUser])

  const loadData = async () => {
    setLoading(true)
    try {
      const [menusRes, flatRes, usersRes] = await Promise.all([
        getAllMenus(),
        getMenusFlat(),
        getUsers()
      ])
      setMenus(menusRes.data.data || [])
      setFlatMenus(flatRes.data.data || [])
      setUsers(usersRes.data.data || [])
    } catch (err) {
      console.error('Erreur chargement:', err)
    } finally {
      setLoading(false)
    }
  }

  const handlePullFromMaster = async () => {
    setPulling(true)
    setPullResult(null)
    try {
      const res = await pullBuilderMenus()
      const data = res.data || {}
      setPullResult({
        success: true,
        applied: data.applied || 0,
        errors: data.errors || []
      })
      // Recharger les menus après pull
      await loadData()
    } catch (err) {
      setPullResult({
        success: false,
        message: err?.response?.data?.detail || 'Erreur lors de la récupération'
      })
    } finally {
      setPulling(false)
      // Effacer le message après 5 secondes
      setTimeout(() => setPullResult(null), 5000)
    }
  }

  const loadTargets = async (type) => {
    try {
      const response = await getMenuTargets(type)
      setTargets(response.data.data || [])
    } catch (err) {
      console.error('Erreur chargement targets:', err)
      setTargets([])
    }
  }

  const loadUserAccess = async (userId) => {
    try {
      const response = await getUserMenuAccess(userId)
      const accessList = response.data.data || []
      setUserAccess(accessList)
      setSelectedMenuIds(accessList.map(a => a.menu_id))
    } catch (err) {
      console.error('Erreur chargement acces:', err)
      setUserAccess([])
      setSelectedMenuIds([])
    }
  }

  const toggleMenu = (menuId) => {
    setOpenMenus(prev => ({ ...prev, [menuId]: !prev[menuId] }))
  }

  // Fonction de filtrage des menus
  const filterMenus = useCallback((menuList, query, type, showInactiveMenus) => {
    const filterMenu = (menu) => {
      // Vérifier le menu actuel
      const matchesSearch = !query ||
        menu.nom.toLowerCase().includes(query.toLowerCase()) ||
        menu.code.toLowerCase().includes(query.toLowerCase())
      const matchesType = type === 'all' || menu.type === type || (type === 'pivot-v2' && menu.type === 'pivot')
      const matchesActive = showInactiveMenus || menu.is_active

      // Filtrer les enfants récursivement
      const filteredChildren = menu.children
        ? menu.children.map(filterMenu).filter(Boolean)
        : []

      // Inclure le menu si lui-même correspond ou s'il a des enfants qui correspondent
      if ((matchesSearch && matchesType && matchesActive) || filteredChildren.length > 0) {
        return {
          ...menu,
          children: filteredChildren,
          _matchesSearch: matchesSearch && matchesType && matchesActive
        }
      }
      return null
    }

    return menuList.map(filterMenu).filter(Boolean)
  }, [])

  // Menus filtrés
  const filteredMenus = useMemo(() => {
    return filterMenus(menus, searchQuery, filterType, showInactive)
  }, [menus, searchQuery, filterType, showInactive, filterMenus])

  // Compter les menus par type
  const menuCounts = useMemo(() => {
    const counts = { all: 0, folder: 0, 'pivot-v2': 0, gridview: 0, dashboard: 0, page: 0 }
    const countMenus = (menuList) => {
      menuList.forEach(menu => {
        counts.all++
        // Compter les anciens pivot sous pivot-v2
        const countType = menu.type === 'pivot' ? 'pivot-v2' : menu.type
        counts[countType] = (counts[countType] || 0) + 1
        if (menu.children) countMenus(menu.children)
      })
    }
    countMenus(menus)
    return counts
  }, [menus])

  // Ouvrir/fermer tous les menus
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

  const collapseAll = () => {
    setOpenMenus({})
  }

  const openCreateModal = (parentId = null) => {
    setEditingMenu(null)
    setFormData({
      parent_id: parentId,
      nom: '',
      code: '',
      icon: 'Folder',
      type: 'folder',
      target_id: null,
      url: '',
      ordre: 0,
      is_active: true
    })
    setShowModal(true)
  }

  const openEditModal = (menu) => {
    setEditingMenu(menu)
    setFormData({
      parent_id: menu.parent_id,
      nom: menu.nom,
      code: menu.code,
      icon: menu.icon || 'Folder',
      type: menu.type === 'pivot' ? 'pivot-v2' : menu.type,
      target_id: menu.target_id,
      url: menu.url || '',
      ordre: menu.ordre,
      is_active: menu.is_active
    })
    setShowModal(true)
  }

  // Fonction pour ouvrir tous les parents d'un menu
  const openParentPath = useCallback((menuId, menusList) => {
    const findParentPath = (id, menus, path = []) => {
      for (const menu of menus) {
        if (menu.id === id) {
          return path
        }
        if (menu.children && menu.children.length > 0) {
          const found = findParentPath(id, menu.children, [...path, menu.id])
          if (found) return found
        }
      }
      return null
    }

    const parentPath = findParentPath(menuId, menusList)
    if (parentPath && parentPath.length > 0) {
      const newOpenMenus = { ...openMenus }
      parentPath.forEach(id => {
        newOpenMenus[id] = true
      })
      setOpenMenus(newOpenMenus)
    }
  }, [openMenus])

  // Fonction pour scroller vers un menu et le highlighter
  const scrollToAndHighlight = useCallback((menuId) => {
    setHighlightedMenuId(menuId)

    // Attendre que le DOM soit mis à jour
    setTimeout(() => {
      const element = menuRefs.current[menuId]
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }

      // Retirer le highlight après 3 secondes
      setTimeout(() => {
        setHighlightedMenuId(null)
      }, 3000)
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
        await updateMenu(editingMenu.id, formData)
        newMenuId = editingMenu.id
      } else {
        const response = await createMenu(formData)
        if (response.data.success) {
          newMenuId = response.data.id
        }
      }

      setShowModal(false)
      await loadData()

      // Si création d'un sous-menu, ouvrir le parent
      if (newMenuId && parentId) {
        setOpenMenus(prev => ({ ...prev, [parentId]: true }))
      }

      // Scroller vers le nouveau menu et le highlighter
      if (newMenuId) {
        // Attendre que les menus soient rechargés
        setTimeout(() => {
          scrollToAndHighlight(newMenuId)
        }, 200)
      }
    } catch (err) {
      console.error('Erreur sauvegarde:', err)
      alert('Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (menuId) => {
    if (!confirm('Supprimer ce menu?')) return

    try {
      const response = await deleteMenu(menuId)
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

  const toggleMenuAccess = (menuId) => {
    setSelectedMenuIds(prev =>
      prev.includes(menuId)
        ? prev.filter(id => id !== menuId)
        : [...prev, menuId]
    )
  }

  const saveUserAccess = async () => {
    if (!selectedUser) return

    setSavingAccess(true)
    try {
      await setBulkUserMenuAccess({
        user_id: selectedUser.id,
        menu_ids: selectedMenuIds,
        can_export: false
      })
      alert('Droits sauvegardés!')
    } catch (err) {
      console.error('Erreur sauvegarde acces:', err)
      alert('Erreur lors de la sauvegarde')
    } finally {
      setSavingAccess(false)
    }
  }

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
            ${depth > 0 ? '' : ''}
            ${isHighlighted
              ? 'bg-green-100 dark:bg-green-900/30 ring-2 ring-green-500 ring-opacity-50 border-green-300'
              : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 hover:border-gray-200 dark:hover:border-gray-600'
            }
            ${!menu.is_active ? 'opacity-60' : ''}
            ${menu._matchesSearch === false ? 'opacity-40' : ''}
          `}
          style={{ marginLeft: depth * 24 }}
        >
          {/* Expand/Collapse button */}
          <button
            onClick={() => hasChildren && toggleMenu(menu.id)}
            className={`w-5 h-5 flex items-center justify-center rounded transition-colors
              ${hasChildren ? 'hover:bg-gray-200 dark:hover:bg-gray-600' : ''}
            `}
          >
            {hasChildren ? (
              isOpen
                ? <ChevronDown className="w-4 h-4 text-gray-500" />
                : <ChevronRight className="w-4 h-4 text-gray-400" />
            ) : <span className="w-4" />}
          </button>

          {/* Icon avec couleur selon type */}
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${typeStyle.bg} dark:bg-opacity-20`}>
            <IconComponent name={menu.icon} className={`w-4 h-4 ${typeStyle.color}`} />
          </div>

          {/* Nom du menu */}
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
              {menu.target_name && (
                <span className="text-xs text-primary-500 dark:text-primary-400 truncate">
                  → {menu.target_name}
                </span>
              )}
            </div>
          </div>

          {/* Badges */}
          {(() => {
            const isStandard = !menu.is_custom
            return (
              <>
                <div className="flex items-center gap-1.5">
                  {/* Badge type */}
                  <span className={`text-xs px-2 py-1 rounded-md font-medium ${typeStyle.bg} ${typeStyle.color} dark:bg-opacity-20`}>
                    {typeStyle.label}
                  </span>

                  {/* Badge standard (protégé) */}
                  {isStandard && (
                    <span className="text-xs text-blue-600 dark:text-blue-400 px-2 py-1 bg-blue-50 dark:bg-blue-900/20 rounded-md flex items-center gap-1 font-medium border border-blue-200 dark:border-blue-700">
                      <Lock className="w-3 h-3" />
                      Standard
                    </span>
                  )}

                  {/* Badge inactif */}
                  {!menu.is_active && (
                    <span className="text-xs text-orange-600 dark:text-orange-400 px-2 py-1 bg-orange-100 dark:bg-orange-900/30 rounded-md flex items-center gap-1">
                      <EyeOff className="w-3 h-3" />
                      Masque
                    </span>
                  )}
                </div>

                {/* Actions - visibles au hover */}
                <div className="flex items-center gap-0.5 opacity-0 group-hover/item:opacity-100 transition-opacity">
                  <button
                    onClick={() => openCreateModal(menu.id)}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
                    title="Ajouter un sous-menu"
                  >
                    <Plus className="w-4 h-4 text-gray-500" />
                  </button>

                  {/* Modifier */}
                  {isStandard ? (
                    <span className="p-1.5 rounded-md cursor-not-allowed" title="Menu standard — modification impossible">
                      <Edit2 className="w-4 h-4 text-gray-300 dark:text-gray-600" />
                    </span>
                  ) : (
                    <button
                      onClick={() => openEditModal(menu)}
                      className="p-1.5 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-md transition-colors"
                      title="Modifier ce menu"
                    >
                      <Edit2 className="w-4 h-4 text-blue-500" />
                    </button>
                  )}

                  {/* Supprimer */}
                  {isStandard ? (
                    <span className="p-1.5 rounded-md cursor-not-allowed" title="Menu standard — suppression impossible">
                      <Trash2 className="w-4 h-4 text-gray-300 dark:text-gray-600" />
                    </span>
                  ) : (
                    <button
                      onClick={() => handleDelete(menu.id)}
                      className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-md transition-colors"
                      title="Supprimer ce menu"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  )}
                </div>
              </>
            )
          })()}
        </div>

        {/* Enfants */}
        {hasChildren && isOpen && (
          <div className="relative">
            {/* Ligne verticale de connexion */}
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

  const renderAccessMenuItem = (menu, depth = 0) => {
    const hasChildren = menu.children && menu.children.length > 0
    const isOpen = openMenus[menu.id]
    const isSelected = selectedMenuIds.includes(menu.id)

    return (
      <div key={menu.id}>
        <div
          className="flex items-center gap-2 py-1.5 px-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded"
          style={{ marginLeft: depth * 20 }}
        >
          <button
            onClick={() => hasChildren && toggleMenu(menu.id)}
            className="w-4 h-4 flex items-center justify-center"
          >
            {hasChildren ? (
              isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />
            ) : null}
          </button>

          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => toggleMenuAccess(menu.id)}
            className="rounded border-primary-300"
          />

          <IconComponent name={menu.icon} className="w-4 h-4 text-gray-500" />
          <span className="text-sm">{menu.nom}</span>
        </div>

        {hasChildren && isOpen && (
          <div>
            {menu.children.map(child => renderAccessMenuItem(child, depth + 1))}
          </div>
        )}
      </div>
    )
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
            <Settings className="w-6 h-6 text-primary-500" />
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              Gestion des Menus
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Bouton récupérer depuis base maître */}
            <button
              onClick={handlePullFromMaster}
              disabled={pulling}
              title="Récupérer les menus depuis la base maître (serveur central)"
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 disabled:opacity-50 disabled:cursor-not-allowed dark:text-green-300 dark:bg-green-900/20 dark:border-green-700 dark:hover:bg-green-900/40 transition-colors"
            >
              {pulling
                ? <><RefreshCw className="w-4 h-4 animate-spin" /> Récupération...</>
                : <><Globe className="w-4 h-4" /> Récupérer base maître</>
              }
            </button>

            {/* Message résultat pull */}
            {pullResult && (
              <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                pullResult.success
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
              }`}>
                {pullResult.success
                  ? `✓ ${pullResult.applied} élément(s) synchronisé(s)`
                  : `✗ ${pullResult.message}`
                }
              </span>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('structure')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'structure'
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
              }`}
            >
              <Folder className="w-4 h-4 inline mr-2" />
              Structure
            </button>
            <button
              onClick={() => setActiveTab('access')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'access'
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
              }`}
            >
              <Users className="w-4 h-4 inline mr-2" />
              Droits d'acces
            </button>
          </div>
        </div>
      </div>

      {/* Contenu */}
      <div className="flex-1 p-6 overflow-auto">
        {activeTab === 'structure' ? (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm">
            {/* Barre d'outils avec recherche et filtres */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 space-y-3">
              {/* Ligne 1: Titre et bouton */}
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Folder className="w-5 h-5 text-primary-500" />
                  Arborescence des menus
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

              {/* Ligne 2: Recherche et filtres */}
              <div className="flex items-center gap-3 flex-wrap">
                {/* Recherche */}
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
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Filtres par type */}
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

                {/* Toggle afficher inactifs */}
                <button
                  onClick={() => setShowInactive(!showInactive)}
                  className={`flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                    showInactive
                      ? 'bg-gray-100 dark:bg-gray-700 border-primary-300 dark:border-primary-600 text-gray-700 dark:text-gray-300'
                      : 'bg-orange-100 border-orange-300 text-orange-700'
                  }`}
                  title={showInactive ? 'Masquer les menus inactifs' : 'Afficher les menus inactifs'}
                >
                  {showInactive ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  {showInactive ? 'Inactifs visibles' : 'Inactifs masques'}
                </button>

                {/* Expand/Collapse all */}
                <div className="flex items-center gap-1 border-l border-primary-300 dark:border-primary-600 pl-3">
                  <button
                    onClick={expandAll}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    title="Tout deployer"
                  >
                    <FolderOpen className="w-4 h-4 text-gray-500" />
                  </button>
                  <button
                    onClick={collapseAll}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    title="Tout replier"
                  >
                    <Folder className="w-4 h-4 text-gray-500" />
                  </button>
                  <button
                    onClick={loadData}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    title="Rafraichir"
                  >
                    <RefreshCw className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              </div>
            </div>

            {/* Liste des menus */}
            <div className="p-4">
              {menus.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Folder className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Aucun menu configure</p>
                  <button
                    onClick={() => openCreateModal(null)}
                    className="mt-4 text-primary-600 hover:underline"
                  >
                    Creer le premier menu
                  </button>
                </div>
              ) : filteredMenus.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Search className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Aucun menu ne correspond a votre recherche</p>
                  <button
                    onClick={() => { setSearchQuery(''); setFilterType('all'); }}
                    className="mt-4 text-primary-600 hover:underline"
                  >
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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Liste utilisateurs */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="font-semibold text-gray-900 dark:text-white">
                  Utilisateurs
                </h2>
              </div>
              <div className="p-4 max-h-[600px] overflow-y-auto">
                {users.map(user => (
                  <div
                    key={user.id}
                    onClick={() => setSelectedUser(user)}
                    className={`
                      flex items-center gap-3 p-3 rounded-lg cursor-pointer mb-2
                      ${selectedUser?.id === user.id
                        ? 'bg-primary-100 dark:bg-primary-900/30 border border-primary-300'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-700 border border-transparent'
                      }
                    `}
                  >
                    <div className="w-10 h-10 rounded-full bg-primary-500 flex items-center justify-center text-white font-bold">
                      {user.nom?.charAt(0) || user.username?.charAt(0) || '?'}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 dark:text-white">
                        {user.nom || user.username}
                      </p>
                      <p className="text-xs text-gray-500">{user.username}</p>
                    </div>
                    {user.is_admin && (
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">
                        Admin
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Droits menus */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <h2 className="font-semibold text-gray-900 dark:text-white">
                  {selectedUser ? `Menus de ${selectedUser.nom || selectedUser.username}` : 'Selectionnez un utilisateur'}
                </h2>
                {selectedUser && !selectedUser.is_admin && (
                  <button
                    onClick={saveUserAccess}
                    disabled={savingAccess}
                    className="btn-primary flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" />
                    {savingAccess ? 'Enregistrement...' : 'Enregistrer'}
                  </button>
                )}
              </div>
              <div className="p-4 max-h-[600px] overflow-y-auto">
                {!selectedUser ? (
                  <p className="text-gray-500 text-center py-8">
                    Selectionnez un utilisateur pour gerer ses droits
                  </p>
                ) : selectedUser.is_admin ? (
                  <div className="text-center py-8">
                    <Check className="w-12 h-12 mx-auto text-green-500 mb-3" />
                    <p className="text-gray-600 dark:text-gray-400">
                      Cet utilisateur est administrateur.<br />
                      Il a acces a tous les menus.
                    </p>
                  </div>
                ) : menus.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">
                    Aucun menu configure
                  </p>
                ) : (
                  <div className="space-y-1">
                    {menus.map(menu => renderAccessMenuItem(menu))}
                  </div>
                )}
              </div>
            </div>
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
                {editingMenu ? 'Modifier le menu' : 'Nouveau menu'}
              </h2>
              <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Nom *
                  </label>
                  <input
                    type="text"
                    value={formData.nom}
                    onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                    className="input"
                    placeholder="Ex: Analyse Ventes"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Code *
                  </label>
                  <input
                    type="text"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                    className="input"
                    placeholder="Ex: analyse-ventes"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Parent
                  </label>
                  <select
                    value={formData.parent_id || ''}
                    onChange={(e) => setFormData({ ...formData, parent_id: e.target.value ? parseInt(e.target.value) : null })}
                    className="input"
                  >
                    <option value="">-- Racine --</option>
                    {flatMenus.filter(m => m.id !== editingMenu?.id).map(m => (
                      <option key={m.id} value={m.id}>
                        {m.parent_name ? `${m.parent_name} > ` : ''}{m.nom}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Type
                  </label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value, target_id: null })}
                    className="input"
                  >
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
                  <select
                    value={formData.target_id || ''}
                    onChange={(e) => setFormData({ ...formData, target_id: e.target.value ? parseInt(e.target.value) : null })}
                    className="input"
                  >
                    <option value="">-- Selectionner --</option>
                    {targets.map(t => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>
              )}

              {formData.type === 'page' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    URL
                  </label>
                  <input
                    type="text"
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    className="input"
                    placeholder="Ex: /ventes"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Icone
                  </label>
                  <select
                    value={formData.icon}
                    onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                    className="input"
                  >
                    {ICONS.map(i => (
                      <option key={i.value} value={i.value}>{i.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Ordre
                  </label>
                  <input
                    type="number"
                    value={formData.ordre}
                    onChange={(e) => setFormData({ ...formData, ordre: parseInt(e.target.value) || 0 })}
                    className="input"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="rounded border-primary-300"
                />
                <label htmlFor="is_active" className="text-sm text-gray-700 dark:text-gray-300">
                  Menu actif
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button onClick={() => setShowModal(false)} className="btn-secondary">
                Annuler
              </button>
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
