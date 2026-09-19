# Installation

## Recommended local setup

Install Python 3.10+ and uv, clone the repository, then run:

```bash
uv venv --python 3.11
uv pip install -e .
```

On macOS, create and open the launcher:

```bash
./scripts/install-macos-app.sh
open "TradingAgents UI.app"
```

On Windows, double-click `scripts\launch-local-webapp.bat`.

## Terminal launch

```bash
./run.sh
```

The installed command also accepts a custom port:

```bash
trade-ui --port 9000
```

## Bedrock extra

```bash
uv pip install -e ".[bedrock]"
```
