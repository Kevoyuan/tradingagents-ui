"""trade-ui CLI - launch the local Streamlit UI."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path


def _find_project_root() -> Path:
    """Find the tradingagents-ui project directory (where app.py lives)."""
    # When installed with pip install -e ., this file is at <project>/trade_ui/cli.py
    return Path(__file__).resolve().parent.parent


def _resolve_app_path() -> Path:
    """Resolve which app.py to run.

    Priority:
    1) TRADINGAGENTS_UI_APP_PATH
    2) ./app.py from current working directory
    3) installed package project root app.py
    """
    env_path = os.environ.get("TRADINGAGENTS_UI_APP_PATH")
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if candidate.is_file():
            return candidate
        print(f"Error: TRADINGAGENTS_UI_APP_PATH does not point to a file: {candidate}")
        sys.exit(1)

    cwd_app = (Path.cwd() / "app.py").resolve()
    if cwd_app.is_file():
        return cwd_app

    fallback = _find_project_root() / "app.py"
    if fallback.is_file():
        return fallback.resolve()

    print("Error: app.py not found.")
    print("Checked TRADINGAGENTS_UI_APP_PATH, current working directory, and installed package location.")
    sys.exit(1)


def _get_lan_ip() -> str | None:
    """Best-effort LAN IP detection for phone/tablet access hints."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: trade-ui [OPTIONS]")
        print()
        print("  Launch the local TradingAgents Streamlit UI.")
        print()
        print("Options:")
        print("  --help, -h     Show this message")
        print("  --port PORT    Specify server port (default: 8501)")
        print("  --host HOST    Bind server address (use 0.0.0.0 for phone/LAN access)")
        print("  --lan          Shortcut for --host 0.0.0.0")
        print("  --no-update    Deprecated no-op kept for old launcher compatibility")
        print()
        print("All other options are passed to Streamlit.")
        sys.exit(0)

    app_path = _resolve_app_path()

    # Build streamlit command
    port = "8501"
    host = None
    extra_args = []
    args = [arg for arg in sys.argv[1:] if arg != "--no-update"]
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = args[i + 1]
            i += 2
        elif args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == "--lan":
            host = "0.0.0.0"
            i += 1
        else:
            extra_args.append(args[i])
            i += 1

    os.environ["TRADINGAGENTS_UI_LOCAL"] = "1"

    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path),
           "--server.port", port, "--server.headless", "true"]
    if host:
        cmd.extend(["--server.address", host])
    cmd.extend(extra_args)

    print(f"Launching UI from: {app_path}")
    if host == "0.0.0.0":
        lan_ip = _get_lan_ip()
        if lan_ip:
            print(f"Phone/LAN URL: http://{lan_ip}:{port}")
        else:
            print(f"Phone/LAN URL: http://<your-computer-ip>:{port}")
    print()
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
