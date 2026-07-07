import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// Use VITE_API_TARGET env var for Docker support (defaults to localhost for local dev)
const apiTarget = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        secure: false,
      },
    },
  },
})