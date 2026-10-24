/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
  test: { environment: 'jsdom', setupFiles: ['./src/tests/setup.ts'], globals: true, exclude: ['e2e/**', 'node_modules/**'] },
})
