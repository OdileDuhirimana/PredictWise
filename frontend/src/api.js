import axios from 'axios'

const BASE = import.meta?.env?.VITE_API_BASE || '/api/v1'
const api = axios.create({ baseURL: BASE })

export function setToken(token){
  if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  else delete api.defaults.headers.common['Authorization']
}

// Initialize from localStorage
const existing = typeof window !== 'undefined' ? localStorage.getItem('jwt') : null
if (existing) setToken(existing)

// Interceptor to handle 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      try { localStorage.removeItem('jwt') } catch(e) {}
      setToken(null)
      // Redirect to login if possible
      if (typeof window !== 'undefined') {
        const loc = window.location
        if (!loc.pathname.startsWith('/login')) {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

export default api
