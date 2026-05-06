import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/bluetooth-data-fatigue': {
        target: 'http://localhost:3002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/bluetooth-data-fatigue/, '/api/bluetooth-data')
      },
      '/api/bluetooth-data-sleep': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/bluetooth-data-sleep/, '/api/bluetooth-data')
      },
      '/api/bluetooth-data': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
      '/api/fatigue': {
        target: 'http://localhost:3002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/fatigue/, '')
      },
      '/api/sleep': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/sleep/, '')
      },
      '/api/dry-eye': {
        target: 'http://localhost:3000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/dry-eye/, '')
      },
      '/ws/dry-eye': {
        target: 'ws://localhost:3000',
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ws\/dry-eye/, '/ws')
      },
      '/ws/sleep': {
        target: 'ws://localhost:3001',
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ws\/sleep/, '/ws')
      },
      '/ws/fatigue': {
        target: 'ws://localhost:3002',
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ws\/fatigue/, '/ws')
      }
    }
  }
})
