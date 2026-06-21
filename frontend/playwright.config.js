import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  retries: 1,
  use: {
    browserName: 'chromium',
    headless: true,
    viewport: { width: 1280, height: 800 },
    actionTimeout: 10000,
    navigationTimeout: 20000,
  },
});
