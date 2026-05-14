# TradingAgents UI

[中文说明](README_zh.md)

A local web app for [TradingAgents](https://github.com/TauricResearch/TradingAgents). Open it like a desktop app, enter your settings, run an analysis, and read the report in the same window.

![Embedded HTML report](images/trade-ui-embedded-html-report.png)

## One-Click Launch

### macOS

Create the app once:

```bash
./scripts/install-macos-app.sh
```

Then double-click:

```text
TradingAgents UI.app
```

It starts the local Streamlit server and opens `http://localhost:8501` in a standalone Chrome/Edge app window.

`TradingAgents UI.app` is macOS-only. On Windows, use the `.bat` launcher below.

### Windows

After the first install, double-click:

```text
scripts\launch-local-webapp.bat
```

It starts the local server in the background and opens:

```text
http://localhost:8501
```

For a more app-like workflow, create a desktop shortcut to the `.bat` file.

### All Platforms

```bash
trade-ui
```

From this checkout during local development:

```bash
./run.sh
```

## First Install

```bash
git clone https://github.com/Kevoyuan/tradingagents-ui.git
cd tradingagents-ui
python3 -m pip install -e .
```

Then choose your launcher:

- macOS: run `./scripts/install-macos-app.sh`, then double-click `TradingAgents UI.app`
- Windows: double-click `scripts\launch-local-webapp.bat`
- Linux/other: run `trade-ui`

## How To Use

1. Open the local UI
2. Fill in ticker, date, language, analyst team, model, and API keys in the sidebar
3. Click **Run Analysis**
4. Open **Browse Reports** when the analysis is done
5. Read the embedded HTML report, or switch back to Markdown

API keys are saved locally for the next launch. Cloud deployments keep keys session-only.

## Built-In TradingAgents Update Check

The app silently checks GitHub once when it opens.

If an update is available, an update icon appears next to the **TradingAgents** logo in the upper-left sidebar. If the icon is not there, the app did not detect an available update.

Click the icon to install or update TradingAgents from GitHub. Restart the app afterward so already-loaded Python modules refresh cleanly.

## Reports

Browse Reports shows embedded HTML by default, so you do not need a separate browser window.

Embedded HTML rendering is local-only. It uses the saved Markdown report and does not call an LLM or spend API tokens.

You can:

- Select a report, switch HTML/Markdown, and copy Markdown from one toolbar
- Jump through sections with the report table of contents
- Use fixed Top/Bottom buttons for long reports
- Read reports in the dark Quant Terminal theme

Historical reports are stored under:

```text
~/.tradingagents/logs/.../reports/
```

## Phone Access

When your computer and phone are on the same Wi-Fi:

```bash
trade-ui --lan
```

or:

```bash
./run-lan.sh
```

Open the printed URL on your phone, for example:

```text
http://192.168.1.23:8501
```

## Cloud Deploy

Deploy to Streamlit Community Cloud if you want access without keeping your computer online:

1. Push this repo to GitHub
2. Create a new Streamlit Community Cloud app
3. Set Main file path to `app.py`
4. Use Python 3.10 or newer
5. Do not store API keys in code or app secrets
6. Deploy and open the generated URL

Cloud notes:

- Each user enters their own API key in the sidebar
- Cloud reports live inside the cloud container and are best for temporary viewing
- Local-only services such as Ollama or localhost LiteLLM are not reachable from Streamlit Cloud

## Features

- One-click local launch
- macOS standalone app window
- Windows double-click launcher
- Sidebar setup for ticker, date, language, analyst team, model, and API keys
- Built-in TradingAgents GitHub update check
- Live agent progress, messages, tool calls, token counts, and timing
- Embedded historical HTML reports
- One-click Markdown copy
- HTML/Markdown view switch
- Report table of contents plus Top/Bottom navigation
- Local preference and API key persistence
- Same-Wi-Fi phone access

## More Screenshots

### Live Analysis Monitor

![Live analysis monitor](images/trade-ui-monitor.png)

### Report Viewer

![Report viewer](images/trade-ui-report-viewer.png)

### Report History

![Report history](images/trade-ui-history-reports.png)

## Developer Notes

UI entrypoint priority:

1. `TRADINGAGENTS_UI_APP_PATH`
2. `./app.py` in the current directory
3. Packaged fallback `app.py`

For a local TradingAgents checkout:

```bash
export TRADINGAGENTS_DIR=/path/to/tradingagents
```

Project layout:

```text
tradingagents-ui/
├── app.py
├── ui_config.py
├── ui_styles.py
├── ui_panels.py
├── preferences.py
├── scripts/
│   ├── install-macos-app.sh
│   ├── launch-local-webapp.sh
│   └── launch-local-webapp.bat
├── tools/
│   └── baoyu-markdown-to-html/
├── trade_ui/
│   └── cli.py
├── pyproject.toml
├── run.sh
└── run-lan.sh
```
