import { defineConfig, devices } from '@playwright/test'

const authenticatedState = process.env.EWASTE_E2E_AUTH_STATE

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.EWASTE_E2E_BASE_URL || 'http://127.0.0.1:8000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ...devices['Desktop Chrome'],
    ...(authenticatedState ? { storageState: authenticatedState } : {}),
  },
})
