# Providers

TradingAgents v0.3.1 native providers are shown directly in the UI. Their model lists and API key names are imported from the upstream package where available.

Native Kimi uses the `kimi` ID and Moonshot's OpenAI-compatible API. The older Kimi Coding Plan remains available as `kimi_coding` and runs through the Anthropic-compatible adapter.

Generic OpenAI-compatible endpoints use the native `openai_compatible` runtime. Configure a Base URL and custom model ID. `OPENAI_COMPATIBLE_API_KEY` is optional, so keyless LM Studio, vLLM and llama.cpp servers remain supported.

Legacy `custom_openai` preferences migrate automatically to `openai_compatible`. Preferences created by older UI releases with `kimi` migrate once to `kimi_coding` so an existing Coding Plan is not silently switched to Moonshot's protocol.

## Credentials

Provider API keys are entered in the Settings drawer (the gear in the left rail). They are stored in `~/.tradingagents/.env` with mode 600 and passed to the selected provider only for the duration of a run. The API never returns a stored key; the settings UI shows a masked hint instead.

Amazon Bedrock supports `AWS_BEARER_TOKEN_BEDROCK` or the normal AWS credential chain, plus `AWS_DEFAULT_REGION` and optional `AWS_PROFILE`. Install the Bedrock extra first.

## Data sources

Data source selections are exact vendor chains. Selecting `yfinance,alpha_vantage` explicitly enables that ordered chain; the UI does not add an unselected fallback. FRED requires `FRED_API_KEY`; Polymarket is keyless.
