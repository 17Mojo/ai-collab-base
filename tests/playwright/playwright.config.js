const path = require('path');
const { defineConfig } = require('@playwright/test');

const repoRoot = path.resolve(__dirname, '../..');

module.exports = defineConfig({
  testDir: path.join(__dirname, 'tests'),
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  reporter: process.env.CI
    ? [
        ['list'],
        ['junit', { outputFile: path.join(repoRoot, 'logs', 'playwright-junit.xml') }],
        ['html', { outputFolder: path.join(repoRoot, 'logs', 'playwright-report'), open: 'never' }],
        ['json', { outputFile: path.join(repoRoot, 'logs', 'playwright-report.json') }],
      ]
    : [
        ['list'],
        ['html', { outputFolder: path.join(repoRoot, 'logs', 'playwright-report'), open: 'on-failure' }],
      ],
  outputDir: path.join(repoRoot, 'logs', 'playwright-results'),
  use: {
    baseURL: 'http://127.0.0.1:4173',
    browserName: 'chromium',
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
    // Enhanced observability
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  webServer: {
    command: 'python3 -m http.server 4173 --bind 127.0.0.1',
    url: 'http://127.0.0.1:4173',
    cwd: repoRoot,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
