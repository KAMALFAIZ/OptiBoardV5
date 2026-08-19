import React from 'react'
import ReactDOM from 'react-dom/client'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community'
import App from './App'
import './index.css'
import { setupPwa } from './pwa/registerSW'

// Service worker (prod uniquement) + capture du prompt d'installation PWA
setupPwa()

// Register all AG Grid community modules globally
ModuleRegistry.registerModules([AllCommunityModule])

ReactDOM.createRoot(document.getElementById('root')).render(
  <App />,
)
