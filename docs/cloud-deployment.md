# Cloud Deployment

Deploy `app.py` as the Streamlit entrypoint and install from `pyproject.toml`. TradingAgents is pinned to v0.3.1.

Cloud mode does not write API keys to `~/.tradingagents/.env`. Entered keys remain session-only. For persistent deployment credentials, use the hosting platform's encrypted secrets and expose the standard provider environment variables.

The local report directory is ephemeral on many cloud platforms. Attach persistent storage if report history must survive restarts.

HTML report generation requires Bun or an `npx`-capable Node.js installation.
