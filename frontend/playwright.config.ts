import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  use: { baseURL: 'http://localhost:5173' },
  webServer: [
    { command: 'cd ../backend && HEALTHDOC_DATA_DIR=/tmp/healthdoc-e2e uvicorn app.main:app --port 8000', url: 'http://localhost:8000/api/health', reuseExistingServer: true, timeout: 60_000 },
    { command: 'npm run dev', url: 'http://localhost:5173', reuseExistingServer: true },
  ],
})
