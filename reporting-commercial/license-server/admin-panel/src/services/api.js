import axios from 'axios'

const ADMIN_KEY_STORAGE = 'ls_admin_key'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

// Injecter automatiquement X-Admin-Key dans chaque requete
api.interceptors.request.use((config) => {
  const key = localStorage.getItem(ADMIN_KEY_STORAGE)
  if (key) {
    config.headers['X-Admin-Key'] = key
  }
  return config
})

// Si 401 -> rediriger vers la page de login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(ADMIN_KEY_STORAGE)
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const getStoredKey = () => localStorage.getItem(ADMIN_KEY_STORAGE)
export const setStoredKey = (key) => localStorage.setItem(ADMIN_KEY_STORAGE, key)
export const clearStoredKey = () => localStorage.removeItem(ADMIN_KEY_STORAGE)
export const isAuthenticated = () => !!localStorage.getItem(ADMIN_KEY_STORAGE)

export default api
