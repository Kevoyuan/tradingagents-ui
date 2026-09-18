"""Data models for TradingAgents server, runs, events, and payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

EventKind = Literal[
    "run_state",
    "agent_status",
    "agent_message",
    "user_message",
    "tool_call",
    "tool_result",
    "stats",
    "report_section",
    "verdict",
    "error",
]

TeamName = Literal["analyst", "research", "trading", "risk", "portfolio"]

RunStatus = Literal["pending", "running", "completed", "cancelled", "failed"]


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class Event(BaseModel):
    """Event schema matching the Section 2 event stream contract."""

    seq: int
    ts: str = Field(default_factory=utc_now_iso)
    run_id: str
    kind: EventKind
    agent: str | None = None
    team: TeamName | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RunConfig(BaseModel):
    """Configuration for starting a new run."""

    ticker: str
    trade_date: str | None = None
    analysts: list[str] | None = None
    depth: int = 1
    quick_model: str | None = None
    deep_model: str | None = None
    provider: str | None = None
    use_stub: bool = False
    step_delay: float = 0.0
    config: dict[str, Any] = Field(default_factory=dict)


class RunHeader(BaseModel):
    """Run header metadata stored in run.json and returned by GET /api/runs."""

    run_id: str
    status: RunStatus = "pending"
    ticker: str
    trade_date: str
    created_at: str = Field(default_factory=utc_now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    stats: dict[str, Any] | None = None
    verdict: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class VerdictPayload(BaseModel):
    """Verdict shape matching Section 3."""

    rating: Literal["Buy", "Overweight", "Hold", "Underweight", "Sell"]
    source_section: Literal["portfolio", "trader"]
    price_target: str | None = None
    executive_summary: str | None = None
    entry_price: str | None = None
    stop_loss: str | None = None
    position_sizing: str | None = None
