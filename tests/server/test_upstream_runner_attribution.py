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
    """Fake streaming adapter shaped like the real one.

    Upstream runs with stream_mode="values", so every chunk is the full
    AgentState dict. An earlier version of this fake emitted node-keyed chunks,
    which is a shape the real stream never produces - the tests stayed green
    while the shipped code matched nothing.
    """

    def __init__(self, *_a, **_k) -> None:
        pass

    def stream(self, *_a, **_k):
        yield {"messages": [SimpleNamespace(content="SNDK")], "market_report": ""}
        yield {"messages": [SimpleNamespace(content="SNDK")], "market_report": ""}  # duplicate
        yield {"messages": [SimpleNamespace(content="price data")], "market_report": "full report"}
        yield {
            "messages": [SimpleNamespace(content="bull case")],
            "investment_debate_state": {"latest_speaker": "Bull"},
        }
        yield {"messages": [SimpleNamespace(content="no signal")], "sentiment_report": "sentiment"}
        yield {
            "messages": [SimpleNamespace(content="Rating: Buy")],
            "final_trade_decision": "Rating: Buy",
        }


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
            StatsCallbackHandler=lambda: SimpleNamespace(
                get_stats=lambda: {
                    "llm_calls": 3,
                    "tool_calls": 2,
                    "tokens_in": 1500,
                    "tokens_out": 800,
                }
            )
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
    assert "bull_researcher" in slugs
    assert all(e["payload"]["status"] in ("running", "done") for e in statuses)
    assert all(e["agent"] == e["payload"]["agent"] for e in statuses)

    messages = [e for e in bus.events if e["kind"] == "agent_message"]
    assert all(e["agent"] is not None for e in messages), "no message may be unattributed"
    assert {e["agent"] for e in messages} == {
        "market",
        "bull_researcher",
        "social",
        "portfolio_manager",
    }
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


def test_debate_speaker_attribution_follows_latest_speaker(
    monkeypatch, tmp_path: Path
) -> None:
    """During a debate there is no report field to key on; the debate state names
    who is speaking, and that is what attributes the message."""
    bus = _run_upstream(monkeypatch, tmp_path)
    bull_msg = [
        e for e in bus.events
        if e["kind"] == "agent_message" and e["payload"]["text"] == "bull case"
    ]
    assert len(bull_msg) == 1
    assert bull_msg[0]["agent"] == "bull_researcher"
    assert bull_msg[0]["team"] == "research"


def test_upstream_run_publishes_stats(monkeypatch, tmp_path: Path) -> None:
    """The upstream path published no stats at all, so LLM calls, tool calls,
    tokens and the burn chart stayed at zero for an entire real run."""
    bus = _run_upstream(monkeypatch, tmp_path)
    stats = [e for e in bus.events if e["kind"] == "stats"]
    assert stats, "upstream run must publish stats events"
    assert stats[-1]["payload"]["llm_calls"] == 3
    assert stats[-1]["payload"]["tool_calls"] == 2
    assert stats[-1]["payload"]["tokens_in"] == 1500
    assert stats[-1]["payload"]["tokens_out"] == 800


def test_upstream_run_publishes_report_sections(monkeypatch, tmp_path: Path) -> None:
    """The reducer counts report_section events for the Reports n/7 figure. The
    upstream runner published none, so it read 0/7 for the whole run."""
    bus = _run_upstream(monkeypatch, tmp_path)
    sections = [e for e in bus.events if e["kind"] == "report_section"]
    assert sections, "upstream run must publish report_section events"
    assert all(e["payload"].get("complete") is True for e in sections)
    keys = {e["payload"]["key"] for e in sections}
    assert "market_report" in keys
    assert "final_trade_decision" in keys
    assert all(e["agent"] for e in sections)
