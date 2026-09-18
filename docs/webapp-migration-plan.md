# Web app migration plan (Streamlit → React + FastAPI)

This file is the single source of truth for the migration. Every phase dispatch reads this
file. Do not re-derive decisions that are already recorded here.

## 0. Context you must not break

- The repo is a thin Python layer over the upstream `tradingagents` package (pinned
  `v0.3.1`, git install). Upstream is installed in the venv; do not vendor or patch it.
- `app.py` (~1.7k lines) is the current Streamlit UI. It stays working until Phase 5.
- The existing 49 tests in `tests/` must stay green in every phase.
- Tooling: run everything through the worktree venv.
  - `unset PYTHONPATH` before Python commands (a global `PYTHONPATH` otherwise shadows
    upstream's `cli` package).
  - `.venv/bin/python -m pytest tests/ -q`
  - `.venv/bin/python -m ruff check .`
  - `.venv/bin/python -m mypy app.py ui_config.py ui_panels.py ui_styles.py trade_ui/`
- Reports already on disk (32 of them) live at
  `~/.tradingagents/logs/<TICKER>/<YYYY-MM-DD>/reports/`. Do not migrate or rewrite them;
  the new report reader must read this exact structure.

## 1. Architecture decisions (already made, do not relitigate)

- Backend: FastAPI + uvicorn. Frontend: React + Vite + TypeScript, Tailwind for tokens.
- Transport: Server-Sent Events. No WebSockets.
- **Exactly one run at a time.** A second `POST /api/runs` while one is active returns 409.
- Runs survive a browser refresh (the event log is on disk and SSE replays). They do **not**
  survive a server restart: after a restart only history is readable, nothing resumes.
- Cancellation is cooperative: a flag checked inside the `runner.stream()` loop. Upstream has
  no cancel API; do not modify upstream.
- Single local user. No auth, no multi-session isolation.

## 2. Event stream contract

Every run appends JSON Lines to `~/.tradingagents/runs/<run_id>/events.jsonl`, and a
`~/.tradingagents/runs/<run_id>/run.json` holds the run header (config, status, timestamps).

Each line:

```json
{
  "seq": 1841,
  "ts": "2026-05-05T09:48:28.412+00:00",
  "run_id": "7f3c2a",
  "kind": "agent_message",
  "agent": "fundamentals",
  "team": "analyst",
  "payload": {}
}
```

- `seq` is a monotonically increasing integer starting at 1, unique per run.
- `agent` is the analyst key (`market`/`social`/`news`/`fundamentals`) or a slug of the
  agent name (e.g. `bull_researcher`), or `null`.
- `team` is one of `analyst` / `research` / `trading` / `risk` / `portfolio`, or `null`.
- `kind` is one of:
  `run_state` | `agent_status` | `agent_message` | `user_message` | `tool_call` |
  `tool_result` | `stats` | `report_section` | `verdict` | `error`.

Payload shapes:

| kind | payload |
|---|---|
| `run_state` | `{"status": "pending"\|"running"\|"completed"\|"cancelled"\|"failed", "ticker": ..., "trade_date": ..., "config": {...}}` |
| `agent_status` | `{"agent": "<slug>", "status": "pending"\|"running"\|"done"\|"failed"}` |
| `agent_message` | `{"text": "<FULL untruncated text>", "model": ..., "tokens_in": int, "tokens_out": int, "latency_ms": int, "cost_usd": float\|null}` |
| `user_message` | `{"text": "..."}` |
| `tool_call` | `{"tool": "...", "args": {...}\|[...]\|"...", "call_id": "..."}` |
| `tool_result` | `{"tool": "...", "call_id": "...", "ok": bool, "duration_ms": int, "result": "<preview>", "truncated": bool, "full_ref": "<path or null>"}` |
| `stats` | `{"llm_calls": int, "tool_calls": int, "tokens_in": int, "tokens_out": int, "cost_usd": float\|null}` |
| `report_section` | `{"key": "market_report", "title": "Market Analyst", "markdown": "...", "complete": bool}` |
| `verdict` | see §3 |
| `error` | `{"message": "...", "traceback": "..."}` |

**Hard requirement:** `agent_message.payload.text` stores the full text. The current
`compact_text(content, 300)` truncation must not be the stored value; truncation is a
presentation concern only. Same for tool results: store the full result on disk and put a
preview in the event with `truncated: true` and a `full_ref` the frontend can fetch.

## 3. Verdict contract

```json
{
  "rating": "Buy|Overweight|Hold|Underweight|Sell",
  "source_section": "portfolio" | "trader",
  "price_target": "194.0",
  "executive_summary": "...",
  "entry_price": "115.0",
  "stop_loss": "110.0",
  "position_sizing": "2-3%"
}
```

- `rating` comes from upstream: `from tradingagents.agents.utils.rating import parse_rating`
  (vocabulary constant: `RATINGS_5_TIER`). Do not write your own rating heuristic.
- While the Portfolio Manager decision has not landed, emit `source_section: "trader"` with a
  best-effort action parsed from the Trader's plan. Once the PM decision lands, emit
  `source_section: "portfolio"` and it wins.
- Numeric fields (`price_target`, `entry_price`, `stop_loss`, `position_sizing`) are
  best-effort extractions and are `null` when absent. Never invent them.

### DANGER: never scan the whole report for an action word

Verified on a real report
(`~/.tradingagents/logs/NBIS/2026-09-18/reports/complete_report.md`):

- line 1029: `## 最终交易建议：BUY NBIS（NMS），分批建仓`
- line 1423: `## 最终交易建议：SELL NBIS (NMS)`
- line 1735 (inside `## V. Portfolio Manager Decision`): `**Rating**: Underweight`

The true verdict is **Underweight**. Whole-document keyword scanning returns BUY and is
wrong. Only read the Portfolio Manager decision.

## 4. Report read path

Do **not** read `complete_report.md` (177–348 KB) to render the report. Read the per-section
files that already exist next to it:

| Document section | Files |
|---|---|
| I. Analyst Team Reports | `1_analysts/market.md`, `1_analysts/sentiment.md`, `1_analysts/news.md`, `1_analysts/fundamentals.md` |
| II. Research Team Decision | `2_research/bull.md`, `2_research/bear.md`, `2_research/manager.md` |
| III. Trading Team Plan | `3_trading/trader.md` |
| IV. Risk Management Team Decision | `4_risk/aggressive.md`, `4_risk/conservative.md`, `4_risk/neutral.md` |
| V. Portfolio Manager Decision | `5_portfolio/decision.md` |

Files may be missing (older runs, partially complete runs). Missing files are skipped, not
errors. The legacy `## I.`…`## V.` headings exist only in the merged file; the per-section
files do not carry them, so the reader supplies the section titles.

### Heading normalisation (required, or the outline is useless)

Agents' own markdown starts at H1 and uses H2/H3 internally. Measured on the real NBIS
report: 5 H1, 103 H2, 31 H3 — but the document only has **5** real `## I.`…`## V.` sections.
The other 98 H2s are agent-internal headings. Rendering naively produces a garbage TOC.

Rule when rendering:

- document title = H1
- the five sections = H2
- agent name = H3
- everything from an agent file is demoted by **+3**, clamped at H6
  (agent H1 → H4, agent H2 → H5, agent H3 → H6)

The TOC exposes exactly two levels: H2 sections and H3 agent names.

### Report section payload

`GET /api/reports/{ticker}/{date}` returns sections with `title`, `slug`, and an ordered list
of agent blocks, each with `name`, `slug`, `markdown`, and `complete`. The frontend renders
one collapsible block per agent and does not mount collapsed content.

## 5. HTTP surface

| Method | Path | Notes |
|---|---|---|
| POST | `/api/runs` | body = run config; `{run_id}`; **409** if a run is active |
| GET | `/api/runs` | history index (from `~/.tradingagents/runs/`) |
| GET | `/api/runs/{id}` | run header + current stats + verdict |
| GET | `/api/runs/{id}/events?after=<seq>` | **SSE**: replay from `after` exclusive, then follow live |
| POST | `/api/runs/{id}/cancel` | cooperative cancel; 409 if not running |
| GET | `/api/reports` | history index over `~/.tradingagents/logs/` |
| GET | `/api/reports/{ticker}/{date}` | per-section metadata + markdown (§4) |
| POST | `/api/reports/{ticker}/{date}/export` | start export (§6); 202 |
| GET | `/api/reports/{ticker}/{date}/export` | cached export HTML; **404** if not generated |
| GET | `/api/providers` | provider + model catalog (reuse `ui_config`) |
| GET/PUT | `/api/credentials` | local mode only (reuse `preferences` / runtime env) |
| GET | `/api/upstream` | compat + update status |
| GET | `/api/health` | liveness; the macOS launcher probes this |

SSE replay must be exact: no gaps and no duplicates for a given `after`.

## 6. Export is the only place Bun survives

The current export spawns Bun + the vendored `tools/baoyu-markdown-to-html` converter with
`--theme quant-terminal`. History: that whole pipeline used to run **on view**, which is the
single biggest performance problem in the current app.

- Export runs **only** on `POST .../export`.
- Output: `<reports_dir>/complete_report__export-<HTML_REPORT_THEME_VERSION>.html`
  (reuse the existing `HTML_REPORT_THEME_VERSION` constant; the version in the filename is
  what invalidates a stale export when the theme changes).
- `GET .../export` returns the cached file, or 404.
- Export failure must never break reading. Surfacing the error in the export UI is enough.
- `GET .../export/status` returning `{"state": "idle"|"running"|"ready"|"failed", "error": ...}`
  is acceptable so the UI can render three states.

## 7. Frontend

- `frontend/` — Vite + React + TypeScript. Tailwind carries design tokens.
- Three screens: Monitor, Reports, Settings.
- Design tokens come from the approved mockup
  `~/.gstack/projects/Kevoyuan-tradingagents-ui/designs/run-monitor-webapp-20260918/variant-E.html`
  — Archivo grotesque, hairline rules, tabular numerals, paper white, and exactly one signal
  colour reserved for the recommendation.
- Verdict colour mapping: `Buy`/`Overweight` green, `Hold` neutral grey,
  `Underweight`/`Sell` red. Conviction differences use a marker, not a second colour.
- The verdict is the visual anchor: set the action keyword at display scale in a band that
  never scrolls away.
- Markdown rendering: `react-markdown` + `remark-gfm` (tables) + `rehype-sanitize`.
  Content is LLM-generated; sanitise it. Do not use `dangerouslySetInnerHTML` unsanitised.
- Monitor composition: masthead; persistent verdict band; five-stage linear rail
  (Analysts / Research / Trading / Risk / Portfolio); "the record" (the untruncated event
  stream with tool args and results nested as evidence); right rail with roster spine, token
  burn chart and run stats.
- Anti-slop rules that were applied in the approved mockup and must survive implementation:
  no purple gradient, no rounded-card-with-left-colour-bar pattern, no emoji icons, no
  GitHub-dark `#0D1117`+neon shortcut, body ≥14px, labels ≥12px, body contrast ≥4.5:1.

## 8. Packaging

- Vite build output goes to `trade_ui/static/` and ships in the wheel. Node is a build-time
  dependency only, never a runtime one.
- `trade-ui` starts uvicorn and serves the static assets. `--legacy` starts the existing
  Streamlit app. Default is the new app.
- `run.sh`, `run-lan.sh`, the macOS `.app` and the Windows `.bat` keep working unchanged.
- `app.py`, `ui_styles.py`, `.streamlit/` are marked deprecated with a removal note. They
  are removed in a later release, not in this one.

## 9. Upstream contract tests

New package `tradingagents_contract/` asserting these symbols exist with the expected shape:

- `tradingagents.graph.trading_graph.TradingAgentsGraph` — constructor signature and
  `.graph.stream`
- `TradingAgentsGraph._run_signature`
- `graph.propagation.propagator.create_initial_state`
- `graph.workflow.compile(checkpointer=...)`
- `tradingagents.reporting.write_report_tree` — including the `1_analysts`/`2_research`/
  `3_trading`/`4_risk`/`5_portfolio` directory structure the report reader depends on
- `tradingagents.dataflows.utils.safe_ticker_component`
- `tradingagents.llm_clients.model_catalog.MODEL_OPTIONS`
- `tradingagents.llm_clients.api_key_env.PROVIDER_API_KEY_ENV`
- `tradingagents.agents.utils.rating.RATINGS_5_TIER` and `parse_rating`
- `cli.stats_handler.StatsCallbackHandler` — note `cli` is a top-level package that ships
  with upstream; a global `PYTHONPATH` shadows it (see §0)

CI runs this suite twice: once against `v0.3.1` and once against the latest upstream tag, and
reports which symbol changed. Output a `COMPATIBILITY.md` matrix.

## 10. Phases, ownership and acceptance

Each phase is dispatched separately. **Touch only your phase's files.** If you need a change
outside your owned paths, stop and report instead of editing.

### P1 — Backend skeleton, run registry, event bus, SSE

Owned paths: `trade_ui/server/**`, `tests/server/**`

Deliverable: a FastAPI app with the run registry (single active run, 409 on conflict), the
event bus writing `events.jsonl`, SSE with exact `after` replay, cooperative cancel, and a
fake/stub upstream so tests never hit the network.

Acceptance (paste raw output):
```
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/server -q
.venv/bin/python -m ruff check .
```
Also demonstrate by hand, with raw output: one stub run to completion; an SSE read with
`after=<mid-seq>` that returns the tail exactly once.

### P2 — Report section parser + verdict extraction

Owned paths: `trade_ui/report_index.py`, `tests/test_report_index.py`

Deliverable: the section model of §4, the +3 heading normalisation, and verdict extraction
per §3. Must work on the existing on-disk reports without modifying them.

Acceptance (paste raw output):
```
.venv/bin/python -m pytest tests/test_report_index.py -q
.venv/bin/python -m pytest tests/ -q
```
Required regression fixture: the real report
`~/.tradingagents/logs/NBIS/2026-09-18/reports/` must yield
`rating == "Underweight"`, `source_section == "portfolio"`, `price_target == "194.0"`.
Assert explicitly that it is **not** `"Buy"` and **not** `"Sell"`.

### P3 — Frontend scaffold + Monitor

Owned paths: `frontend/**` (scaffold, tokens, Monitor)

Deliverable: Vite + React + TS project, Tailwind tokens from §7, the Monitor screen, and an
SSE client that reconnects with `after` after a reload.

Acceptance (paste raw output):
```
cd frontend && npm ci || npm install
cd frontend && npx tsc --noEmit
cd frontend && npx playwright test monitor
```
Three Playwright cases required: happy path, reload-and-reconnect, Stop cancels.

### P4 — Report screen + export endpoint

Owned paths: `frontend/**` (Report screen only), `trade_ui/server/export.py`,
`tests/server/test_export.py`

Deliverable: the two-level TOC, collapsible agent blocks, the verdict card, and the export
endpoint of §6 with three UI states.

Acceptance (paste raw output):
```
.venv/bin/python -m pytest tests/server -q
cd frontend && npx playwright test report
```
Required: opening the NBIS report in the UI shows **Underweight**, and the TOC two levels
resolve correctly despite the agent files' own H1/H2/H3.

### P5 — Packaging, `--legacy`, CI contract job

Owned paths: `pyproject.toml`, `MANIFEST.in`, `.github/workflows/ci.yml`,
`trade_ui/cli.py`, `scripts/wheel-smoke-test.sh`, `tradingagents_contract/**`,
`COMPATIBILITY.md`, `README.md`, `docs/*`

Deliverable: static assets in the wheel, `trade-ui` serving the new app, `--legacy` serving
Streamlit, the contract suite and CI job.

Carried over from P1 review (must be fixed here):

- `trade_ui/server/app.py` sets `allow_origins=["*"]` together with
  `allow_credentials=True`. Browsers reject that combination, and a wildcard origin is
  wrong for a local app anyway. Bind CORS to the actual localhost origins
  (`http://localhost:<port>` / `http://127.0.0.1:<port>`) or drop the CORS middleware
  entirely once the frontend is served same-origin.
- Confirm the static-asset mount serves the SPA at `/` without shadowing the `/api` routes
  or the root `/health` probe the macOS launcher depends on.

Acceptance (paste raw output):
```
unset PYTHONPATH && .venv/bin/python -m build
bash scripts/wheel-smoke-test.sh
.venv/bin/python -m pytest tradingagents_contract -q
```
Plus: `trade-ui --help` documents both modes.

## 11. Stop conditions

- Two consecutive acceptance failures in the same phase: stop and report raw output. Do not
  widen the change.
- Any need to touch upstream `tradingagents` source: stop.
- Any need to change the contracts in §2–§9: stop and report the reason. They were decided
  against real data and a review process.
- Never delete or rewrite reports under `~/.tradingagents/logs/`.
