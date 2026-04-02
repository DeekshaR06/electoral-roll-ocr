import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname),
    },
  },
  server: {
    proxy: {
      '/api': {
        target:  'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (routePath) => routePath.replace(/^\/api/, ''),
      },
    },
  },
  plugins: [
    react(),
  ]
});