# TradingAgents UI

[中文说明](README_zh.md)

A local web app for [TradingAgents](https://github.com/TauricResearch/TradingAgents). Open it like a desktop app, enter your settings, run an analysis, and read the report in the same window.

![Embedded HTML report](images/trade-ui-embedded-html-report.png)

## Launching

There is one Streamlit app entrypoint: `app.py`.

For normal local use, launch through `trade-ui` or one of the included scripts. These wrappers set local mode (`TRADINGAGENTS_UI_LOCAL=1`) so API keys can be saved on this computer, then start Streamlit for `app.py`.

The macOS and Windows launchers first look for an existing Python environment with Streamlit. If none is found, they use `uv` to create `.venv` and install this project automatically.

Direct `streamlit run app.py` is also supported for Streamlit Community Cloud and advanced debugging. Direct Streamlit mode does not save API keys to disk unless you explicitly enable local mode.

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

### Terminal

```bash
trade-ui
```

From this checkout during local development, use the equivalent wrapper:

```bash
./run.sh
```

Both commands start local mode and open the same UI at `http://localhost:8501`.

### Direct Streamlit

Use this for Streamlit Cloud or advanced debugging:

```bash
streamlit run app.py
```

In direct Streamlit mode, API keys stay session-only. To opt into local API-key persistence while bypassing the wrapper:

```text
# macOS/Linux
TRADINGAGENTS_UI_LOCAL=1 streamlit run app.py

# Windows PowerShell
$env:TRADINGAGENTS_UI_LOCAL="1"; streamlit run app.py
```

## First Install

Install `uv` once if you want the desktop launchers to bootstrap the Python environment automatically:

```text
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
git clone https://github.com/Kevoyuan/tradingagents-ui.git
cd tradingagents-ui
```

Then choose your launcher:

- macOS: run `./scripts/install-macos-app.sh`, then double-click `TradingAgents UI.app`
- Windows: double-click `scripts\launch-local-webapp.bat`
- Terminal on any OS: run `trade-ui`
- Local development checkout: run `./run.sh`

For terminal development, you can create the same environment manually:

```bash
uv venv --python 3.11
uv pip install -e .
```

## How To Use

1. Open the local UI
2. Fill in ticker, date, language, analyst team, model, and API keys in the sidebar
3. Click **Run Analysis**
4. Open **Browse Reports** when the analysis is done
5. Read the embedded HTML report, or switch back to Markdown

API keys are saved locally for the next launch. Cloud deployments keep keys session-only.

## Built-In TradingAgents Update Check

The app silently checks GitHub once when it opens.

Launch commands do not update TradingAgents before startup. Updates are handled inside the UI so every local launcher behaves the same way.

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
- Cloud runs `app.py` directly; do not use the local `trade-ui` wrapper there
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

The UI entrypoint is always `app.py`.

Local wrappers include `trade-ui`, `python -m trade_ui.cli`, `./run.sh`, `./run-lan.sh`, and the macOS/Windows launch scripts. They resolve the app path, set `TRADINGAGENTS_UI_LOCAL=1`, then exec Streamlit.

The macOS and Windows launch scripts prefer `.venv`, then other Python interpreters that can import Streamlit. If none is usable and `uv` is installed, they run `uv venv --python 3.11 .venv` and `uv pip install -e .` automatically. Override the bootstrap Python with `TRADINGAGENTS_UI_PYTHON_VERSION`.

Local wrapper app-path priority:

1. `TRADINGAGENTS_UI_APP_PATH`
2. `./app.py` in the current directory
3. Packaged fallback `app.py`

Direct `streamlit run app.py` bypasses the wrapper. That is the right path for Streamlit Cloud and useful for debugging, but it leaves API keys session-only unless `TRADINGAGENTS_UI_LOCAL=1` is set.

TradingAgents update checks live in `app.py` and are triggered from the sidebar update icon. The CLI does not install or update TradingAgents during startup.

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
