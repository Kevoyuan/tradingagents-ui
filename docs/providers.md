# Providers

TradingAgents v0.3.1 native providers are shown directly in the UI. Their model lists and API key names are imported from the upstream package where available.

Native Kimi uses the `kimi` ID and Moonshot's OpenAI-compatible API. The older Kimi Coding Plan remains available as `kimi_coding` and runs through the Anthropic-compatible adapter.

Generic OpenAI-compatible endpoints use the native `openai_compatible` runtime. Configure a Base URL and custom model ID. `OPENAI_COMPATIBLE_API_KEY` is optional, so keyless LM Studio, vLLM and llama.cpp servers remain supported.

Legacy `custom_openai` preferences migrate automatically to `openai_compatible`. Preferences created by older UI releases with `kimi` migrate once to `kimi_coding` so an existing Coding Plan is not silently switched to Moonshot's protocol.

## Credentials

Provider API keys are entered in the sidebar. Local mode stores them in `~/.tradingagents/.env`; cloud and direct Streamlit sessions keep them in memory unless platform secrets are configured.

Amazon Bedrock supports `AWS_BEARER_TOKEN_BEDROCK` or the normal AWS credential chain, plus `AWS_DEFAULT_REGION` and optional `AWS_PROFILE`. Install the Bedrock extra first.

## Data sources

Data source selections are exact vendor chains. Selecting `yfinance,alpha_vantage` explicitly enables that ordered chain; the UI does not add an unselected fallback. FRED requires `FRED_API_KEY`; Polymarket is keyless.
