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
