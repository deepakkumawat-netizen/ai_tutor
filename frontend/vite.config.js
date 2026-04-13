import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,        // try 5173 first
    strictPort: false, // if busy, auto-pick next available port
    open: true,        // auto-open browser on whatever port it lands on
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      }
    }
  }
})
