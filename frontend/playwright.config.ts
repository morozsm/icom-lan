import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '../tests/e2e',
  testMatch: /v2-ui-interactive\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180_000,
  outputDir: '../.playwright-output',
  reporter: 'list',
  use: {
    baseURL: 'http://192.168.55.152:8080',
    viewport: { width: 1728, height: 1200 },
    trace: 'retain-on-failure',
    screenshot: 'off',
    video: 'off',
    headless: true,
  },
});
