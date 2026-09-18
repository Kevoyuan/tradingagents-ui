"""EventBus managing event sequence, disk persistence, and SSE subscriber distribution."""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from trade_ui.server.models import Event, EventKind, TeamName, utc_now_iso

MAX_INLINE_TOOL_RESULT_LENGTH = 500


class EventBus:
    """Thread-safe event bus and file-backed event log for a single run."""

    def __init__(self, run_dir: Path, run_id: str) -> None:
        self.run_dir = run_dir
        self.run_id = run_id
        self.events_file = run_dir / "events.jsonl"
        self.tools_dir = run_dir / "tools"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.tools_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._seq = 0
        self._subscribers: set[asyncio.Queue[Event | None]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._closed = False

        # If events file already exists, initialize seq from disk
        if self.events_file.is_file():
            existing = self.read_events(after=0)
            if existing:
                self._seq = max(e.seq for e in existing)

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the async event loop for thread-safe subscriber dispatch."""
        self._loop = loop

    def publish(
        self,
        kind: EventKind,
        payload: dict[str, Any],
        agent: str | None = None,
        team: TeamName | None = None,
    ) -> Event:
        """Publish a new event, assign monotonic seq, write to disk, and notify subscribers."""
        with self._lock:
            self._seq += 1
            event = Event(
                seq=self._seq,
                ts=utc_now_iso(),
                run_id=self.run_id,
                kind=kind,
                agent=agent,
                team=team,
                payload=payload,
            )
            line = event.model_dump_json() + "\n"
            with open(self.events_file, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()

            self._dispatch_to_subscribers(event)
            return event

    def publish_tool_result(
        self,
        tool: str,
        call_id: str,
        ok: bool,
        duration_ms: int,
        result: str,
        agent: str | None = None,
        team: TeamName | None = None,
    ) -> Event:
        """Record a tool result, truncating in the event stream and saving full result to disk if large."""
        if len(result) > MAX_INLINE_TOOL_RESULT_LENGTH:
            tool_path = self.tools_dir / f"{call_id}.txt"
            with open(tool_path, "w", encoding="utf-8") as f:
                f.write(result)
            preview = result[:MAX_INLINE_TOOL_RESULT_LENGTH] + "... [truncated]"
            payload = {
                "tool": tool,
                "call_id": call_id,
                "ok": ok,
                "duration_ms": duration_ms,
                "result": preview,
                "truncated": True,
                "full_ref": f"/api/runs/{self.run_id}/tools/{call_id}",
            }
        else:
            payload = {
                "tool": tool,
                "call_id": call_id,
                "ok": ok,
                "duration_ms": duration_ms,
                "result": result,
                "truncated": False,
                "full_ref": None,
            }
        return self.publish(kind="tool_result", payload=payload, agent=agent, team=team)

    def _dispatch_to_subscribers(self, item: Event | None) -> None:
        """Push an item to all active subscriber queues safely."""
        subscribers = list(self._subscribers)
        if not subscribers:
            return

        def _push() -> None:
            for q in subscribers:
                with contextlib.suppress(asyncio.QueueFull):
                    q.put_nowait(item)

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(_push)
        else:
            _push()

    def register_subscriber(self, q: asyncio.Queue[Event | None]) -> None:
        """Register a subscriber queue."""
        with self._lock:
            self._subscribers.add(q)

    def unregister_subscriber(self, q: asyncio.Queue[Event | None]) -> None:
        """Unregister a subscriber queue."""
        with self._lock:
            self._subscribers.discard(q)

    def read_events(self, after: int = 0) -> list[Event]:
        """Read events from disk with seq > after in strict ascending order."""
        if not self.events_file.is_file():
            return []
        events: list[Event] = []
        with open(self.events_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("seq", 0) > after:
                        events.append(Event.model_validate(data))
                except Exception:
                    continue
        events.sort(key=lambda e: e.seq)
        return events

    async def subscribe(self, after: int = 0, is_active: bool = True) -> AsyncIterator[Event]:
        """Replay events > after, then stream live events without gaps or duplicates."""
        q: asyncio.Queue[Event | None] = asyncio.Queue(maxsize=1000)

        # Set event loop reference if available
        with contextlib.suppress(RuntimeError):
            self.set_event_loop(asyncio.get_running_loop())

        if is_active:
            self.register_subscriber(q)

        last_seq = after
        try:
            # 1. Replay from disk first
            disk_events = self.read_events(after=after)
            for event in disk_events:
                if event.seq > last_seq:
                    yield event
                    last_seq = event.seq

            # If the run is not active or was closed, we are done
            if not is_active or self._closed:
                return

            # 2. Consume live events from queue
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # Timeout keep-alive check: if run closed in the meantime, stop
                    if self._closed:
                        break
                    continue

                if event is None:
                    # End of stream sentinel
                    break

                if event.seq <= last_seq:
                    # Duplicate from subscription overlap
                    continue

                yield event
                last_seq = event.seq

                # If this event terminates the run, finish stream
                if event.kind == "run_state":
                    status = event.payload.get("status")
                    if status in ("completed", "cancelled", "failed"):
                        break
        finally:
            self.unregister_subscriber(q)

    def close(self) -> None:
        """Mark bus as closed and signal EOF to all active subscribers."""
        with self._lock:
            self._closed = True
            self._dispatch_to_subscribers(None)
            self._subscribers.clear()
