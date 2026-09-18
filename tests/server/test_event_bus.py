"""Tests for EventBus sequence, event schema contract, and tool result disk persistence."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from trade_ui.server.event_bus import EventBus


def test_event_sequence_monotonic(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_test_seq"
    bus = EventBus(run_dir=run_dir, run_id="seq_run")

    ev1 = bus.publish(kind="user_message", payload={"text": "hello 1"})
    ev2 = bus.publish(kind="agent_status", agent="market", team="analyst", payload={"status": "running"})
    ev3 = bus.publish(kind="stats", payload={"llm_calls": 1})

    assert ev1.seq == 1
    assert ev2.seq == 2
    assert ev3.seq == 3

    # Check persistence on disk
    events_file = run_dir / "events.jsonl"
    assert events_file.is_file()
    lines = events_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3

    parsed = [json.loads(line) for line in lines]
    assert [p["seq"] for p in parsed] == [1, 2, 3]
    for p in parsed:
        assert "ts" in p
        assert "kind" in p
        assert "run_id" in p
        assert "payload" in p


def test_tool_result_truncation_and_retrieval(client: TestClient, runs_dir: Path) -> None:
    run_dir = runs_dir / "test_tool_run"
    bus = EventBus(run_dir=run_dir, run_id="test_tool_run")

    # Short result
    bus.publish_tool_result(
        tool="short_tool",
        call_id="call_short",
        ok=True,
        duration_ms=15,
        result="short result content",
        agent="market",
        team="analyst",
    )

    # Long result (> 500 chars)
    large_content = "X" * 1200
    bus.publish_tool_result(
        tool="long_tool",
        call_id="call_long",
        ok=True,
        duration_ms=55,
        result=large_content,
        agent="market",
        team="analyst",
    )

    events = bus.read_events(after=0)
    assert len(events) == 2

    # Verify short tool result
    short_ev = events[0]
    assert short_ev.payload["tool"] == "short_tool"
    assert short_ev.payload["truncated"] is False
    assert short_ev.payload["full_ref"] is None
    assert short_ev.payload["result"] == "short result content"

    # Verify long tool result
    long_ev = events[1]
    assert long_ev.payload["tool"] == "long_tool"
    assert long_ev.payload["truncated"] is True
    assert long_ev.payload["full_ref"] == "/api/runs/test_tool_run/tools/call_long"
    assert len(long_ev.payload["result"]) < 600
    assert "... [truncated]" in long_ev.payload["result"]

    # Verify disk persistence for long tool result
    tool_file = run_dir / "tools" / "call_long.txt"
    assert tool_file.is_file()
    assert tool_file.read_text(encoding="utf-8") == large_content

    # Verify retrieval via API
    # Create run header first so get_tool_result finds run
    header_file = run_dir / "run.json"
    header_file.write_text(
        json.dumps({
            "run_id": "test_tool_run",
            "status": "completed",
            "ticker": "AAPL",
            "trade_date": "2026-05-01",
            "created_at": "2026-05-01T00:00:00Z",
            "config": {},
        }),
        encoding="utf-8",
    )

    res = client.get("/api/runs/test_tool_run/tools/call_long")
    assert res.status_code == 200
    assert res.text == large_content
