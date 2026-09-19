"""A run left mid-flight by a dead server must not hijack the Monitor."""
from __future__ import annotations

import json
from pathlib import Path

from trade_ui.server.config import ServerSettings
from trade_ui.server.registry import RunRegistry


def _write_run(runs_dir: Path, run_id: str, status: str) -> Path:
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_file = run_dir / "run.json"
    run_file.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": status,
                "ticker": "ZZZ",
                "trade_date": "2026-01-01",
            }
        ),
        encoding="utf-8",
    )
    return run_file


def test_running_run_from_a_dead_process_is_closed_on_startup(tmp_path: Path) -> None:
    """The real failure: the frontend prefers a running run when choosing what
    to display, so one zombie from a previous server process pinned the Monitor
    to a dead run and pressing Start appeared to do nothing."""
    runs_dir = tmp_path / "runs"
    zombie = _write_run(runs_dir, "zombie01", "running")
    pending = _write_run(runs_dir, "zombie02", "pending")
    finished = _write_run(runs_dir, "done01", "completed")

    RunRegistry(settings=ServerSettings(runs_dir=runs_dir))

    assert json.loads(zombie.read_text(encoding="utf-8"))["status"] == "failed"
    assert json.loads(pending.read_text(encoding="utf-8"))["status"] == "failed"
    # A finished run is left exactly as it was.
    assert json.loads(finished.read_text(encoding="utf-8"))["status"] == "completed"


def test_reconcile_survives_a_corrupt_run_file(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    bad = runs_dir / "broken" / "run.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not json", encoding="utf-8")

    # Must not raise: one bad file cannot stop the server from starting.
    RunRegistry(settings=ServerSettings(runs_dir=runs_dir))
    assert bad.read_text(encoding="utf-8") == "{not json"


def _write_events(runs_dir: Path, run_id: str, timestamps: list[str]) -> None:
    events = runs_dir / run_id / "events.jsonl"
    events.write_text(
        "\n".join(
            json.dumps({"seq": i + 1, "ts": ts, "run_id": run_id, "kind": "stats"})
            for i, ts in enumerate(timestamps)
        )
        + "\n",
        encoding="utf-8",
    )


def test_completed_at_comes_from_the_last_event_not_the_clock(tmp_path: Path) -> None:
    """A real run was marked failed at 10:25:12 while its own last event was at
    10:27:35, because reconcile stamped the startup time. A completion time that
    precedes the run's final event is impossible and breaks time-based views."""
    runs_dir = tmp_path / "runs"
    last_event = "2026-09-19T10:27:35.833671+00:00"
    run_file = _write_run(runs_dir, "stale01", "running")
    _write_events(runs_dir, "stale01", ["2026-09-19T10:27:05+00:00", last_event])

    RunRegistry(settings=ServerSettings(runs_dir=runs_dir))

    header = json.loads(run_file.read_text(encoding="utf-8"))
    assert header["status"] == "failed"
    assert header["completed_at"] == last_event


def test_a_run_whose_log_moved_recently_is_left_alone(tmp_path: Path) -> None:
    """Two servers sharing a runs directory: the freshly started one must not
    mark the other's live run as failed."""
    from datetime import datetime, timezone

    runs_dir = tmp_path / "runs"
    run_file = _write_run(runs_dir, "live01", "running")
    now_iso = datetime.now(timezone.utc).isoformat()
    _write_events(runs_dir, "live01", [now_iso])

    RunRegistry(settings=ServerSettings(runs_dir=runs_dir))

    assert json.loads(run_file.read_text(encoding="utf-8"))["status"] == "running"
