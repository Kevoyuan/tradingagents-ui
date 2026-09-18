import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import os from 'os';

const testLogsDir = process.env.TRADINGAGENTS_LOGS_DIR || path.join(os.tmpdir(), 'tradingagents-playwright-logs');

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    channel: 'chrome',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome',
      },
    },
  ],
  webServer: [
    {
      command:
        `TRADINGAGENTS_STUB=1 TRADINGAGENTS_LOGS_DIR="${testLogsDir}" ../.venv/bin/python -m uvicorn trade_ui.server.app:app --host 127.0.0.1 --port 8000`,
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: 'npx vite --port 5173 --host 127.0.0.1',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
});
