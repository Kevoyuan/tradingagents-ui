"""Tests for cooperative cancellation of runs."""

from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient


def test_cooperative_cancel_running_run(client: TestClient) -> None:
    # Start run with delay
    res = client.post(
        "/api/runs",
        json={"ticker": "NFLX", "trade_date": "2026-05-15", "use_stub": True, "step_delay": 0.2},
    )
    assert res.status_code == 201
    run_id = res.json()["run_id"]

    time.sleep(0.05)

    # Cancel the running run
    cancel_res = client.post(f"/api/runs/{run_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelling"

    # Wait for run to finish cancelling
    for _ in range(50):
        time.sleep(0.05)
        run_data = client.get(f"/api/runs/{run_id}").json()
        if run_data["status"] in ("completed", "cancelled", "failed"):
            break

    assert run_data["status"] == "cancelled"
    assert run_data["completed_at"] is not None

    # Verify event log contains cancelled run_state
    event_res = client.get(f"/api/runs/{run_id}/events?after=0")
    assert event_res.status_code == 200
    lines = [line for line in event_res.text.split("\n") if line.startswith("data: ")]
    events = [json.loads(line[6:]) for line in lines]
    assert any(
        e["kind"] == "run_state" and e["payload"].get("status") == "cancelled"
        for e in events
    )


def test_cancel_already_finished_run_returns_409(client: TestClient) -> None:
    # Run to completion
    res = client.post(
        "/api/runs",
        json={"ticker": "INTC", "trade_date": "2026-05-16", "use_stub": True, "step_delay": 0.0},
    )
    assert res.status_code == 201
    run_id = res.json()["run_id"]

    for _ in range(50):
        time.sleep(0.02)
        run_data = client.get(f"/api/runs/{run_id}").json()
        if run_data["status"] in ("completed", "cancelled", "failed"):
            break

    # Now attempt to cancel
    cancel_res = client.post(f"/api/runs/{run_id}/cancel")
    assert cancel_res.status_code == 409
    assert "not running" in cancel_res.json()["detail"]


def test_cancel_nonexistent_run_returns_404(client: TestClient) -> None:
    res = client.post("/api/runs/nonexistent_id/cancel")
    assert res.status_code == 404
