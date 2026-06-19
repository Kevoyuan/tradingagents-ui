# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`tradingagents-ui` is a Streamlit web UI for [TradingAgents](https://github.com/TauricResearch/TradingAgents) — a local desktop-style app for configuring LLM analysts, running a multi-agent trading analysis, and reading the resulting reports embedded in the page. The repo is a thin Python layer on top of the upstream `tradingagents` package (installed from Git via `pyproject.toml`).

Single Streamlit entrypoint: `app.py` (1.6k lines). The package adds a CLI wrapper (`trade_ui/`) and a few launcher scripts (`scripts/`) for macOS/Windows one-click launching.

## Common Commands

Install (editable, into the active venv):

```bash
uv venv --python 3.11
uv pip install -e .
```

Run the UI (this is what the `.app` and `.bat` launchers call):

```bash
./run.sh                # local dev, http://localhost:8501
./run-lan.sh            # bind 0.0.0.0 for phone access
trade-ui --lan          # equivalent via installed console_script
trade-ui --port 9000    # custom port (passed through to streamlit)
```

Direct Streamlit is supported for cloud/deep debugging, but it bypasses the local wrapper and leaves API keys session-only unless `TRADINGAGENTS_UI_LOCAL=1` is set:

```bash
streamlit run app.py
```

Run tests:

```bash
pytest tests/                                   # all tests
pytest tests/test_cli.py                        # CLI helper tests only
pytest tests/test_app_helpers.py                # app.py pure helper tests
pytest -k safe_report_filename_part             # single test by name
```

Lint / format / type-check (config in `pyproject.toml`):

```bash
ruff check .
ruff format .
mypy app.py ui_config.py ui_panels.py ui_styles.py trade_ui/
```

No Makefile, no `tox`, no pre-commit hooks are wired up. CI does not exist in this repo.

## High-Level Architecture

```
app.py                  Streamlit UI (sidebar, run, live monitor, report viewer, html export)
ui_config.py            Constants: PROVIDERS, PROVIDER_URLS, PROVIDER_API_KEY_ENV,
                        ANALYST_OPTIONS, ALL_TEAMS, ANALYST_KEY_MAP, LANGUAGES, etc.
ui_panels.py            HTML render helpers for the live agent progress and message tables
ui_styles.py            One big CUSTOM_CSS string injected via st.markdown
preferences.py          JSON-backed user prefs at ~/.tradingagents/ui_preferences.json
                        plus ~/.tradingagents/.env for API keys (local mode only)
trade_ui/cli.py         Console-script wrapper: set local mode then exec streamlit
scripts/                One-click launchers (install-macos-app.sh, launch-local-webapp.sh/bat)
tools/baoyu-markdown-to-html/  Vendored Bun/TS markdown→HTML converter (Quant Terminal theme)
tests/                  pytest suite for the pure helpers in app.py and trade_ui/cli.py
```

### Data flow on Run Analysis

1. `main()` (`app.py:1511`) renders the sidebar, then renders two tabs: **Run Analysis** and **Browse Reports**.
2. The user fills ticker, date, language, analysts, depth, LLM provider, two model IDs, and (per-provider) API key. Credentials are kept in `st.session_state` and persisted to `~/.tradingagents/.env` only when `TRADINGAGENTS_UI_LOCAL=1` (set by `trade_ui/cli.py` via `os.environ`).
3. Clicking **Run Analysis** spawns a daemon `threading.Thread` running `_run_analysis_thread` (`app.py:955`). The thread mutates a shared `state` dict; the main thread polls it via `st.rerun()` every ~1.5s.
4. Inside the thread:
   - `get_runtime_llm_config` maps the selected provider to a runtime provider + base URL (custom endpoints run through OpenAI/Anthropic runtime with a custom URL — see `PROVIDER_RUNTIME` in `ui_config.py`).
   - `apply_api_env_values` writes credentials into `os.environ` under `RUN_ENV_LOCK` (the lock exists because env vars are process-global).
   - A `TradingAgentsGraph` is built with the user's `quick_think_llm` / `deep_think_llm` and `max_debate_rounds` from depth.
   - `graph.graph.stream(...)` yields chunks; the thread appends messages/tool calls to `state`, updates `agent_status` per analyst/team, and saves report sections to `state["report_sections"]`.
   - On completion, sections are written to `<results_dir>/<ticker>/<date>/reports/*.md` and a `~/.tradingagents/latest_report.md` symlink is refreshed.
5. **Browse Reports** tab (`browse_reports_ui`, `app.py:1246`) walks `~/.tradingagents/logs/`, lists `complete_report*.md` files, and renders them either as embedded HTML (via the vendored baoyu converter) or raw Markdown.

### TradingAgents update check

`cached_tradingagents_update_status` (`app.py:145`) is `@st.cache_data(ttl=3600)`. It does a `git ls-remote --tags` against `TauricResearch/TradingAgents` and compares to either a local checkout (when `TRADINGAGENTS_DIR` is set) or the installed pip package version. The sidebar brand renders an `↥` button when an update is available; clicking it calls `update_tradingagents_from_app` which shells out to `git pull` + `pip install -e .` (or `pip install -U git+https://...` when no local checkout).

The CLI does not install or update TradingAgents during startup. The deprecated `--no-update` flag is accepted only so old launchers do not fail.

### Environment variables

- `TRADINGAGENTS_UI_LOCAL=1` — set by `trade_ui/cli.py`. When set, API keys are persisted to disk. Unset in Streamlit Cloud.
- `TRADINGAGENTS_UI_APP_PATH` — override which `app.py` to run (1st priority in `_resolve_app_path`).
- `TRADINGAGENTS_UI_PYTHON_VERSION` — Python version used by desktop launchers when bootstrapping `.venv` with `uv` (default: `3.11`).
- `TRADINGAGENTS_DIR` — path to a local TradingAgents checkout. If set, updates are done via `git pull` + `pip install -e .` instead of reinstalling the git URL.
- `TRADINGAGENTS_UI_PORT` / `TRADINGAGENTS_UI_HOST` — read by the macOS/Windows launcher scripts only.

### Custom conventions worth knowing

- Long Streamlit app is intentionally a single file: app.py is ~1.7k lines. Helper modules are only for things that need to be reused (config constants, CSS, panel renderers) or for things that are easier to test outside Streamlit.
- HTML report generation runs an out-of-process Bun script (`tools/baoyu-markdown-to-html/scripts/main.ts`). `ensure_baoyu_dependencies` lazily installs its `node_modules` on first use. The script returns a JSON envelope with `htmlPath`; the HTML is read back into Python and embedded via `streamlit.components.v1.html`.
- Provider model lists come from two sources, in priority order: `PROVIDER_MODEL_OPTIONS` (UI-defined overrides) then `MODEL_OPTIONS` (imported from `tradingagents.llm_clients.model_catalog`). The override exists because some TradingAgents provider setups don't ship the most current models.
- The "compatible" provider types (e.g. `ollama`, `glm_cn`, `litellm`, `custom_openai`) all run through a real OpenAI/Anthropic runtime via `PROVIDER_RUNTIME`; the user just supplies a different base URL and key.
- Tests cover only pure helpers — anything that touches `st.session_state`, `streamlit.components.v1`, or threads is not unit-tested. The `tests/` directory is gitignored from the published repo (see `.gitignore`).

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
