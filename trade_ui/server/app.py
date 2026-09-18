"""FastAPI backend application factory and server entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trade_ui.server.api import router
from trade_ui.server.config import ServerSettings
from trade_ui.server.registry import RunRegistry


def create_app(runs_dir: Path | str | None = None, use_stub: bool | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = ServerSettings(runs_dir=runs_dir, use_stub=use_stub)
    registry = RunRegistry(settings=settings)

    app = FastAPI(
        title="TradingAgents API",
        version="1.3.0",
        description="FastAPI backend for TradingAgents run monitor and report viewer",
    )

    # Allow CORS for local frontend development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach registry to application state
    app.state.settings = settings
    app.state.registry = registry

    # Register API routes under /api
    app.include_router(router, prefix="/api")

    # Also expose /health at root for launchers
    @app.get("/health")
    def root_health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
