# TradingAgents UI

A local Streamlit desktop-style interface for running [TradingAgents](https://github.com/TauricResearch/TradingAgents) analyses and reading the resulting reports.

**Compatible with TradingAgents v0.3.1**

![TradingAgents UI analysis monitor](images/trade-ui-monitor.png)

## Quick Start

Requirements: Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Kevoyuan/tradingagents-ui.git
cd tradingagents-ui
uv venv --python 3.11
uv pip install -e .
```

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

Provider metadata and model choices come from the upstream v0.3.1 registry where possible. UI-only compatible endpoints are maintained separately.

## Documentation

- [Installation and alternative launch methods](docs/installation.md)
- [Providers and credentials](docs/providers.md)
- [Cloud deployment](docs/cloud-deployment.md)
- [LAN access](docs/lan-access.md)
- [Development](docs/development.md)

## Development

```bash
uv pip install -e .
pytest tests
ruff check .
```

See [docs/development.md](docs/development.md) for architecture, environment variables and direct Streamlit usage.
