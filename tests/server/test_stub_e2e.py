"""Tests for stub runner end-to-end execution and contract compliance."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from trade_ui.server.event_bus import EventBus
from trade_ui.server.models import RunConfig, RunHeader
from trade_ui.server.runner import CancellationToken, StubRunner


def test_stub_runner_end_to_end_direct(tmp_path: Path) -> None:
    run_dir = tmp_path / "stub_direct"
    run_id = "stub_dir1"
    event_bus = EventBus(run_dir=run_dir, run_id=run_id)
    cancel_token = CancellationToken()

    header = RunHeader(
        run_id=run_id,
        status="pending",
        ticker="AAPL",
        trade_date="2026-05-20",
        config={},
    )
    config = RunConfig(ticker="AAPL", trade_date="2026-05-20", use_stub=True, step_delay=0.0)

    runner = StubRunner(
        header=header,
        config=config,
        event_bus=event_bus,
        cancel_token=cancel_token,
        on_header_update=lambda h: None,
    )

    runner.run()

    assert header.status == "completed"
    assert header.started_at is not None
    assert header.completed_at is not None
    assert header.stats is not None
    assert header.verdict is not None

    # Check verdict shape matches Section 3
    verdict = header.verdict
    assert verdict["rating"] == "Buy"
    assert verdict["source_section"] == "portfolio"
    assert verdict["price_target"] == "194.0"
    assert verdict["entry_price"] == "115.0"
    assert verdict["stop_loss"] == "110.0"
    assert verdict["position_sizing"] == "2-3%"

    # Check all events in events.jsonl
    events = event_bus.read_events(after=0)
    assert len(events) > 0
    kinds = {e.kind for e in events}
    expected_kinds = {
        "run_state",
        "user_message",
        "agent_status",
        "agent_message",
        "tool_call",
        "tool_result",
        "report_section",
        "verdict",
        "stats",
    }
    assert expected_kinds <= kinds, f"Missing kinds: {expected_kinds - kinds}"


def test_stub_run_via_api_e2e(client: TestClient) -> None:
    res = client.post(
        "/api/runs",
        json={
            "ticker": "MSFT",
            "trade_date": "2026-05-21",
            "use_stub": True,
            "step_delay": 0.0,
        },
    )
    assert res.status_code == 201
    run_id = res.json()["run_id"]

    # Poll run status until completed
    for _ in range(50):
        time.sleep(0.02)
        run_data = client.get(f"/api/runs/{run_id}").json()
        if run_data["status"] in ("completed", "cancelled", "failed"):
            break

    assert run_data["status"] == "completed"
    assert run_data["stats"] is not None
    assert run_data["verdict"]["rating"] == "Buy"

    # Check events via API
    events_res = client.get(f"/api/runs/{run_id}/events?after=0")
    assert events_res.status_code == 200
    lines = [line for line in events_res.text.split("\n") if line.startswith("data: ")]
    events = [json.loads(line[6:]) for line in lines]
    assert len(events) >= 10
    assert events[0]["kind"] == "run_state"
    assert events[-1]["kind"] == "run_state"
    assert events[-1]["payload"]["status"] == "completed"


def test_stub_runner_twelve_agents_and_stages(tmp_path: Path) -> None:
    run_dir = tmp_path / "stub_12_agents"
    run_id = "stub_12"
    event_bus = EventBus(run_dir=run_dir, run_id=run_id)
    cancel_token = CancellationToken()

    header = RunHeader(
        run_id=run_id,
        status="pending",
        ticker="AAPL",
        trade_date="2026-05-20",
        config={},
    )
    config = RunConfig(ticker="AAPL", trade_date="2026-05-20", use_stub=True, step_delay=0.0)

    runner = StubRunner(
        header=header,
        config=config,
        event_bus=event_bus,
        cancel_token=cancel_token,
        on_header_update=lambda h: None,
    )

    runner.run()

    events = event_bus.read_events(after=0)

    expected_teams = {
        "analyst": ["market", "social", "news", "fundamentals"],
        "research": ["bull_researcher", "bear_researcher", "research_manager"],
        "trading": ["trader"],
        "risk": ["aggressive_analyst", "neutral_analyst", "conservative_analyst"],
        "portfolio": ["portfolio_manager"],
    }

    status_by_agent: dict[str, str] = {}
    transitions: list[tuple[str, str]] = []
    for ev in events:
        if ev.kind == "agent_status":
            agent = ev.payload.get("agent") or ev.agent
            st = ev.payload.get("status")
            if agent and st:
                status_by_agent[agent] = st
                transitions.append((agent, st))

    # All 12 agents must transition running -> done
    for _team, slugs in expected_teams.items():
        for slug in slugs:
            assert status_by_agent.get(slug) == "done", f"Agent {slug} not marked done"
            slug_transitions = [st for (ag, st) in transitions if ag == slug]
            assert slug_transitions == ["running", "done"], f"Invalid transitions for {slug}: {slug_transitions}"

    # Verify pipeline order of agents
    expected_order = [
        "market", "social", "news", "fundamentals",
        "bull_researcher", "bear_researcher", "research_manager",
        "trader",
        "aggressive_analyst", "neutral_analyst", "conservative_analyst",
        "portfolio_manager",
    ]
    seen_running_order = [ag for (ag, st) in transitions if st == "running"]
    assert seen_running_order == expected_order

    # Required end state for completed stub run: Analysts 4/4, Research 3/3, Trading 1/1, Risk 3/3, Portfolio 1/1
    stage_counts = {
        team: (sum(1 for a in slugs if status_by_agent.get(a) == "done"), len(slugs))
        for team, slugs in expected_teams.items()
    }
    assert stage_counts["analyst"] == (4, 4), "Analysts must be 4/4"
    assert stage_counts["research"] == (3, 3), "Research must be 3/3"
    assert stage_counts["trading"] == (1, 1), "Trading must be 1/1"
    assert stage_counts["risk"] == (3, 3), "Risk must be 3/3"
    assert stage_counts["portfolio"] == (1, 1), "Portfolio must be 1/1"
    assert sum(count[0] for count in stage_counts.values()) == 12, "All 12 agents must be done"

    # Verdict event kept last among agent transitions
    verdict_events = [ev for ev in events if ev.kind == "verdict"]
    assert len(verdict_events) == 1
    last_agent_done_seq = max(
        ev.seq for ev in events if ev.kind == "agent_status" and ev.payload.get("status") == "done"
    )
    assert verdict_events[0].seq > last_agent_done_seq

