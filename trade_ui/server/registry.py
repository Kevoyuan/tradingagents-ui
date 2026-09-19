"""Run registry enforcing single active run, persistence to run.json, and run indexing."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from trade_ui.server.config import ServerSettings
from trade_ui.server.event_bus import EventBus
from trade_ui.server.models import RunConfig, RunHeader, utc_now_iso
from trade_ui.server.runner import CancellationToken, StubRunner, UpstreamRunner

logger = logging.getLogger(__name__)


class RunConflictError(Exception):
    """Raised when starting a run while another is active (HTTP 409)."""


class RunNotFoundError(Exception):
    """Raised when a run ID does not exist (HTTP 404)."""


class RunNotRunningError(Exception):
    """Raised when attempting to cancel a run that is not running (HTTP 409)."""


class ActiveRun:
    """Encapsulates state for the currently executing run."""

    def __init__(
        self,
        run_id: str,
        header: RunHeader,
        event_bus: EventBus,
        cancel_token: CancellationToken,
        thread: threading.Thread,
    ) -> None:
        self.run_id = run_id
        self.header = header
        self.event_bus = event_bus
        self.cancel_token = cancel_token
        self.thread = thread

    def is_active(self) -> bool:
        """Return True if run is still executing."""
        return self.header.status in ("pending", "running") and self.thread.is_alive()


class RunRegistry:
    """Registry managing run lifecycle, single active constraint, and disk index."""

    def __init__(self, settings: ServerSettings | None = None) -> None:
        self.settings = settings or ServerSettings()
        self.runs_dir = self.settings.runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.active_run: ActiveRun | None = None
        self._reconcile_orphaned_runs()

    def _reconcile_orphaned_runs(self) -> None:
        """Close out runs left mid-flight by a previous server process.

        A run only exists inside the process that started it. When the server
        restarts, any run.json still marked running or pending is a zombie: it
        will never finish and never emit another event. The frontend prefers a
        running run when choosing what to display, so a single zombie would
        hijack the Monitor permanently - which is exactly what happened, the
        UI sat on a dead run from a previous process while the user pressed
        Start and nothing moved.

        Two limits on that, both learned from a real run:

        - The completion time is taken from the run's own last event, never from
          the clock at startup. Stamping "now" produced runs whose completed_at
          preceded their own final event by minutes, which is impossible and
          breaks anything that orders or measures runs by time.
        - A run whose log moved in the last minute is left alone. Its owning
          process is probably still alive (two servers sharing a runs
          directory); marking it failed would clobber a healthy run.
        """
        if not self.runs_dir.is_dir():
            return
        now = time.time()
        for child in self.runs_dir.iterdir():
            run_file = child / "run.json"
            if not run_file.is_file():
                continue
            try:
                header = RunHeader.model_validate_json(run_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            if header.status not in ("running", "pending"):
                continue

            last_ts = self._last_event_timestamp(child / "events.jsonl")
            if last_ts is not None:
                try:
                    if now - datetime.fromisoformat(last_ts).timestamp() < 60:
                        continue
                except ValueError:
                    pass

            header.status = "failed"
            header.completed_at = last_ts or header.completed_at
            # Persist inline rather than via _save_header, which takes the lock
            # and is not yet safe to use from __init__.
            try:
                run_file.write_text(header.model_dump_json(indent=2), encoding="utf-8")
            except OSError:
                continue

    @staticmethod
    def _last_event_timestamp(events_file: Path) -> str | None:
        """Read the final event's timestamp without loading the whole log."""
        if not events_file.is_file():
            return None
        try:
            with open(events_file, "rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(0, size - 8192))
                tail = handle.read().decode("utf-8", "replace").strip().splitlines()
        except OSError:
            return None
        for line in reversed(tail):
            try:
                value = json.loads(line).get("ts")
            except (json.JSONDecodeError, AttributeError):
                continue
            if isinstance(value, str) and value:
                return value
        return None

    def has_active_run(self) -> bool:
        """Check whether a run is currently in progress."""
        with self._lock:
            if self.active_run is not None:
                if self.active_run.is_active():
                    return True
                # Clean up inactive run reference
                self.active_run = None
            return False

    def get_active_run_id(self) -> str | None:
        """Return active run_id if one is running."""
        with self._lock:
            if self.active_run is not None and self.active_run.is_active():
                return self.active_run.run_id
            return None

    def _save_header(self, header: RunHeader) -> None:
        """Persist run.json to disk."""
        run_dir = self.runs_dir / header.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        run_file = run_dir / "run.json"
        temp_file = run_dir / "run.json.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(header.model_dump_json(indent=2))
        temp_file.replace(run_file)

    def start_run(self, config: RunConfig) -> RunHeader:
        """Start a new run, enforcing single active run constraint."""
        with self._lock:
            if self.active_run is not None:
                if self.active_run.is_active():
                    raise RunConflictError(f"A run is already active: {self.active_run.run_id}")
                self.active_run = None

            run_id = uuid.uuid4().hex[:8]
            run_dir = self.runs_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)

            trade_date = config.trade_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

            header = RunHeader(
                run_id=run_id,
                status="pending",
                ticker=config.ticker,
                trade_date=trade_date,
                created_at=utc_now_iso(),
                config=config.model_dump(),
            )
            self._save_header(header)

            event_bus = EventBus(run_dir=run_dir, run_id=run_id)
            cancel_token = CancellationToken()

            def on_header_update(updated_header: RunHeader) -> None:
                self._save_header(updated_header)

            use_stub = config.use_stub or self.settings.use_stub
            if use_stub:
                runner = StubRunner(
                    header=header,
                    config=config,
                    event_bus=event_bus,
                    cancel_token=cancel_token,
                    on_header_update=on_header_update,
                )
            else:
                runner = UpstreamRunner(
                    header=header,
                    config=config,
                    event_bus=event_bus,
                    cancel_token=cancel_token,
                    on_header_update=on_header_update,
                )

            thread = threading.Thread(target=runner.run, name=f"run-{run_id}", daemon=True)
            active = ActiveRun(
                run_id=run_id,
                header=header,
                event_bus=event_bus,
                cancel_token=cancel_token,
                thread=thread,
            )
            self.active_run = active
            thread.start()

            return header

    def get_run(self, run_id: str) -> RunHeader | None:
        """Retrieve run header from memory if active or from disk."""
        with self._lock:
            if self.active_run is not None and self.active_run.run_id == run_id:
                return self.active_run.header

        run_file = self.runs_dir / run_id / "run.json"
        if not run_file.is_file():
            return None

        try:
            with open(run_file, encoding="utf-8") as f:
                data = json.load(f)
            return RunHeader.model_validate(data)
        except Exception as err:
            logger.warning("Failed to parse %s: %s", run_file, err)
            return None

    def list_runs(self) -> list[RunHeader]:
        """Return history index of all runs from runs directory, newest first."""
        results: list[RunHeader] = []
        if not self.runs_dir.is_dir():
            return results

        for child in self.runs_dir.iterdir():
            if not child.is_dir():
                continue
            run_id = child.name
            with self._lock:
                if self.active_run is not None and self.active_run.run_id == run_id:
                    results.append(self.active_run.header)
                    continue
            run_file = child / "run.json"
            if run_file.is_file():
                try:
                    with open(run_file, encoding="utf-8") as f:
                        data = json.load(f)
                    results.append(RunHeader.model_validate(data))
                except Exception:
                    continue

        results.sort(key=lambda r: r.created_at, reverse=True)
        return results

    def cancel_run(self, run_id: str) -> bool:
        """Cooperatively cancel a running run. Returns True if cancelled, raises otherwise."""
        with self._lock:
            if self.active_run is not None and self.active_run.run_id == run_id:
                if self.active_run.is_active():
                    self.active_run.cancel_token.cancel()
                    return True
                raise RunNotRunningError("Run is not running")

        run = self.get_run(run_id)
        if run is None:
            raise RunNotFoundError(f"Run {run_id} not found")
        raise RunNotRunningError(f"Run {run_id} is not running (status: {run.status})")

    def get_event_bus(self, run_id: str) -> EventBus | None:
        """Get the EventBus for a run (either active or file-backed)."""
        with self._lock:
            if self.active_run is not None and self.active_run.run_id == run_id:
                return self.active_run.event_bus

        run_dir = self.runs_dir / run_id
        if run_dir.is_dir():
            return EventBus(run_dir=run_dir, run_id=run_id)
        return None
