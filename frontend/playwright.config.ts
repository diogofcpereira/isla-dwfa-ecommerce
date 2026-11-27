// playwright.config.ts — testes e2e (extra do M2): a SPA num Chromium a sério, contra a API
// a sério. No CI correm no job `docker`, contra os contentores do compose.prod.yaml
// (http://localhost, com o seed). Em dev: E2E_BASE_URL=http://localhost:5173 npm run test:e2e
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  // Os testes mexem nos mesmos dados (stock, encomendas): um de cada vez, por ordem.
  workers: 1,
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI), // um test.only esquecido não passa no CI
  retries: 0, // um teste e2e instável é para corrigir, não para repetir até passar
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost',
    locale: 'pt-PT',
    timezoneId: 'Europe/Lisbon',
    trace: 'retain-on-failure', // se falhar: o passo a passo, com a rede e a consola
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
