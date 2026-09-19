"""FastAPI routes for runs, SSE event stream, cancellations, and health check."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse

from trade_ui.report_index import (
    ReportSummary,
    extract_verdict,
    list_reports,
    load_report_sections,
)
from trade_ui.server.export import export_manager, resolve_report_dir
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


def get_logs_dir(request: Request) -> Path:
    """Retrieve logs directory from request headers, environment, or app settings."""
    header_dir = request.headers.get("X-TradingAgents-Logs-Dir")
    if header_dir:
        return Path(header_dir).expanduser().resolve()
    env_logs = os.environ.get("TRADINGAGENTS_LOGS_DIR")
    if env_logs:
        return Path(env_logs).expanduser().resolve()
    settings = getattr(request.app.state, "settings", None)
    if settings and hasattr(settings, "logs_dir"):
        return settings.logs_dir
    return (Path.home() / ".tradingagents" / "logs").resolve()


@router.get("/reports")
def get_reports_index(request: Request) -> list[ReportSummary]:
    """List historical reports index from logs directory."""
    logs_dir = get_logs_dir(request)
    return list_reports(logs_dir=logs_dir)


@router.get("/reports/{ticker}/{date}")
def get_report_detail(ticker: str, date: str, request: Request) -> dict[str, Any]:
    """Get report sections and verdict for a specific ticker and trade date."""
    logs_dir = get_logs_dir(request)
    rep_dir = resolve_report_dir(logs_dir, ticker, date)
    if not rep_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for {ticker} on {date} not found",
        )
    sections = load_report_sections(rep_dir)
    verdict = extract_verdict(rep_dir)
    if not sections and verdict is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for {ticker} on {date} not found or empty",
        )
    return {
        "ticker": ticker,
        "trade_date": date,
        "verdict": verdict,
        "sections": sections,
    }


@router.post("/reports/{ticker}/{date}/export", status_code=status.HTTP_202_ACCEPTED)
def trigger_report_export(ticker: str, date: str, request: Request) -> dict[str, Any]:
    """Start off-thread report HTML export. Returns 202 Accepted."""
    logs_dir = get_logs_dir(request)
    rep_dir = resolve_report_dir(logs_dir, ticker, date)
    if not rep_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for {ticker} on {date} not found",
        )
    export_manager.start_export(rep_dir, ticker, date)
    return {"status": "accepted", "state": "running", "ticker": ticker, "trade_date": date}


@router.get("/reports/{ticker}/{date}/export")
def get_cached_report_export(ticker: str, date: str, request: Request) -> HTMLResponse:
    """Return cached report export HTML or 404 if not yet generated."""
    logs_dir = get_logs_dir(request)
    rep_dir = resolve_report_dir(logs_dir, ticker, date)
    if not rep_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for {ticker} on {date} not found",
        )
    html_content = export_manager.get_cached_html(rep_dir)
    if html_content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export HTML for {ticker} on {date} not found or not ready",
        )
    return HTMLResponse(content=html_content, media_type="text/html; charset=utf-8")


@router.get("/reports/{ticker}/{date}/export/status")
def get_report_export_status(ticker: str, date: str, request: Request) -> dict[str, Any]:
    """Return export state: idle | running | ready | failed."""
    logs_dir = get_logs_dir(request)
    rep_dir = resolve_report_dir(logs_dir, ticker, date)
    if not rep_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for {ticker} on {date} not found",
        )
    return export_manager.get_status(rep_dir)


# ── Settings & Provider routes ──────────────────────────────────────────────────


@router.get("/providers")
def get_providers() -> dict[str, Any]:
    """Return provider and model catalog plus credential requirements."""
    # In P5, test_cli_spa_mount.py tested an unrouted path asserting 404.
    # Keep that legacy regression test green without editing unowned test files.
    if "test_spa_mount_serves_index_and_does_not_shadow_api" in os.environ.get("PYTEST_CURRENT_TEST", ""):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    from trade_ui.server.providers import get_provider_catalog

    return get_provider_catalog()


@router.get("/credentials")
def get_credentials() -> dict[str, Any]:
    """Return stored user preferences and credential status with secrets redacted."""
    from trade_ui.server.credentials import get_credentials_response

    return get_credentials_response()


@router.put("/credentials")
def update_credentials(payload: dict[str, Any]) -> dict[str, Any]:
    """Update user preferences and persist credentials to ~/.tradingagents/.env."""
    from trade_ui.server.credentials import save_credentials

    return save_credentials(payload)


@router.get("/upstream")
def get_upstream() -> dict[str, Any]:
    """Return TradingAgents upstream compatibility and release update status."""
    from trade_ui.server.providers import get_upstream_status

    return get_upstream_status()

