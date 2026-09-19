from __future__ import annotations

from types import SimpleNamespace

import pytest

from provider_migrations import migrate_provider_preferences
from tradingagents_adapter import TradingAgentsAdapter, detect_asset_type
from tradingagents_compat import tradingagents_compatibility
from ui_config import PROVIDER_API_KEY_ENV, PROVIDERS


def test_native_provider_ids_align_with_upstream():
    expected = {
        "openai", "anthropic", "google", "azure", "bedrock", "xai", "deepseek",
        "qwen", "qwen-cn", "glm", "glm-cn", "minimax", "minimax-cn", "openrouter",
        "mistral", "kimi", "groq", "nvidia", "ollama", "openai_compatible",
    }
    visible = {provider_id for _, provider_id in PROVIDERS}
    assert expected <= visible
    assert expected <= set(PROVIDER_API_KEY_ENV)


def test_upstream_claude_5_models_are_visible():
    from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS

    models = {model for options in MODEL_OPTIONS["anthropic"].values() for _, model in options}
    # Assert the catalog is usable rather than pinning exact ids: upstream
    # renames models between releases (claude-fable-5 became claude-fable-5-1
    # and the two opus-4 ids collapsed into claude-opus-5 between v0.3.1 and
    # v0.5.0), and an exact list turns every rename into a false failure.
    assert models, "anthropic model catalog is empty"
    assert "claude-sonnet-5" in models


def test_kimi_and_custom_openai_preferences_migrate_once():
    migrated, notes = migrate_provider_preferences(
        {
            "llm_provider": "kimi",
            "provider_model_profiles": {"kimi": {"quick": "sonnet"}},
        }
    )
    assert migrated["llm_provider"] == "kimi_coding"
    assert migrated["provider_model_profiles"]["kimi_coding"]["quick"] == "sonnet"
    assert notes
    again, second_notes = migrate_provider_preferences({**migrated, "llm_provider": "kimi"})
    assert again["llm_provider"] == "kimi"
    assert second_notes == []


@pytest.mark.parametrize("ticker", ["BTC-USD", "ETH-USD", "SOL/USDT"])
def test_crypto_ticker_detection(ticker):
    assert detect_asset_type(ticker) == "crypto"


def test_stock_ticker_not_misclassified():
    assert detect_asset_type("NVDA") == "stock"


def test_checkpoint_thread_id_includes_graph_shape():
    from tradingagents.graph.checkpointer import thread_id

    base = thread_id("BTC-USD", "2026-07-12", "analysts=market|debate=1|risk=1|asset=crypto")
    assert base != thread_id("BTC-USD", "2026-07-12", "analysts=news|debate=1|risk=1|asset=crypto")
    assert base != thread_id("BTC-USD", "2026-07-12", "analysts=market|debate=3|risk=3|asset=crypto")
    assert base != thread_id("BTC-USD", "2026-07-12", "analysts=market|debate=1|risk=1|asset=stock")


def test_incompatible_version_returns_ui_safe_status():
    # Bounds are owned by tradingagents_compat; this test pins the boundary
    # behaviour, not a literal version, so a bump moves the constants and these
    # two lines together. A stale hardcoded version here is exactly how the
    # v0.3.1 -> v0.5.0 bump first surfaced as a red test.
    assert not tradingagents_compatibility("0.4.0").compatible
    assert "too old" in tradingagents_compatibility("0.4.0").message
    assert not tradingagents_compatibility("0.6.0").compatible
    assert "not supported yet" in tradingagents_compatibility("0.6.0").message
    assert tradingagents_compatibility("0.5.0").compatible
    assert tradingagents_compatibility("0.5.9").compatible


def test_checkpoint_enabled_uses_compiled_checkpoint_graph(monkeypatch):
    import tradingagents.graph.checkpointer as checkpoint_module

    events = []

    class Context:
        def __enter__(self):
            events.append("checkpoint-enter")
            return "saver"

        def __exit__(self, *_args):
            events.append("checkpoint-exit")

    monkeypatch.setattr(checkpoint_module, "get_checkpointer", lambda *_args: Context())
    monkeypatch.setattr(checkpoint_module, "clear_checkpoint", lambda *_args: events.append("checkpoint-clear"))
    monkeypatch.setattr(checkpoint_module, "thread_id", lambda *_args: "shape-aware-thread")

    stream_graph = SimpleNamespace(
        stream=lambda initial, **args: iter([
            {**initial, "final_trade_decision": "HOLD", "messages": []},
        ])
    )
    workflow = SimpleNamespace(
        compile=lambda checkpointer=None: events.append(("compile", checkpointer)) or stream_graph
    )
    propagator = SimpleNamespace(
        create_initial_state=lambda ticker, date, **kwargs: {
            "company_of_interest": ticker,
            "trade_date": date,
            **kwargs,
        },
        get_graph_args=lambda callbacks=None: {"config": {}, "stream_mode": "values"},
    )
    memory = SimpleNamespace(
        get_past_context=lambda _ticker: "memory",
        store_decision=lambda **_kwargs: events.append("memory-store"),
    )
    graph = SimpleNamespace(
        config={"checkpoint_enabled": True, "data_cache_dir": "/tmp"},
        workflow=workflow,
        graph=stream_graph,
        propagator=propagator,
        memory_log=memory,
        _resolve_pending_entries=lambda _ticker: events.append("memory-resolve"),
        resolve_instrument_context=lambda _ticker, asset: f"instrument:{asset}",
        _run_signature=lambda asset: f"shape:{asset}",
        _log_state=lambda *_args: events.append("log-state"),
        curr_state=None,
        ticker=None,
    )

    chunks = list(TradingAgentsAdapter(graph).stream("BTC-USD", "2026-07-12"))
    assert chunks[-1]["asset_type"] == "crypto"
    assert ("compile", "saver") in events
    assert "checkpoint-clear" in events
    assert "checkpoint-exit" in events
