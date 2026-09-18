"""Tests for SSE endpoint: exact replay with after=<seq>, no gaps, no duplicates, live follow."""

from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient
from httpx_sse import connect_sse


def test_sse_replay_after_mid_seq(client: TestClient) -> None:
    # 1. Run a stub run to completion
    res = client.post(
        "/api/runs",
        json={"ticker": "TSLA", "trade_date": "2026-05-10", "use_stub": True, "step_delay": 0.0},
    )
    assert res.status_code == 201
    run_id = res.json()["run_id"]

    # Wait for completion
    for _ in range(50):
        time.sleep(0.02)
        run_info = client.get(f"/api/runs/{run_id}").json()
        if run_info["status"] in ("completed", "cancelled", "failed"):
            break

    # 2. Read all events with after=0 to discover total count
    all_events: list[dict] = []
    with connect_sse(client, "GET", f"/api/runs/{run_id}/events?after=0") as event_source:
        for sse in event_source.iter_sse():
            all_events.append(json.loads(sse.data))

    total = len(all_events)
    assert total >= 8, f"Expected at least 8 events, got {total}"
    seqs = [e["seq"] for e in all_events]
    assert seqs == list(range(1, total + 1)), "Full replay must have all sequence numbers from 1 to total"

    # 3. Choose mid_seq
    mid_seq = total // 2
    expected_tail_seqs = list(range(mid_seq + 1, total + 1))

    # 4. SSE request with after=mid_seq
    tail_events: list[dict] = []
    with connect_sse(client, "GET", f"/api/runs/{run_id}/events?after={mid_seq}") as event_source:
        for sse in event_source.iter_sse():
            data = json.loads(sse.data)
            tail_events.append(data)
            assert int(sse.id) == data["seq"]

    tail_seqs = [e["seq"] for e in tail_events]

    # Assert exact tail: no gaps and no duplicates!
    assert tail_seqs == expected_tail_seqs, f"Expected {expected_tail_seqs}, got {tail_seqs}"
    assert len(tail_seqs) == len(set(tail_seqs)), "No duplicates allowed in SSE replay"


def test_sse_live_streaming(client: TestClient) -> None:
    # Start run with moderate step delay so it's active while streaming
    res = client.post(
        "/api/runs",
        json={"ticker": "AMD", "trade_date": "2026-05-11", "use_stub": True, "step_delay": 0.05},
    )
    assert res.status_code == 201
    run_id = res.json()["run_id"]

    events: list[dict] = []
    with connect_sse(client, "GET", f"/api/runs/{run_id}/events?after=0") as event_source:
        for sse in event_source.iter_sse():
            data = json.loads(sse.data)
            events.append(data)

    assert len(events) > 0
    seqs = [e["seq"] for e in events]
    # Check strictly monotonic increasing without gaps
    assert seqs == list(range(1, len(events) + 1))
    # Final event must be terminal completed
    assert events[-1]["kind"] == "run_state"
    assert events[-1]["payload"]["status"] == "completed"
