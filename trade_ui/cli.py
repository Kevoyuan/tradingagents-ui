"""trade-ui CLI - launch the TradingAgents Web UI."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def _find_project_root() -> Path:
    """Find the tradingagents-ui project directory."""
    # When installed with pip install -e ., this file is at <project>/trade_ui/cli.py
    return Path(__file__).resolve().parent.parent


def _get_static_dir() -> Path:
    """Resolve the directory containing built frontend static assets."""
    return Path(__file__).resolve().parent / "static"


def _get_lan_ip() -> str | None:
    """Best-effort LAN IP detection for phone/tablet access hints."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def create_ui_app(static_dir: Path | None = None) -> FastAPI:
    """Create FastAPI application with static assets mounted for the SPA."""
    from starlette.exceptions import HTTPException
    from starlette.staticfiles import StaticFiles

    from trade_ui.server.app import create_app

    s_dir = static_dir or _get_static_dir()

    class SPAStaticFiles(StaticFiles):
        async def __call__(self, scope, receive, send):
            # This mount only ever serves files over HTTP. Starlette's
            # StaticFiles.__call__ asserts scope["type"] == "http", which raises
            # inside the request handler for any other scope. The realistic case
            # is a websocket upgrade from a stale client that saw this port
            # answer Streamlit's /_stcore/health probe and assumed a Streamlit
            # server was listening. Refuse it cleanly instead of crashing.
            if scope["type"] != "http":
                if scope["type"] == "websocket":
                    from starlette.websockets import WebSocket

                    await WebSocket(scope, receive=receive, send=send).close(code=1000)
                return
            await super().__call__(scope, receive, send)

        async def get_response(self, path: str, scope):
            # Never let the static mount intercept /api routes
            if scope.get("path", "").startswith("/api"):
                raise HTTPException(status_code=404, detail="Not Found")
            try:
                response = await super().get_response(path, scope)
                if response.status_code == 404 and not path.startswith("assets/"):
                    return await super().get_response("index.html", scope)
                return response
            except HTTPException as exc:
                if exc.status_code == 404 and not path.startswith("assets/"):
                    return await super().get_response("index.html", scope)
                raise exc

    app = create_app()

    # Legacy Streamlit health probe compatibility
    @app.get("/_stcore/health")
    def stcore_health() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/", SPAStaticFiles(directory=str(s_dir), html=True), name="static")
    return app


def _run_default(args: list[str]) -> None:
    """Launch the FastAPI + React application via uvicorn."""
    import uvicorn

    static_dir = _get_static_dir()
    index_file = static_dir / "index.html"
    if not index_file.is_file():
        print(
            f"Error: Built frontend assets not found at {index_file}.\n"
            "Please run 'bash scripts/build-frontend.sh' to build the frontend first.",
            file=sys.stderr,
        )
        sys.exit(1)

    port = 8501
    host = "127.0.0.1"
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                print(f"Error: Invalid port number: {args[i + 1]}", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == "--lan":
            host = "0.0.0.0"
            i += 1
        else:
            i += 1

    os.environ["TRADINGAGENTS_UI_LOCAL"] = "1"

    print(f"Starting TradingAgents UI at http://{host}:{port}")
    if host == "0.0.0.0":
        lan_ip = _get_lan_ip()
        if lan_ip:
            print(f"Phone/LAN URL: http://{lan_ip}:{port}")
        else:
            print(f"Phone/LAN URL: http://<your-computer-ip>:{port}")
    print()

    app = create_ui_app(static_dir)
    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: trade-ui [OPTIONS]")
        print()
        print("  Launch the local TradingAgents UI.")
        print()
        print("Options:")
        print("  --help, -h     Show this message")
        print("  --port PORT    Specify server port (default: 8501)")
        print("  --host HOST    Bind server address (default: 127.0.0.1, use 0.0.0.0 for phone/LAN access)")
        print("  --lan          Shortcut for --host 0.0.0.0")
        print("  --no-update    Deprecated no-op kept for old launcher compatibility")
        print()
        print("Default mode:")
        print("  Starts uvicorn serving the FastAPI backend and built React SPA.")
        print()
        sys.exit(0)

    raw_args = [arg for arg in sys.argv[1:] if arg != "--no-update"]
    _run_default(raw_args)


if __name__ == "__main__":
    main()
