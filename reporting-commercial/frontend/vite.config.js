import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: process.env.PORT ? parseInt(process.env.PORT) : 3003,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8084',
        changeOrigin: true,
        // Retry automatique si le backend n'est pas encore prêt au démarrage
        configure: (proxy) => {
          proxy.on('error', (err, req, res) => {
            // Réponse JSON 503 propre au lieu d'un crash Vite
            if (!res.headersSent) {
              res.writeHead(503, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({ error: 'Backend indisponible', detail: err.message }))
            }
          })
        }
      }
    }
  }
})
