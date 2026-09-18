import { test, expect, APIRequestContext } from '@playwright/test';

async function ensureNoActiveRun(request: APIRequestContext) {
  try {
    const res = await request.get('http://127.0.0.1:8000/api/runs');
    if (res.ok()) {
      const runs = await res.json();
      for (const r of runs) {
        if (r.status === 'running' || r.status === 'pending') {
          await request.post(`http://127.0.0.1:8000/api/runs/${r.run_id}/cancel`);
        }
      }
    }
  } catch {
    // Ignore error if backend is just starting
  }
}

test.describe('Monitor Screen', () => {
  test.beforeEach(async ({ request }) => {
    await ensureNoActiveRun(request);
  });

  test('(a) happy path - a stub run streams into the record and agent statuses advance', async ({
    page,
    request,
  }) => {
    // 1. Start a stub run with a modest step delay
    const createRes = await request.post('http://127.0.0.1:8000/api/runs', {
      data: {
        ticker: 'FORM',
        trade_date: '2026-05-05',
        use_stub: true,
        step_delay: 0.04,
      },
    });
    expect(createRes.status()).toBe(201);
    const { run_id } = await createRes.json();

    // 2. Open the monitor for this run
    await page.goto(`/?runId=${run_id}`);

    // Assert masthead and ticker
    await expect(page.locator('header')).toContainText('FORM');

    // Assert verdict band and stages exist
    await expect(page.locator('[data-testid="verdict-band"]')).toBeVisible();
    await expect(page.locator('[data-testid="stage-rail"]')).toBeVisible();

    // Assert events stream into the record
    await expect(page.locator('[data-testid="the-record"]')).toBeVisible();
    await expect(page.locator('[data-testid^="event-"]').first()).toBeVisible({ timeout: 10000 });

    // Assert that the run completes and displays Buy verdict
    const verdictAction = page.locator('[data-testid="verdict-action"]');
    await expect(verdictAction).toHaveText(/BUY/i, { timeout: 20000 });

    // Assert stages have advanced to completion
    await expect(page.locator('[data-testid="stage-analyst"]')).toContainText('4/4');
    await expect(page.locator('[data-testid="stage-research"]')).toContainText(/2\/|3\//);
    await expect(page.locator('[data-testid="stage-trading"]')).toContainText('1/1');
    await expect(page.locator('[data-testid="stage-portfolio"]')).toContainText('1/1');

    // Assert right rail roster shows agents done
    const marketAgent = page.locator('[data-testid="agent-item-market"]');
    await expect(marketAgent).toBeVisible();

    // Assert the record has multiple untruncated entries
    const countText = await page.locator('[data-testid="record-count"]').innerText();
    expect(countText).toMatch(/\d+ entries · untruncated/);
  });

  test('(b) reload-and-reconnect - reload mid-run and assert the record is complete with no duplicate seq', async ({
    page,
    request,
  }) => {
    // 1. Start a stub run with step_delay=0.08 so we can reliably reload mid-run
    const createRes = await request.post('http://127.0.0.1:8000/api/runs', {
      data: {
        ticker: 'MSFT',
        trade_date: '2026-05-21',
        use_stub: true,
        step_delay: 0.08,
      },
    });
    expect(createRes.status()).toBe(201);
    const { run_id } = await createRes.json();

    // 2. Open the monitor
    await page.goto(`/?runId=${run_id}`);

    // Wait until at least 4 events have arrived
    await expect(page.locator('[data-testid^="event-"]').nth(3)).toBeVisible({ timeout: 10000 });

    // 3. Reload mid-run
    await page.reload();

    // 4. Wait for the run to complete after reload
    await expect(page.locator('[data-testid="verdict-action"]')).toHaveText(/BUY/i, {
      timeout: 25000,
    });

    // 5. Inspect the stored events in sessionStorage to verify complete sequence with no duplicates
    const storedEvents = await page.evaluate((id) => {
      const raw = sessionStorage.getItem(`tradingagents_events_${id}`);
      return raw ? JSON.parse(raw) : [];
    }, run_id);

    expect(storedEvents.length).toBeGreaterThanOrEqual(10);

    const seqs = storedEvents.map((e: { seq: number }) => e.seq);
    const uniqueSeqs = new Set(seqs);

    // No duplicate sequences
    expect(uniqueSeqs.size).toBe(seqs.length);

    // Contiguous sequence starting from 1
    for (let i = 0; i < seqs.length; i++) {
      expect(seqs[i]).toBe(i + 1);
    }
  });

  test('(c) Stop cancels - clicking Stop cancels the run and the UI reflects the cancelled state', async ({
    page,
    request,
  }) => {
    // 1. Start a stub run with step_delay=0.15 so it remains running while we click Stop
    const createRes = await request.post('http://127.0.0.1:8000/api/runs', {
      data: {
        ticker: 'NVDA',
        trade_date: '2026-05-22',
        use_stub: true,
        step_delay: 0.15,
      },
    });
    expect(createRes.status()).toBe(201);
    const { run_id } = await createRes.json();

    // 2. Open the monitor
    await page.goto(`/?runId=${run_id}`);

    // 3. Wait for the stop button to be visible and click it
    const stopBtn = page.locator('[data-testid="stop-run-button"]');
    await expect(stopBtn).toBeVisible({ timeout: 5000 });
    await stopBtn.click();

    // 4. Assert UI reflects cancelled state
    const verdictAction = page.locator('[data-testid="verdict-action"]');
    await expect(verdictAction).toHaveText(/CANCELLED/i, { timeout: 10000 });

    // Stop button is gone / replaced by New run button
    await expect(page.locator('[data-testid="new-run-button"]')).toBeVisible();

    // 5. Assert backend reflects cancelled status
    const statusRes = await request.get(`http://127.0.0.1:8000/api/runs/${run_id}`);
    expect(statusRes.ok()).toBeTruthy();
    const runHeader = await statusRes.json();
    expect(runHeader.status).toBe('cancelled');
  });
});
