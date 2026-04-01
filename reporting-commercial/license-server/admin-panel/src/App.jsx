import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Clients from './pages/Clients'
import ClientDetail from './pages/ClientDetail'
import Licenses from './pages/Licenses'
import LicenseDetail from './pages/LicenseDetail'
import GenerateLicense from './pages/GenerateLicense'
import Logs from './pages/Logs'
import Login from './pages/Login'
import { isAuthenticated } from './services/api'

// Garde : redirige vers /login si non authentifie
function RequireAuth({ children }) {
  return isAuthenticated() ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Page de connexion — accessible sans cle */}
        <Route path="/login" element={<Login />} />

        {/* Toutes les autres routes protegees */}
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/clients" element={<Clients />} />
          <Route path="/clients/:id" element={<ClientDetail />} />
          <Route path="/licenses" element={<Licenses />} />
          <Route path="/licenses/generate" element={<GenerateLicense />} />
          <Route path="/licenses/:id" element={<LicenseDetail />} />
          <Route path="/logs" element={<Logs />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
