# Upstream TradingAgents Compatibility Matrix

This document tracks compatibility between `tradingagents-ui` and the upstream [TradingAgents](https://github.com/TauricResearch/TradingAgents) library.

## Verified Upstream Releases

| TradingAgents Version | Status | CI Contract Suite | Notes |
|-----------------------|--------|-------------------|-------|
| `v0.3.1` (Pinned) | Supported & Pinned | Passing | Base target version installed by default in virtual environments. |
| `v0.5.0` (Latest Tag) | Compatible | Passing | Contract verified; adds optional `portfolio_context` to initial state. |

## Symbol Contract Matrix

The following upstream symbols are required by `tradingagents-ui` and asserted by `tradingagents_contract`:

| Symbol / Interface | Expected Signature / Structure | v0.3.1 | v0.5.0 | Usage in tradingagents-ui |
|--------------------|--------------------------------|--------|--------|---------------------------|
| `tradingagents.graph.trading_graph.TradingAgentsGraph` | `__init__(selected_analysts, debug, config, callbacks)` | Pass | Pass | Core graph runner instantiation |
| `TradingAgentsGraph._run_signature` | `_run_signature(asset_type) -> str` | Pass | Pass | Checkpoint thread identification |
| `TradingAgentsGraph.graph.stream` | `.stream(initial_state, **args) -> Iterator[chunk]` | Pass | Pass | Event streaming and state iteration |
| `Propagator.create_initial_state` | `(company_name, trade_date, asset_type, past_context, instrument_context, ...)` | Pass | Pass | State initialization before graph run |
| `graph.workflow.compile` | `.compile(checkpointer=...)` | Pass | Pass | Recompiling graph with persistence checkpointer |
| `tradingagents.reporting.write_report_tree` | `(final_state, ticker, save_path)` producing `1_analysts/`, `2_research/`, `3_trading/`, `4_risk/`, `5_portfolio/`, `complete_report.md` | Pass | Pass | Per-section report persistence |
| `tradingagents.dataflows.utils.safe_ticker_component` | `safe_ticker_component(ticker: str) -> str` | Pass | Pass | Sanitizing ticker for filesystem paths |
| `tradingagents.llm_clients.model_catalog.MODEL_OPTIONS` | `dict[str, dict[str, list[tuple[str, str]]]]` | Pass | Pass | Provider and model discovery catalog |
| `tradingagents.llm_clients.api_key_env.PROVIDER_API_KEY_ENV` | `dict[str, str]` | Pass | Pass | Mapping provider identifiers to environment variables |
| `tradingagents.agents.utils.rating.RATINGS_5_TIER` | `("Buy", "Overweight", "Hold", "Underweight", "Sell")` | Pass | Pass | Canonical 5-tier recommendation vocabulary |
| `tradingagents.agents.utils.rating.parse_rating` | `parse_rating(text: str) -> str \| None` | Pass | Pass | Verdict rating extraction |
| `cli.stats_handler.StatsCallbackHandler` | Class inheriting callback handler | Pass | Pass | Token usage and tool call tracking |

## Running Contract Verification

Contract tests verify the above symbols against the installed upstream package:

```bash
unset PYTHONPATH
.venv/bin/python -m pytest tradingagents_contract -v
```

> [!IMPORTANT]
> Upstream TradingAgents installs a top-level package named `cli`. If you have a global `PYTHONPATH` set (e.g. from other CLI agent tools), it can shadow upstream's `cli` module and cause `ImportError: cannot import name 'StatsCallbackHandler' from 'cli.stats_handler'`. Always run python commands with `unset PYTHONPATH`.
