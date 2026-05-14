import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { SettingsProvider } from './context/SettingsContext'
import { ThemeProvider, useTheme } from './context/ThemeContext'
import { GlobalFilterProvider } from './context/GlobalFilterContext'
import { LicenseProvider, useLicense } from './context/LicenseContext'
import { ChatProvider } from './context/ChatContext'
import { DWHProvider, useDWH } from './context/DWHContext'
import { DataSourceProvider } from './context/DataSourceContext'
import { ToastProvider } from './components/common/Toast'
import Layout from './components/common/Layout'
import MobileLayout from './components/mobile/MobileLayout'
import { useIsMobile } from './hooks/useIsMobile'
import LicenseBanner from './components/common/LicenseBanner'
import api from './services/api'
import ErrorBoundary from './components/common/ErrorBoundary'

// Pages critiques (affichées au premier rendu, pas de lazy)
import LoginPage from './pages/LoginPage'
import SetupPage from './pages/SetupPage'
import LicensePage from './pages/LicensePage'
import HomePage from './pages/HomePage'

// Lazy-loaded pages — chaque page = chunk séparé (code splitting)
const Ventes = lazy(() => import('./pages/Ventes'))
const Stocks = lazy(() => import('./pages/Stocks'))
const Recouvrement = lazy(() => import('./pages/Recouvrement'))
const UserManagement = lazy(() => import('./pages/UserManagement'))
const ClientUserManagement = lazy(() => import('./pages/ClientUserManagement'))
const ClientDWHManagement = lazy(() => import('./pages/ClientDWHManagement'))
const DashboardBuilder = lazy(() => import('./pages/DashboardBuilder'))
const DashboardView = lazy(() => import('./pages/DashboardView'))
const GridViewBuilder = lazy(() => import('./pages/GridViewBuilder'))
const GridViewDisplay = lazy(() => import('./pages/GridViewDisplay'))
const MenuManagement = lazy(() => import('./pages/MenuManagement'))
const MenuMasterManagement = lazy(() => import('./pages/MenuMasterManagement'))
const Settings = lazy(() => import('./pages/Settings'))
const ThemeManagement = lazy(() => import('./pages/ThemeManagement'))
const ReportScheduler = lazy(() => import('./pages/ReportScheduler'))
const DatabaseManagement = lazy(() => import('./pages/DatabaseManagement'))
const DWHManagement = lazy(() => import('./pages/DWHManagement'))
const DataSourceTemplates = lazy(() => import('./pages/DataSourceTemplates'))
const ETLAdmin = lazy(() => import('./pages/ETLAdmin'))
const ListeVentes = lazy(() => import('./pages/ListeVentes'))
const AnalyseCACreances = lazy(() => import('./pages/AnalyseCACreances'))
const PIC2026 = lazy(() => import('./pages/PIC2026'))
const PivotBuilderV2 = lazy(() => import('./pages/PivotBuilderV2'))
const PivotViewerV2 = lazy(() => import('./pages/PivotViewerV2'))
const AIAssistantPage = lazy(() => import('./pages/AIAssistantPage'))
const ETLColonnesPage = lazy(() => import('./pages/ETLColonnesPage'))
const UpdateManagerPage = lazy(() => import('./pages/UpdateManagerPage'))
const AIQueryLibraryPage = lazy(() => import('./pages/AIQueryLibraryPage'))
const AIPromptsPage = lazy(() => import('./pages/AIPromptsPage'))
const EnvManagerPage = lazy(() => import('./pages/EnvManagerPage'))
const MasterConfigPage = lazy(() => import('./pages/MasterConfigPage'))
const WhatsAppConfigPage = lazy(() => import('./pages/WhatsAppConfigPage'))
const RolesAdmin = lazy(() => import('./pages/RolesAdmin'))
const AlertsPage = lazy(() => import('./pages/AlertsPage'))
const MySubscriptionsPage = lazy(() => import('./pages/MySubscriptionsPage'))
const AdminSubscriptionsPage = lazy(() => import('./pages/AdminSubscriptionsPage'))
const DrillThroughPage = lazy(() => import('./pages/DrillThroughPage'))
const FicheClient = lazy(() => import('./pages/FicheClient'))
const FicheFournisseur = lazy(() => import('./pages/FicheFournisseur'))
const Comptabilite = lazy(() => import('./pages/Comptabilite'))
const SageConfigAdmin = lazy(() => import('./pages/SageConfigAdmin'))
const DigestAdmin = lazy(() => import('./pages/DigestAdmin'))
const AIPresentationBuilder = lazy(() => import('./pages/AIPresentationBuilder'))
const AIDeckBuilder = lazy(() => import('./pages/AIDeckBuilder'))
const SpreadsheetBuilder = lazy(() => import('./pages/SpreadsheetBuilder'))
const SpreadsheetViewer = lazy(() => import('./pages/SpreadsheetViewer'))
const Setup2FAPage = lazy(() => import('./pages/Setup2FAPage'))
const OrdreFabrication = lazy(() => import('./pages/OrdreFabrication'))
const DemoRegisterPage = lazy(() => import('./pages/DemoRegisterPage'))
const DemoStatusPage = lazy(() => import('./pages/DemoStatusPage'))
const DemoBoardPage = lazy(() => import('./pages/DemoBoardPage'))
const DemoLaunchPage = lazy(() => import('./pages/DemoLaunchPage'))

const PageLoader = () => (
  <div className="min-h-[200px] flex items-center justify-center">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
  </div>
)

// Composant pour proteger les routes
function ProtectedRoute({ children, pageCode }) {
  const { isAuthenticated, hasAccess, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />
  }

  if (pageCode && !hasAccess(pageCode)) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Acces refuse</h2>
          <p className="text-gray-500">Vous n'avez pas les droits pour acceder a cette page.</p>
        </div>
      </div>
    )
  }

  return children
}

function AppContent() {
  const { isAuthenticated, login, logout, user, loading } = useAuth()
  const { darkMode, setDarkMode } = useTheme()
  const { isLicensed, loading: licenseLoading, isExpiringSoon, isGraceMode, license } = useLicense()
  const { hasDWH, initializeContext } = useDWH()
  const isMobile = useIsMobile()
  const [refreshing, setRefreshing] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [setupStatus, setSetupStatus] = useState({ loading: true, configured: true })

  // Verifier si l'application est configuree au demarrage
  useEffect(() => {
    const checkSetupStatus = async () => {
      try {
        const response = await api.get('/setup/status')
        let appName = response.data.app_name
        // Essayer de recuperer le nom depuis la base de donnees (prioritaire)
        if (response.data.configured) {
          try {
            const nameRes = await api.get('/setup/app-name')
            if (nameRes.data.success && nameRes.data.app_name) {
              appName = nameRes.data.app_name
            }
          } catch (e) { /* fallback sur le .env */ }
        }
        setSetupStatus({
          loading: false,
          configured: response.data.configured,
          appName
        })
      } catch (error) {
        console.error('Erreur verification setup:', error)
        // En cas d'erreur, on considere que c'est configure pour eviter de bloquer
        setSetupStatus({ loading: false, configured: true })
      }
    }
    checkSetupStatus()
  }, [])

  // Auto-initialise le contexte DWH si l'utilisateur est connecté mais qu'aucun DWH actif n'est défini
  // (ex : après un refresh de page où initializeContext n'a pas été appelé)
  useEffect(() => {
    if (user?.id && !hasDWH) {
      initializeContext(user.id)
    }
  }, [user?.id, hasDWH]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await api.post('/cache/clear')
      setRefreshKey(prev => prev + 1)
    } catch (error) {
      console.error('Erreur lors du rafraichissement:', error)
    } finally {
      setTimeout(() => setRefreshing(false), 500)
    }
  }, [])

  const handleConfigured = () => {
    // Recharger la page apres configuration
    window.location.reload()
  }

  const handleLicenseActivated = () => {
    window.location.reload()
  }

  // Afficher le loader pendant la verification du setup et de la licence
  if (setupStatus.loading || loading || licenseLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  // Etape 1: Verification de la licence AVANT tout
  if (!isLicensed) {
    return <LicensePage onActivated={handleLicenseActivated} />
  }

  // Afficher la page de setup si non configure
  if (!setupStatus.configured) {
    return <SetupPage onConfigured={handleConfigured} />
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={login} appName={setupStatus.appName} />
  }

  // Version mobile : layout simplifié avec seulement les pages autorisées
  if (isMobile) {
    return <MobileLayout appName={setupStatus.appName} />
  }

  return (
    <Layout
      darkMode={darkMode}
      setDarkMode={setDarkMode}
      onRefresh={handleRefresh}
      refreshing={refreshing}
      user={user}
      onLogout={logout}
      appName={setupStatus.appName}
    >
      {/* Bannières d'avertissement licence (expiration, grâce, mode limité) */}
      <LicenseBanner />
      <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="/" element={
          <ProtectedRoute pageCode="dashboard">
            <HomePage />
          </ProtectedRoute>
        } />
        <Route path="/ventes" element={
          <ProtectedRoute pageCode="ventes">
            <Ventes key={refreshKey} />
          </ProtectedRoute>
        } />
        <Route path="/stocks" element={
          <ProtectedRoute pageCode="stocks">
            <Stocks key={refreshKey} />
          </ProtectedRoute>
        } />
        <Route path="/recouvrement" element={
          <ProtectedRoute pageCode="recouvrement">
            <Recouvrement key={refreshKey} />
          </ProtectedRoute>
        } />
        <Route path="/admin/users" element={
          <ProtectedRoute pageCode="users">
            <UserManagement />
          </ProtectedRoute>
        } />
        <Route path="/admin/client-users" element={
          <ProtectedRoute pageCode="client_users">
            <ClientUserManagement />
          </ProtectedRoute>
        } />
        <Route path="/admin/client-dwh" element={
          <ProtectedRoute pageCode="client_dwh">
            <ClientDWHManagement />
          </ProtectedRoute>
        } />
        <Route path="/builder" element={
          <ProtectedRoute pageCode="admin">
            <DashboardBuilder />
          </ProtectedRoute>
        } />
        <Route path="/view/:id" element={
          <ProtectedRoute pageCode="dashboard">
            <ErrorBoundary title="Erreur lors du chargement du dashboard">
              <DashboardView />
            </ErrorBoundary>
          </ProtectedRoute>
        } />
        <Route path="/gridview-builder" element={
          <ProtectedRoute pageCode="admin">
            <GridViewBuilder />
          </ProtectedRoute>
        } />
        <Route path="/grid/:id" element={
          <ProtectedRoute pageCode="dashboard">
            <GridViewDisplay />
          </ProtectedRoute>
        } />
        <Route path="/admin/menus" element={
          <ProtectedRoute pageCode="admin">
            <MenuManagement />
          </ProtectedRoute>
        } />
        <Route path="/admin/master-menus" element={
          <ProtectedRoute pageCode="admin">
            <MenuMasterManagement />
          </ProtectedRoute>
        } />
      <Route path="/settings" element={<ProtectedRoute pageCode="admin"><Settings /></ProtectedRoute>} />
      <Route path="/themes" element={<ProtectedRoute pageCode="dashboard"><ThemeManagement /></ProtectedRoute>} />
      <Route path="/admin/report-scheduler" element={<ProtectedRoute pageCode="admin"><ReportScheduler /></ProtectedRoute>} />
      <Route path="/admin/database" element={<ProtectedRoute pageCode="admin"><DatabaseManagement /></ProtectedRoute>} />
      <Route path="/admin/dwh" element={<ProtectedRoute pageCode="dwh_management"><DWHManagement /></ProtectedRoute>} />
      <Route path="/admin/datasources" element={<ProtectedRoute pageCode="admin"><DataSourceTemplates /></ProtectedRoute>} />
      <Route path="/admin/etl" element={<ProtectedRoute pageCode="etl_admin"><ETLAdmin /></ProtectedRoute>} />
      <Route path="/liste-ventes" element={<ProtectedRoute pageCode="ventes"><ListeVentes /></ProtectedRoute>} />
      <Route path="/analyse-ca-creances" element={<ProtectedRoute pageCode="dashboard"><AnalyseCACreances /></ProtectedRoute>} />
      <Route path="/pic-2026" element={<ProtectedRoute pageCode="dashboard"><PIC2026 /></ProtectedRoute>} />
      <Route path="/pivot-builder-v2" element={<ProtectedRoute pageCode="admin"><ErrorBoundary title="Erreur dans le Pivot Builder"><PivotBuilderV2 /></ErrorBoundary></ProtectedRoute>} />
      <Route path="/pivot-v2/:id" element={<ProtectedRoute pageCode="dashboard"><ErrorBoundary title="Erreur lors du chargement du pivot"><PivotViewerV2 /></ErrorBoundary></ProtectedRoute>} />
      <Route path="/ai-assistant" element={<ProtectedRoute pageCode="dashboard"><ErrorBoundary title="Erreur dans l'assistant IA"><AIAssistantPage /></ErrorBoundary></ProtectedRoute>} />
      <Route path="/ai-presentation" element={<ProtectedRoute pageCode="dashboard"><ErrorBoundary title="Erreur dans le générateur IA"><AIPresentationBuilder /></ErrorBoundary></ProtectedRoute>} />
      <Route path="/ai-deck" element={<ProtectedRoute pageCode="dashboard"><ErrorBoundary title="Erreur dans le Deck IA"><AIDeckBuilder /></ErrorBoundary></ProtectedRoute>} />
      <Route path="/admin/etl-colonnes" element={<ProtectedRoute pageCode="etl_admin"><ETLColonnesPage /></ProtectedRoute>} />
      <Route path="/updates" element={<ProtectedRoute pageCode="dashboard"><UpdateManagerPage /></ProtectedRoute>} />
      <Route path="/admin/ai-library" element={<ProtectedRoute pageCode="admin"><AIQueryLibraryPage /></ProtectedRoute>} />
      <Route path="/admin/ai-prompts" element={<ProtectedRoute pageCode="admin"><AIPromptsPage /></ProtectedRoute>} />
      <Route path="/admin/env" element={<ProtectedRoute pageCode="admin"><EnvManagerPage /></ProtectedRoute>} />
      <Route path="/admin/master-config" element={<ProtectedRoute pageCode="admin"><MasterConfigPage /></ProtectedRoute>} />
      <Route path="/admin/whatsapp" element={<ProtectedRoute pageCode="admin"><WhatsAppConfigPage /></ProtectedRoute>} />
      <Route path="/admin/roles" element={<ProtectedRoute pageCode="admin"><RolesAdmin /></ProtectedRoute>} />
      <Route path="/admin/alerts" element={<ProtectedRoute pageCode="admin"><AlertsPage /></ProtectedRoute>} />
      <Route path="/admin/subscriptions" element={<ProtectedRoute pageCode="admin"><AdminSubscriptionsPage /></ProtectedRoute>} />
      <Route path="/mes-abonnements" element={<ProtectedRoute pageCode="dashboard"><MySubscriptionsPage /></ProtectedRoute>} />
      <Route path="/admin/drillthrough" element={<ProtectedRoute pageCode="admin"><DrillThroughPage /></ProtectedRoute>} />
      <Route path="/fiche-client" element={<ProtectedRoute pageCode="ventes"><FicheClient /></ProtectedRoute>} />
      <Route path="/fiche-fournisseur" element={<ProtectedRoute pageCode="achats"><FicheFournisseur /></ProtectedRoute>} />
      <Route path="/comptabilite" element={<ProtectedRoute pageCode="comptabilite"><Comptabilite /></ProtectedRoute>} />
      <Route path="/comptabilite/:section" element={<ProtectedRoute pageCode="comptabilite"><Comptabilite /></ProtectedRoute>} />
      <Route path="/admin/sage-config" element={<ProtectedRoute pageCode="admin"><SageConfigAdmin /></ProtectedRoute>} />
      <Route path="/admin/digest" element={<ProtectedRoute pageCode="admin"><DigestAdmin /></ProtectedRoute>} />
      <Route path="/spreadsheet-builder" element={<ProtectedRoute pageCode="admin"><ErrorBoundary title="Erreur dans le Spreadsheet Builder"><SpreadsheetBuilder /></ErrorBoundary></ProtectedRoute>} />
      <Route path="/spreadsheet/:id" element={<ProtectedRoute pageCode="dashboard"><ErrorBoundary title="Erreur lors du chargement du tableur"><SpreadsheetViewer /></ErrorBoundary></ProtectedRoute>} />
      <Route path="/setup-2fa" element={<ProtectedRoute><Setup2FAPage /></ProtectedRoute>} />
      <Route path="/production/ordres-fabrication" element={<ProtectedRoute pageCode="dashboard"><ErrorBoundary title="Erreur Ordres de fabrication"><OrdreFabrication /></ErrorBoundary></ProtectedRoute>} />
      </Routes>
      </Suspense>
    </Layout>
  )
}

// Composant racine qui intercepte les routes demo avant tout contexte
function AppRoot() {
  const { pathname } = window.location
  if (pathname === '/demo' || pathname.startsWith('/demo/')) {
    return (
      <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/demo" element={<DemoRegisterPage />} />
        <Route path="/demo/:token" element={<DemoStatusPage />} />
        <Route path="/demo/:token/board" element={<DemoBoardPage />} />
        <Route path="/demo/:token/launch" element={<DemoLaunchPage />} />
      </Routes>
      </Suspense>
    )
  }
  return (
    <LicenseProvider>
      <AuthProvider>
        <ThemeProvider>
          <SettingsProvider>
            <GlobalFilterProvider>
              <ChatProvider>
                <DWHProvider>
                  <DataSourceProvider>
                    <ToastProvider>
                      <AppContent />
                    </ToastProvider>
                  </DataSourceProvider>
                </DWHProvider>
              </ChatProvider>
            </GlobalFilterProvider>
          </SettingsProvider>
        </ThemeProvider>
      </AuthProvider>
    </LicenseProvider>
  )
}

function App() {
  return (
    <Router>
      <ErrorBoundary title="Une erreur critique est survenue — veuillez recharger la page">
        <AppRoot />
      </ErrorBoundary>
    </Router>
  )
}

export default App
