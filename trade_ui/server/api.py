"""FastAPI routes for runs, SSE event stream, cancellations, and health check."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse, StreamingResponse

from trade_ui.server.models import RunConfig, RunHeader
from trade_ui.server.registry import (
    RunConflictError,
    RunNotFoundError,
    RunNotRunningError,
    RunRegistry,
)

router = APIRouter()


def get_registry(request: Request) -> RunRegistry:
    """Retrieve RunRegistry instance from app state."""
    return request.app.state.registry  # type: ignore[no-any-return]


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe returning server health status."""
    return {"status": "ok"}


@router.post("/runs", status_code=status.HTTP_201_CREATED)
def create_run(config: RunConfig, request: Request) -> dict[str, Any]:
    """Start a new analysis run. Returns 409 Conflict if another run is active."""
    registry = get_registry(request)
    try:
        header = registry.start_run(config)
        return {
            "run_id": header.run_id,
            "status": header.status,
            "ticker": header.ticker,
            "trade_date": header.trade_date,
        }
    except RunConflictError as err:
        active_id = registry.get_active_run_id()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(err), "active_run_id": active_id},
        ) from err


@router.get("/runs")
def list_runs(request: Request) -> list[RunHeader]:
    """List run history index from ~/.tradingagents/runs/."""
    registry = get_registry(request)
    return registry.list_runs()


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request) -> RunHeader:
    """Get run header, stats, and verdict by run_id."""
    registry = get_registry(request)
    run = registry.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")
    return run


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str, request: Request) -> dict[str, Any]:
    """Cooperatively cancel an active run. Returns 409 Conflict if not running."""
    registry = get_registry(request)
    try:
        registry.cancel_run(run_id)
        return {"status": "cancelling", "run_id": run_id}
    except RunNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except RunNotRunningError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err


@router.get("/runs/{run_id}/events")
async def stream_events(
    run_id: str,
    request: Request,
    after: int = Query(default=0, ge=0, description="Replay events strictly after this sequence number"),
) -> StreamingResponse:
    """Stream run events as Server-Sent Events (SSE). Replays from after exclusive, then follows live."""
    registry = get_registry(request)
    run = registry.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")

    event_bus = registry.get_event_bus(run_id)
    if event_bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event log for run {run_id} not found")

    # Determine whether run is currently active
    is_active = (
        registry.active_run is not None
        and registry.active_run.run_id == run_id
        and registry.active_run.is_active()
    )

    async def sse_generator() -> AsyncIterator[str]:
        async for event in event_bus.subscribe(after=after, is_active=is_active):
            event_data = event.model_dump_json()
            yield f"id: {event.seq}\nevent: message\ndata: {event_data}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runs/{run_id}/tools/{call_id}")
def get_tool_result(run_id: str, call_id: str, request: Request) -> PlainTextResponse:
    """Retrieve full untruncated tool result saved on disk."""
    registry = get_registry(request)
    run = registry.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")

    tool_file = registry.runs_dir / run_id / "tools" / f"{call_id}.txt"
    if not tool_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool result not found")

    with open(tool_file, encoding="utf-8") as f:
        content = f.read()
    return PlainTextResponse(content)
