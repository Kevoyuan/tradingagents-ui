"""The upstream path must attribute messages to agents and emit agent_status.

Regression guard for the bug where UpstreamRunner flattened each chunk into one
message list, discarding the chunk key that identifies the agent node. Every
event went out as agent=None, so the UI rendered "System" for everything and the
roster, stage rail and agent counters never left zero on a real run. The stub
runner did both correctly, which is why the whole Playwright suite passed while
real runs were unusable.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from trade_ui.server.models import RunConfig, RunHeader
from trade_ui.server.runner import UpstreamRunner


class _Bus:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def publish(self, kind: str, payload: dict, agent=None, team=None):  # noqa: ANN001
        self.events.append({"kind": kind, "payload": payload, "agent": agent, "team": team})

    def close(self) -> None:
        pass


class _Token:
    is_cancelled = False


class _Adapter:
    """Fake streaming adapter: chunks keyed by upstream node name."""

    def __init__(self, *_a, **_k) -> None:
        pass

    def stream(self, *_a, **_k):
        yield {"Market Analyst": {"messages": [SimpleNamespace(content="SNDK")]}}
        yield {"Market Analyst": {"messages": [SimpleNamespace(content="SNDK")]}}  # duplicate
        yield {"tools_market": {"messages": [SimpleNamespace(content="price data")]}}
        yield {"Sentiment Analyst": {"messages": [SimpleNamespace(content="no signal")]}}
        yield {"Portfolio Manager": {"messages": [SimpleNamespace(content="Rating: Buy")]}}


def _run_upstream(monkeypatch, tmp_path: Path) -> _Bus:
    import sys

    import trade_ui.server.runner as runner_mod

    bus = _Bus()
    header = RunHeader(run_id="r1", status="running", ticker="SNDK", trade_date="2026-09-19")

    # Bypass credential/config resolution; the subject under test is attribution.
    monkeypatch.setattr(
        runner_mod,
        "resolve_run_config",
        lambda *_a, **_k: SimpleNamespace(
            upstream_config={}, env_values={}, provider="deepseek", missing_credentials=[]
        ),
        raising=False,
    )
    # run() imports the adapter locally, so patch it on its own module.
    import tradingagents_adapter as adapter_mod

    monkeypatch.setattr(adapter_mod, "TradingAgentsAdapter", _Adapter, raising=True)
    monkeypatch.setattr(
        runner_mod, "temporary_environment", lambda *_a, **_k: SimpleNamespace(
            __enter__=lambda s: None, __exit__=lambda s, *a: None
        ), raising=False,
    )
    monkeypatch.setitem(
        sys.modules,
        "tradingagents.graph.trading_graph",
        SimpleNamespace(TradingAgentsGraph=lambda *_a, **_k: SimpleNamespace()),
    )
    monkeypatch.setitem(
        sys.modules,
        "cli.stats_handler",
        SimpleNamespace(
            StatsCallbackHandler=lambda: SimpleNamespace(get_stats=lambda: {})
        ),
    )

    runner = UpstreamRunner(
        header=header,
        config=RunConfig(ticker="SNDK", trade_date="2026-09-19"),
        event_bus=bus,
        cancel_token=_Token(),
        on_header_update=lambda _h: None,
    )
    runner.run()
    return bus


def test_upstream_messages_carry_agent_and_status(monkeypatch, tmp_path: Path) -> None:
    bus = _run_upstream(monkeypatch, tmp_path)

    statuses = [e for e in bus.events if e["kind"] == "agent_status"]
    assert statuses, "upstream run must publish agent_status events"
    slugs = {e["payload"]["agent"] for e in statuses}
    # Upstream calls it "Sentiment Analyst"; the UI roster slug is "social".
    assert "social" in slugs
    assert "market" in slugs
    assert "portfolio_manager" in slugs
    assert all(e["payload"]["status"] in ("running", "done") for e in statuses)
    assert all(e["agent"] == e["payload"]["agent"] for e in statuses)

    messages = [e for e in bus.events if e["kind"] == "agent_message"]
    assert all(e["agent"] is not None for e in messages), "no message may be unattributed"
    assert {e["agent"] for e in messages} == {"market", "social", "portfolio_manager"}
    assert all(e["team"] is not None for e in messages)


def test_repeated_message_content_is_not_published_twice(monkeypatch, tmp_path: Path) -> None:
    bus = _run_upstream(monkeypatch, tmp_path)
    market_texts = [
        e["payload"]["text"] for e in bus.events
        if e["kind"] == "agent_message" and e["agent"] == "market"
    ]
    # The graph re-emits the same message on consecutive ticks. The tool-node
    # message below it is legitimately a separate line for the same agent.
    assert market_texts.count("SNDK") == 1, f"duplicate content leaked through: {market_texts}"
    assert "price data" in market_texts


def test_tool_node_message_attributes_to_the_agent_that_spoke_last(
    monkeypatch, tmp_path: Path
) -> None:
    bus = _run_upstream(monkeypatch, tmp_path)
    tool_msg = [
        e for e in bus.events
        if e["kind"] == "agent_message" and e["payload"]["text"] == "price data"
    ]
    assert len(tool_msg) == 1
    assert tool_msg[0]["agent"] == "market"
