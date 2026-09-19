import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import os from 'os';

/**
 * Charting of raw data that upstream delivers as message text.
 *
 * The fixture mirrors a real run (`~/.tradingagents/runs/ed41b5d9`): a CSV block
 * with comment headers, and an indicator dump whose label arrives as a markdown
 * heading. Both are seeded on disk rather than produced by the stub runner,
 * because the stub's messages are prose.
 */

const runsDir =
  process.env.TRADINGAGENTS_RUNS_DIR || path.join(os.tmpdir(), 'tradingagents-playwright-runs');

function seedRun(runId: string, ticker: string, messageText: string | string[]) {
  const dir = path.join(runsDir, runId);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, 'run.json'),
    JSON.stringify({
      run_id: runId,
      status: 'completed',
      ticker,
      trade_date: '2026-09-19',
      created_at: '2026-09-19T10:00:00Z',
      started_at: '2026-09-19T10:00:00Z',
      completed_at: '2026-09-19T10:15:00Z',
      config: { ticker, trade_date: '2026-09-19', analysts: ['market'] },
      stats: null,
      verdict: null,
      error: null,
    }),
    'utf-8',
  );
  // The terminal run_state goes last, as a real run writes it. The client stops
  // reading the stream when it sees a terminal state, so a backlog that
  // announced completion first would be truncated at that point.
  const texts = Array.isArray(messageText) ? messageText : [messageText];
  const events = [
    {
      seq: 1,
      ts: '2026-09-19T10:00:01Z',
      run_id: runId,
      kind: 'run_state',
      agent: null,
      team: null,
      payload: { status: 'running', ticker, trade_date: '2026-09-19', config: {} },
    },
    ...texts.map((text, index) => ({
      seq: index + 2,
      ts: '2026-09-19T10:00:02Z',
      run_id: runId,
      kind: 'agent_message',
      agent: 'market',
      team: 'analyst',
      payload: { text, model: 'upstream', tokens_in: 0, tokens_out: 0, latency_ms: 0 },
    })),
    {
      seq: texts.length + 2,
      ts: '2026-09-19T10:00:03Z',
      run_id: runId,
      kind: 'run_state',
      agent: null,
      team: null,
      payload: { status: 'completed', ticker, trade_date: '2026-09-19', config: {} },
    },
  ];
  fs.writeFileSync(
    path.join(dir, 'events.jsonl'),
    events.map((event) => JSON.stringify(event)).join('\n') + '\n',
    'utf-8',
  );
}

function ohlcvBlock(rows: number): string {
  const lines = [
    `# Stock data for CHARTS from 2026-03-19 to 2026-09-19`,
    `# Total records: ${rows}`,
    '# Data retrieved on: 2026-09-19 20:37:16',
    '',
    'Date,Open,High,Low,Close,Volume,Dividends,Stock Splits',
  ];
  for (let i = 0; i < rows; i += 1) {
    const day = String((i % 28) + 1).padStart(2, '0');
    const month = String((Math.floor(i / 28) % 9) + 1).padStart(2, '0');
    const close = 200 + i;
    lines.push(`2026-${month}-${day},${close - 1},${close + 2},${close - 3},${close},1000000,0.0,0.0`);
  }
  return lines.join('\n');
}

const INDICATOR_BLOCK = [
  '## close_200_sma values from 2026-07-21 to 2026-09-19:',
  '2026-09-19: N/A: Not a trading day (weekend or holiday) 2026-09-18: 227.84 2026-09-17: 227.21',
  '2026-09-16: 226.54 2026-09-15: 225.90 2026-09-14: 225.25 2026-09-11: 224.57 2026-09-10: 223.97',
  '2026-09-09: 223.37 2026-09-08: 222.78 2026-09-04: 222.34 2026-09-03: 221.96 2026-09-02: 221.59',
].join('\n');

/** A "verified snapshot" message: two tables of single readings, then a series. */
const SNAPSHOT_BLOCK = [
  '## Verified market data snapshot for CHARTS',
  '',
  '### Latest verified OHLCV row',
  '',
  '| Field | Value |',
  '|---|---:|',
  '| Open | 338.00 |',
  '| Close | 323.60 |',
  '',
  '### Verified technical indicators (latest row)',
  '',
  '| Indicator | Value |',
  '|---|---:|',
  '| close_200_sma | 227.84 |',
  '| rsi | 57.92 |',
  '',
  '### Recent verified closes (last 30 rows)',
  '',
  '| Date | Close |',
  '|---|---:|',
  ...Array.from({ length: 30 }, (_, i) => {
    // Distinct days: a repeated date is covered by its own test below.
    const day = String(i + 1).padStart(2, '0');
    const month = i < 15 ? '08' : '09';
    const dateOfMonth = i < 15 ? day : String(i - 14).padStart(2, '0');
    return `| 2026-${month}-${dateOfMonth} | ${300 + i}.27 |`;
  }),
].join('\n');

test.describe('Data charts', () => {
  test('charts an OHLCV block and keeps the raw rows one click away', async ({ page }) => {
    const runId = 'chartcsv1';
    seedRun(runId, 'CHARTS', ohlcvBlock(127));

    await page.goto(`/?runId=${runId}`);

    const charted = page.locator('[data-testid="agent-message-charted"]');
    await expect(charted).toBeVisible();

    // The library renders into a canvas; that is the difference between a chart
    // and a claim of one.
    await expect(page.locator('[data-testid="data-chart"] canvas').first()).toBeVisible();

    // Raw rows are collapsed by default, matching how tool output is treated.
    const toggle = page.locator('[data-testid="toggle-raw-data"]');
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(charted).not.toContainText('Date,Open,High,Low,Close');

    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(charted).toContainText('Date,Open,High,Low,Close');
  });

  test('charts an indicator dump whose label is a markdown heading', async ({ page }) => {
    const runId = 'chartind1';
    seedRun(runId, 'CHARTS', INDICATOR_BLOCK);

    await page.goto(`/?runId=${runId}`);

    const charted = page.locator('[data-testid="agent-message-charted"]');
    await expect(charted).toBeVisible();
    await expect(charted).toContainText('close_200_sma');
    await expect(page.locator('[data-testid="data-chart"] canvas').first()).toBeVisible();
  });

  test('leaves a prose message exactly as it was', async ({ page }) => {
    const runId = 'chartprose1';
    seedRun(runId, 'CHARTS', 'The market looks constructive into the print. No tables here.');

    await page.goto(`/?runId=${runId}`);

    await expect(page.locator('[data-testid="event-2"]')).toContainText('constructive into the print');
    await expect(page.locator('[data-testid="agent-message-charted"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="data-chart"]')).toHaveCount(0);
  });

  test('charts the series inside a snapshot table and skips its single readings', async ({ page }) => {
    const runId = 'charttable1';
    seedRun(runId, 'CHARTS', SNAPSHOT_BLOCK);

    await page.goto(`/?runId=${runId}`);

    const charted = page.locator('[data-testid="agent-message-charted"]');
    await expect(charted).toBeVisible();
    // Only the 30-row Date/Close table is a series. The Field/Value and
    // Indicator/Value tables have no date column, so they stay as tables.
    // The column is generically named "Close", so the section heading names the
    // chart instead of a bare "Close".
    await expect(charted).toContainText('Recent verified closes (30 pts)');
    await expect(page.locator('[data-testid="data-chart"]')).toHaveCount(1);
    await expect(charted).not.toContainText('bars');
  });

  test('charts a repeated dataset once and leaves the repeats as text', async ({ page }) => {
    const runId = 'chartdupe1';
    // The graph re-emits a message as its state grows; the NET run carried 94
    // charted messages over 18 datasets.
    seedRun(runId, 'CHARTS', [ohlcvBlock(30), ohlcvBlock(30)]);

    await page.goto(`/?runId=${runId}`);

    await expect(page.locator('[data-testid="agent-message-charted"]')).toHaveCount(1);
    await expect(page.locator('[data-testid="data-chart"]')).toHaveCount(1);
    // Both messages are still in the record: only the chart is de-duplicated.
    // The first charts and collapses its rows; the repeat is left as text.
    await expect(page.locator('[data-testid="event-2"]')).toContainText('Charted');
    await expect(page.locator('[data-testid="event-2"]')).toContainText('Raw data');
    await expect(page.locator('[data-testid="event-3"]')).toContainText('Date,Open,High,Low,Close');
  });

  test('refuses a truncated CSV block instead of charting half of it', async ({ page }) => {
    const runId = 'chartbad1';
    // A well-formed block followed by a row-shaped line that cannot be parsed.
    const broken = `${ohlcvBlock(40)}\n2026-99-99,not,a,row,at,all`;
    seedRun(runId, 'CHARTS', broken);

    await page.goto(`/?runId=${runId}`);

    // The message still renders as text; it is the chart that is withheld.
    await expect(page.locator('[data-testid="event-2"]')).toContainText('Date,Open,High,Low,Close');
    await expect(page.locator('[data-testid="agent-message-charted"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="data-chart"]')).toHaveCount(0);
  });

  test('survives a table that names the same day twice', async ({ page }) => {
    const runId = 'chartdupdate1';
    // The chart library throws on a repeated time, and a throw here blanks the
    // record rather than just the chart. Collapse the duplicate instead.
    const repeated = [
      '## Recent closes',
      '',
      '| Date | Close |',
      '|---|---:|',
      ...Array.from({ length: 20 }, (_, i) => `| 2026-08-${String((i % 10) + 1).padStart(2, '0')} | ${300 + i} |`),
    ].join('\n');
    seedRun(runId, 'CHARTS', repeated);

    await page.goto(`/?runId=${runId}`);

    const charted = page.locator('[data-testid="agent-message-charted"]');
    await expect(charted).toBeVisible();
    await expect(charted).toContainText('10 pts');
    await expect(page.locator('[data-testid="data-chart"] canvas').first()).toBeVisible();
  });
});
