import { defineConfig, devices } from '@playwright/test'

const localChannel = process.env.PLAYWRIGHT_CHANNEL as
  | 'chrome'
  | 'msedge'
  | undefined

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false,
  reporter: 'line',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'], channel: localChannel } },
    { name: 'mobile-chromium', use: { ...devices['Pixel 7'], channel: localChannel } },
  ],
})
