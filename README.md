# TradingAgents UI

A local web app for running [TradingAgents](https://github.com/TauricResearch/TradingAgents) analyses and reading the resulting reports. The interface is a React single-page app served by a FastAPI backend; the analysis engine is the upstream `tradingagents` package, unmodified.

[中文说明](README_zh.md)

**Compatible with TradingAgents v0.5.0**

![TradingAgents UI analysis monitor](images/trade-ui-monitor.png)

## Quick Start

Requirements: Python 3.10+, [uv](https://docs.astral.sh/uv/), and Node.js 18+ (to build the frontend).

```bash
git clone https://github.com/Kevoyuan/tradingagents-ui.git
cd tradingagents-ui
uv venv --python 3.11
uv pip install -e .
bash scripts/build-frontend.sh
trade-ui
```

The app starts on <http://localhost:8501>.

### Launch Options

The installed command accepts a custom port and a LAN binding:

```bash
trade-ui --port 9000   # custom port
trade-ui --lan         # bind 0.0.0.0 for phone/tablet access
```

See [LAN access](docs/lan-access.md) for details.

### Building the Frontend

The frontend is built with React, Vite, and TypeScript. Build the static assets before running the interface or packaging:

```bash
bash scripts/build-frontend.sh
```

Compiled assets are written to `trade_ui/static/` and packaged into wheels, so pip installs do not need Node at runtime.

### macOS

```bash
./scripts/install-macos-app.sh
open "TradingAgents UI.app"
```

After the first setup, open `TradingAgents UI.app` normally.

### Windows

Double-click `scripts\launch-local-webapp.bat`. The launcher creates the local environment when needed and opens the app in your browser.

## First Run

1. Open **Settings** (the gear in the left rail) and choose the LLM provider and models.
2. Enter the provider API key. Saved keys are written to `~/.tradingagents/.env`.
3. Set the ticker (for example `NVDA` or `BTC-USD`), trade date, output language, analyst team, and research depth.
4. Click **New Run** in the top right, confirm the ticker and date, then press **Start Run**.

The Monitor shows agent progress, streamed messages, tool calls, token burn, and report sections as they arrive. Completed reports remain available under **Reports**.

## Screenshots

### Exported HTML Report

![Exported HTML report](images/trade-ui-exported-html-report.png)

### Report Viewer

![Report viewer](images/trade-ui-report-viewer.png)

### Report History

![Report history](images/trade-ui-history-reports.png)

### Provider Configuration

![Provider configuration](images/trade-ui-providers.png)

## Core Features

- Live multi-agent analysis progress with streamed messages and tool evidence
- Price and indicator charts built from the data agents cite
- Stock and crypto analysis paths
- TradingAgents checkpoint/resume support
- Native and custom LLM providers
- Markdown report viewer with one-click themed HTML export
- Local report history and model-specific report files
- Token and cost accounting from a generated price table
- Optional local API key persistence

## API Keys and Privacy

Local launchers set local mode. When you save preferences or run an analysis, API keys are stored in:

```text
~/.tradingagents/.env
```

The file is created with user-only permissions (mode 600) where supported. Keys are never written to this repository by the UI; they live only on this machine and are passed only to the provider selected for the run.

Reports are stored under:

```text
~/.tradingagents/logs/
```

The latest complete report is linked at `~/.tradingagents/latest_report.md` when the operating system permits symlinks.

## TradingAgents Compatibility

This release supports TradingAgents `>=0.5.0,<0.6` and installs the exact `v0.5.0` tag
by default. The in-app updater also installs the tag shown in its update prompt.

See [COMPATIBILITY.md](COMPATIBILITY.md) for the verified upstream releases and interface symbol contract matrix.

## Documentation

- [Compatibility Matrix](COMPATIBILITY.md)
- [Installation and alternative launch methods](docs/installation.md)
- [Providers and credentials](docs/providers.md)
- [LAN access](docs/lan-access.md)
- [Development](docs/development.md)

## Development

```bash
uv pip install -e .
bash scripts/build-frontend.sh
pytest tests/
pytest tradingagents_contract/
ruff check .
```

See [docs/development.md](docs/development.md) for architecture, environment variables and development usage.
