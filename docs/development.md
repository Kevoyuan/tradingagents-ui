# Development

## Commands

```bash
uv pip install -e .
bash scripts/build-frontend.sh
pytest tests/
pytest tradingagents_contract/
ruff check .
mypy app.py ui_config.py ui_panels.py ui_styles.py trade_ui/
```

Run locally with `./run.sh` or `trade-ui --port 9000` (or `trade-ui --legacy` for Streamlit).

## Architecture

- `app.py`: Streamlit composition, live progress and report browser
- `tradingagents_adapter.py`: v0.3.1 streaming/checkpoint lifecycle adapter
- `tradingagents_compat.py`: supported version range and exact tag install helpers
- `provider_migrations.py`: backward-compatible Provider preference migrations
- `ui_config.py`: native and UI-only Provider metadata
- `ui_advanced.py`: advanced runtime and data source settings
- `preferences.py`: local JSON preferences
- `ui_panels.py` and `ui_styles.py`: presentation helpers

## Environment variables

- `TRADINGAGENTS_UI_LOCAL=1`: enable local API key persistence
- `TRADINGAGENTS_UI_APP_PATH`: override the Streamlit entrypoint
- `TRADINGAGENTS_UI_PYTHON_VERSION`: launcher bootstrap Python version
- `TRADINGAGENTS_DIR`: use a local upstream checkout
- `TRADINGAGENTS_UI_PORT` and `TRADINGAGENTS_UI_HOST`: launcher network settings

The streaming adapter mirrors the upstream v0.3.1 `_run_graph` initialization and cleanup because upstream does not expose a public streaming equivalent of `propagate()`. Keep version-specific private API use isolated in that module.
