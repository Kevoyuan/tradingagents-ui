"""Streaming adapter that preserves TradingAgents v0.3.1 run semantics."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

_CRYPTO_BASES = {
    "BTC", "ETH", "USDT", "USDC", "BNB", "SOL", "XRP", "DOGE", "ADA",
    "AVAX", "DOT", "LINK", "LTC", "BCH", "TRX", "TON", "SHIB", "XLM",
}


def detect_asset_type(ticker: str) -> str:
    """Classify common Yahoo-style crypto pairs without network access."""
    try:
        from tradingagents.dataflows.symbol_utils import crypto_base

        if crypto_base(ticker):
            return "crypto"
    except (ImportError, ModuleNotFoundError):
        pass
    normalized = ticker.upper().strip().replace("/", "-").replace("_", "-")
    match = re.fullmatch(r"([A-Z0-9]+)-(USD|USDT|USDC)", normalized)
    return "crypto" if match and match.group(1) in _CRYPTO_BASES else "stock"


class TradingAgentsAdapter:
    """Expose upstream-equivalent initialization as a streaming iterator.

    TradingAgents v0.3.1 has no public callback-based streaming runner. This
    adapter deliberately mirrors its private ``_run_graph`` lifecycle in one
    isolated module so the Streamlit UI can retain live progress.
    """

    def __init__(self, graph: Any, callbacks: list[Any] | None = None):
        self.graph = graph
        self.callbacks = callbacks or []

    def run_signature(self, asset_type: str) -> str:
        return self.graph._run_signature(asset_type)

    def stream(self, ticker: str, trade_date: str, asset_type: str | None = None) -> Iterator[dict[str, Any]]:
        from tradingagents.graph.checkpointer import clear_checkpoint, get_checkpointer, thread_id

        asset_type = asset_type or detect_asset_type(ticker)
        graph = self.graph
        graph.ticker = ticker
        graph._resolve_pending_entries(ticker)
        checkpoint_ctx = None
        completed = False
        final_state: dict[str, Any] = {}

        if graph.config.get("checkpoint_enabled"):
            checkpoint_ctx = get_checkpointer(graph.config["data_cache_dir"], ticker)
            saver = checkpoint_ctx.__enter__()
            graph.graph = graph.workflow.compile(checkpointer=saver)

        try:
            past_context = graph.memory_log.get_past_context(ticker)
            instrument_context = graph.resolve_instrument_context(ticker, asset_type)
            initial_state = graph.propagator.create_initial_state(
                ticker,
                str(trade_date),
                asset_type=asset_type,
                past_context=past_context,
                instrument_context=instrument_context,
            )
            args = graph.propagator.get_graph_args(callbacks=self.callbacks)
            signature = self.run_signature(asset_type)
            if graph.config.get("checkpoint_enabled"):
                args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = thread_id(
                    ticker, str(trade_date), signature
                )

            for chunk in graph.graph.stream(initial_state, **args):
                final_state.update(chunk)
                yield chunk

            graph.curr_state = final_state
            graph._log_state(str(trade_date), final_state)
            graph.memory_log.store_decision(
                ticker=ticker,
                trade_date=str(trade_date),
                final_trade_decision=final_state["final_trade_decision"],
            )
            if graph.config.get("checkpoint_enabled"):
                clear_checkpoint(graph.config["data_cache_dir"], ticker, str(trade_date), signature)
            completed = True
        finally:
            if checkpoint_ctx is not None:
                checkpoint_ctx.__exit__(None, None, None)
                graph.graph = graph.workflow.compile()
            if not completed:
                graph.curr_state = final_state or None
