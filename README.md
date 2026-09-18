# TradingAgents UI

A local Streamlit desktop-style interface for running [TradingAgents](https://github.com/TauricResearch/TradingAgents) analyses and reading the resulting reports.

[中文说明](README_zh.md)

**Compatible with TradingAgents v0.3.1**

![TradingAgents UI analysis monitor](images/trade-ui-monitor.png)

## Quick Start

Requirements: Python 3.10+, [uv](https://docs.astral.sh/uv/), and Node.js 18+ (for frontend build).

```bash
git clone https://github.com/Kevoyuan/tradingagents-ui.git
cd tradingagents-ui
uv venv --python 3.11
uv pip install -e .
bash scripts/build-frontend.sh
trade-ui
```

### Launch Modes

- **Default (FastAPI + React)**: Run `trade-ui` to start the new React SPA and FastAPI backend server.
- **Legacy (Streamlit)**: Run `trade-ui --legacy` to launch the original Streamlit interface (`app.py`).

### Building the Frontend

The web UI frontend is built with React, Vite, and TypeScript. Build static assets before running the default interface or packaging:

```bash
bash scripts/build-frontend.sh
```

Compiled assets are placed into `trade_ui/static/` and packaged directly into wheels for pip distribution without requiring Node at runtime.

### macOS

```bash
./scripts/install-macos-app.sh
open "TradingAgents UI.app"
```

After the first setup, open `TradingAgents UI.app` normally.

### Windows

Double-click `scripts\launch-local-webapp.bat`. The launcher creates the local environment when needed and opens the app in your browser.

## First Run

1. Select an LLM provider and models.
2. Enter the required provider API key.
3. Enter a ticker such as `NVDA` or `BTC-USD`.
4. Choose the analyst team and research depth.
5. Click **Run Analysis**.

The live view shows agent progress, tool calls and report sections. Completed reports remain available under **Browse Reports**.

## Screenshots

### Embedded HTML Report

![Embedded HTML report](images/trade-ui-embedded-html-report.png)

### Report Viewer

![Report viewer](images/trade-ui-report-viewer.png)

### Report History

![Report history](images/trade-ui-history-reports.png)

### Provider Configuration

![Provider configuration](images/trade-ui-providers.png)

## Core Features

- Live multi-agent analysis progress
- Stock and crypto analysis paths
- TradingAgents checkpoint/resume support
- Native and custom LLM providers
- Markdown and embedded HTML reports
- Local report history and model-specific report files
- Optional local API key persistence

## API Keys and Privacy

Local launchers set local mode. When you save preferences or run an analysis, API keys are stored in:

```text
~/.tradingagents/.env
```

The file is created with user-only permissions where supported. Keys are not written to this repository or sent to Streamlit Cloud by the UI. They are passed only to the providers selected for the run.

Direct Streamlit and cloud deployments use session-only keys unless you configure platform secrets. See [Cloud deployment](docs/cloud-deployment.md).

Reports are stored under:

```text
~/.tradingagents/logs/
```

The latest complete report is linked at `~/.tradingagents/latest_report.md` when the operating system permits symlinks.

## TradingAgents Compatibility

This release supports TradingAgents `>=0.3.1,<0.4` and installs the exact `v0.3.1` tag by default. The in-app updater also installs the tag shown in its update prompt.

See [COMPATIBILITY.md](COMPATIBILITY.md) for the verified upstream releases and interface symbol contract matrix.

## Documentation

- [Compatibility Matrix](COMPATIBILITY.md)
- [Installation and alternative launch methods](docs/installation.md)
- [Providers and credentials](docs/providers.md)
- [Cloud deployment](docs/cloud-deployment.md)
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
