import axios from 'axios'

// `import.meta.env` is always defined by Vite (it's a build-time
// construct, never actually undefined in a Vite-built app) — the
// optional chaining this used to have (`import.meta?.env?.VITE_API_BASE`)
// broke Vite's static replacement of `import.meta.env.X` reads, so
// VITE_API_BASE was silently never applied in a production build
// regardless of what was configured; only the '/api/v1' fallback ever
// took effect. Confirmed via a real production build: the optional-
// chained version left `VITE_API_BASE` as a runtime property lookup in
// the bundle instead of being inlined, and it always evaluated to
// undefined at runtime.
const BASE = import.meta.env.VITE_API_BASE || '/api/v1'
const api = axios.create({ baseURL: BASE })

// backend/app.py registers /health at the application root, not under
// the /api/v1 blueprint prefix (it's an infrastructure-level check meant
// to work independently of the API routing, matching Render's/Docker's
// healthCheckPath convention). Confirmed via a real end-to-end run: every
// component that instead called `api.get('/health')` through the
// /api/v1-prefixed client always got a 404, meaning the connectivity
// indicator (components/Connectivity.jsx) reported "Offline" 100% of the
// time regardless of whether the backend was actually reachable. This
// derives the true health-check URL from the same BASE so it keeps
// working whether the app is deployed same-origin or cross-origin.
const ROOT = BASE.replace(/\/api\/v1\/?$/, '')

export function checkHealth() {
  return axios.get(`${ROOT}/health`)
}

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
