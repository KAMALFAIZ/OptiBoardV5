import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Contacts
export const contactsApi = {
  list: (params) => api.get('/contacts', { params }),
  get: (id) => api.get(`/contacts/${id}`),
  create: (data) => api.post('/contacts', data),
  update: (id, data) => api.put(`/contacts/${id}`, data),
  delete: (id) => api.delete(`/contacts/${id}`),
}

// Tickets SAV
export const ticketsApi = {
  list: (params) => api.get('/tickets', { params }),
  get: (id) => api.get(`/tickets/${id}`),
  stats: () => api.get('/tickets/stats'),
  create: (data) => api.post('/tickets', data),
  updateStatus: (id, data) => api.put(`/tickets/${id}/status`, data),
  reply: (id, data) => api.post(`/tickets/${id}/reply`, data),
}

// Campagnes
export const campaignsApi = {
  list: (params) => api.get('/campaigns', { params }),
  get: (id) => api.get(`/campaigns/${id}`),
  create: (data) => api.post('/campaigns', data),
  addStep: (id, data) => api.post(`/campaigns/${id}/steps`, data),
  start: (id) => api.post(`/campaigns/${id}/start`),
  pause: (id) => api.post(`/campaigns/${id}/pause`),
  enroll: (id, data) => api.post(`/campaigns/${id}/enroll`, data),
}

// Workflows
export const workflowsApi = {
  list: (params) => api.get('/workflows', { params }),
  create: (data) => api.post('/workflows', data),
  update: (id, data) => api.put(`/workflows/${id}`, data),
  delete: (id) => api.delete(`/workflows/${id}`),
}

// Templates
export const templatesApi = {
  list: (params) => api.get('/templates', { params }),
  create: (data) => api.post('/templates', data),
  update: (id, data) => api.put(`/templates/${id}`, data),
  delete: (id) => api.delete(`/templates/${id}`),
}

// Produits
export const productsApi = {
  list: () => api.get('/products'),
  get: (code) => api.get(`/products/${code}`),
  getSecret: (code) => api.get(`/products/${code}/secret`),
  regenerateSecret: (code) => api.post(`/products/${code}/regenerate-secret`),
}

// Canaux
export const channelsApi = {
  getConfig: () => api.get('/channels/config'),
  updateConfig: (data) => api.put('/channels/config', data),
  test: (data) => api.post('/channels/test', data),
  verify: (data) => api.post('/channels/verify', data),
}

// Analytics
export const analyticsApi = {
  dashboard: () => api.get('/analytics/dashboard'),
  contactsEvolution: () => api.get('/analytics/contacts/evolution'),
  contactsByProduct: () => api.get('/analytics/contacts/by-product'),
  ticketsByProduct: () => api.get('/analytics/tickets/by-product'),
  deliveriesByChannel: () => api.get('/analytics/deliveries/by-channel'),
}

export default api
