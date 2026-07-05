import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/v1': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      },
      // src/api.js derives the health-check URL by stripping '/api/v1' off
      // VITE_API_BASE, since backend/app.py registers /health at the
      // application root rather than under the /api/v1 blueprint prefix
      // (see api.js's own comment). Without an explicit proxy entry here,
      // `npm run dev` never forwards GET /health to the backend at all —
      // Vite's dev server falls back to serving index.html (the SPA
      // fallback) with a 200 status for any unmatched path, so
      // Connectivity.jsx's checkHealth().then(...) always resolved
      // successfully and showed "Online" regardless of whether the real
      // backend was reachable. Confirmed via a real dev run: curling
      // http://localhost:5173/health returned the SPA's HTML shell, not
      // {"status":"ok"}, until this entry was added.
      '/health': 'http://localhost:5000',
      '/auth': 'http://localhost:5000',
      '/students': 'http://localhost:5000',
      '/ml': 'http://localhost:5000',
      '/analytics': 'http://localhost:5000',
      '/gamify': 'http://localhost:5000',
      '/alerts': 'http://localhost:5000',
      '/wellness': 'http://localhost:5000',
      '/digital-twin': 'http://localhost:5000',
      '/voice': 'http://localhost:5000'
    }
  }
})
