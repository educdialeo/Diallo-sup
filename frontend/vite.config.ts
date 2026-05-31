import process from 'node:process'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Le SPA est servi par FastAPI en prod ; en dev, Vite proxifie l'API du backend.
// La cible du proxy est surchargeable via VITE_API_TARGET (utile pour pointer
// vers un uvicorn de demo sur un port jetable, ex. 8016, sans toucher au :8000
// de prod).
const apiTarget = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': apiTarget,
      '/health': apiTarget,
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
