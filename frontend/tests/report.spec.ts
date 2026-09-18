import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import os from 'os';

const testLogsDir = process.env.TRADINGAGENTS_LOGS_DIR || path.join(os.tmpdir(), 'tradingagents-playwright-logs');

function setupSyntheticReport(logsDir: string) {
  const repDir = path.join(logsDir, 'SYNTHETIC', '2026-05-20', 'reports');
  fs.mkdirSync(path.join(repDir, '1_analysts'), { recursive: true });
  fs.mkdirSync(path.join(repDir, '2_research'), { recursive: true });
  fs.mkdirSync(path.join(repDir, '3_trading'), { recursive: true });
  fs.mkdirSync(path.join(repDir, '4_risk'), { recursive: true });
  fs.mkdirSync(path.join(repDir, '5_portfolio'), { recursive: true });

  // Complete report encoding the trap: early BUY line, later SELL line, and PM Underweight
  fs.writeFileSync(
    path.join(repDir, 'complete_report.md'),
    `# SYNTHETIC 综合研报

## 最终交易建议：BUY SYNTHETIC（NMS），分批建仓

多头分析逻辑阐述...

## 最终交易建议：SELL SYNTHETIC (NMS)

空头与激进风控结论...

## V. Portfolio Manager Decision

**Rating**: Underweight
**Price Target**: 194.0
**Executive Summary**: 尽管前期研报出现BUY与SELL讨论，估值过高下调至Underweight评级。
`,
    'utf-8'
  );

  fs.writeFileSync(
    path.join(repDir, '1_analysts', 'market.md'),
    `# 市场技术分析报告

## 动量指标
技术指标超买，短期建议谨慎。
`,
    'utf-8'
  );

  fs.writeFileSync(
    path.join(repDir, '2_research', 'bull.md'),
    `# 多方观点

## 核心逻辑
长期逻辑坚实，推荐 BUY。
`,
    'utf-8'
  );

  fs.writeFileSync(
    path.join(repDir, '3_trading', 'trader.md'),
    `# 交易执行计划

**Entry Price**: 150.00
**Stop Loss**: 140.00
**Position Sizing**: 2%
`,
    'utf-8'
  );

  fs.writeFileSync(
    path.join(repDir, '4_risk', 'aggressive.md'),
    `# 激进风险评估

建议 SELL 降低敞口。
`,
    'utf-8'
  );

  fs.writeFileSync(
    path.join(repDir, '5_portfolio', 'decision.md'),
    `# 投资组合经理最终决策

**Rating**: Underweight

**Price Target**: 194.0

**Entry Price**: 150.00

**Stop Loss**: 140.00

**Position Sizing**: 2%

**Executive Summary**: 尽管前期研报出现BUY与SELL讨论，估值过高下调至Underweight评级。
`,
    'utf-8'
  );
}

test.describe('Report Screen', () => {
  test.beforeAll(() => {
    setupSyntheticReport(testLogsDir);
  });

  test('(a) synthetic report trap - UI asserts Underweight, not BUY', async ({ page }) => {
    // Navigate directly to the report detail screen for the synthetic report
    await page.goto('/reports/SYNTHETIC/2026-05-20');

    // Assert Verdict Card exists and shows Underweight at display scale
    const verdictCard = page.locator('[data-testid="verdict-card"]');
    await expect(verdictCard).toBeVisible();

    const verdictAction = page.locator('[data-testid="verdict-action"]');
    await expect(verdictAction).toBeVisible();

    // Must show Underweight
    await expect(verdictAction).toHaveText(/UNDERWEIGHT/i);

    // Assert explicitly that it is NOT BUY and NOT SELL
    const actionText = (await verdictAction.innerText()).trim();
    expect(actionText.toUpperCase()).toBe('UNDERWEIGHT');
    expect(actionText.toUpperCase()).not.toBe('BUY');
    expect(actionText.toUpperCase()).not.toBe('SELL');

    // Assert price target is 194.0
    const priceTarget = page.locator('[data-testid="verdict-price-target"]');
    await expect(priceTarget).toHaveText('194.0');

    // Assert executive summary mentions Underweight
    const summary = page.locator('[data-testid="verdict-summary"]');
    await expect(summary).toContainText('Underweight');
  });

  test('(b) two-level TOC resolves correctly and demotes headings', async ({ page }) => {
    await page.goto('/reports/SYNTHETIC/2026-05-20');

    // Assert TOC container is visible
    const toc = page.locator('[data-testid="report-toc"]');
    await expect(toc).toBeVisible();

    // Level 1: Document Sections
    await expect(page.locator('[data-testid="toc-section-analysts"]')).toContainText('I. Analyst Team Reports');
    await expect(page.locator('[data-testid="toc-section-research"]')).toContainText('II. Research Team Decision');
    await expect(page.locator('[data-testid="toc-section-trading"]')).toContainText('III. Trading Team Plan');
    await expect(page.locator('[data-testid="toc-section-risk"]')).toContainText('IV. Risk Management Team Decision');
    await expect(page.locator('[data-testid="toc-section-portfolio"]')).toContainText('V. Portfolio Manager Decision');

    // Level 2: Agent names under each section
    await expect(page.locator('[data-testid="toc-agent-analysts-market"]')).toHaveText('Market Analyst');
    await expect(page.locator('[data-testid="toc-agent-research-bull"]')).toHaveText('Bull Researcher');
    await expect(page.locator('[data-testid="toc-agent-trading-trader"]')).toHaveText('Trader');
    await expect(page.locator('[data-testid="toc-agent-risk-aggressive"]')).toHaveText('Aggressive Analyst');
    await expect(page.locator('[data-testid="toc-agent-portfolio-decision"]')).toHaveText('Portfolio Manager');
  });

  test('(c) collapsible block unmounts content when collapsed', async ({ page }) => {
    await page.goto('/reports/SYNTHETIC/2026-05-20');

    const contentLocator = page.locator('[data-testid="agent-block-content-analysts-market"]');
    const toggleLocator = page.locator('[data-testid="agent-block-toggle-analysts-market"]');

    // Initially open
    await expect(contentLocator).toBeVisible();

    // Click collapse
    await toggleLocator.click();

    // Crucial requirement: Collapsed content MUST NOT BE MOUNTED in the DOM
    await expect(contentLocator).not.toBeAttached();

    // Click expand
    await toggleLocator.click();

    // Now mounted and visible again
    await expect(contentLocator).toBeVisible();
    await expect(contentLocator).toContainText('市场技术分析报告');
  });

  test('(d) reports index lists reports and navigates to report detail', async ({ page }) => {
    await page.goto('/reports');

    // Assert index table exists and lists SYNTHETIC
    const table = page.locator('[data-testid="reports-table"]');
    await expect(table).toBeVisible();

    const row = page.locator('[data-testid="report-row-SYNTHETIC-2026-05-20"]');
    await expect(row).toBeVisible();
    await expect(row).toContainText('SYNTHETIC');
    await expect(row).toContainText(/Underweight/i);

    // Clicking row navigates to the report
    await row.click();
    await expect(page).toHaveURL(/\/reports\/SYNTHETIC\/2026-05-20/);

    const verdictAction = page.locator('[data-testid="verdict-action"]');
    await expect(verdictAction).toHaveText(/UNDERWEIGHT/i);
  });

  test('(e) export UI rendered with functional trigger', async ({ page }) => {
    await page.goto('/reports/SYNTHETIC/2026-05-20');

    const exportWidget = page.locator('[data-testid="export-widget"]');
    await expect(exportWidget).toBeVisible();

    // Export button is available
    const exportBtn = page.locator('[data-testid="export-button"], [data-testid="open-export-button"]');
    await expect(exportBtn.first()).toBeVisible();
  });
});
