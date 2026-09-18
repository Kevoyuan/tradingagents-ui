"""Tests for run registry, single active run constraint, and history indexing."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def test_create_run_and_get(client: TestClient) -> None:
    res = client.post("/api/runs", json={"ticker": "AAPL", "trade_date": "2026-05-01", "use_stub": True})
    assert res.status_code == 201
    data = res.json()
    assert "run_id" in data
    assert data["ticker"] == "AAPL"
    run_id = data["run_id"]

    # Retrieve by ID
    get_res = client.get(f"/api/runs/{run_id}")
    assert get_res.status_code == 200
    run_data = get_res.json()
    assert run_data["run_id"] == run_id
    assert run_data["ticker"] == "AAPL"


def test_single_active_run_returns_409_conflict(client: TestClient) -> None:
    # Start a run with step delay to keep it running for a brief moment
    res1 = client.post(
        "/api/runs",
        json={"ticker": "NVDA", "trade_date": "2026-05-02", "use_stub": True, "step_delay": 0.02},
    )
    assert res1.status_code == 201
    run_id1 = res1.json()["run_id"]

    # Immediately try to start a second run while the first is running
    res2 = client.post(
        "/api/runs",
        json={"ticker": "MSFT", "trade_date": "2026-05-02", "use_stub": True},
    )
    assert res2.status_code == 409
    detail = res2.json()["detail"]
    assert detail["active_run_id"] == run_id1
    assert "already active" in detail["message"]

    # Wait for the first run to complete
    for _ in range(100):
        time.sleep(0.02)
        check = client.get(f"/api/runs/{run_id1}").json()
        if check["status"] in ("completed", "cancelled", "failed"):
            break

    assert check["status"] == "completed"

    # Now starting another run should succeed
    res3 = client.post(
        "/api/runs",
        json={"ticker": "MSFT", "trade_date": "2026-05-02", "use_stub": True, "step_delay": 0.0},
    )
    assert res3.status_code == 201


def test_list_runs_history(client: TestClient) -> None:
    res = client.post("/api/runs", json={"ticker": "GOOGL", "trade_date": "2026-05-03", "use_stub": True})
    assert res.status_code == 201
    run_id = res.json()["run_id"]

    # Allow run to complete
    time.sleep(0.1)

    list_res = client.get("/api/runs")
    assert list_res.status_code == 200
    runs = list_res.json()
    assert isinstance(runs, list)
    assert any(r["run_id"] == run_id for r in runs)


def test_get_nonexistent_run_returns_404(client: TestClient) -> None:
    res = client.get("/api/runs/nonexistent_12345")
    assert res.status_code == 404
