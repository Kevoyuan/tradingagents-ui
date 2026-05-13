"""trade-ui CLI - update TradingAgents and launch the Streamlit UI."""

from __future__ import annotations

import importlib.util
import os
import socket
import subprocess
import sys
from pathlib import Path

TRADINGAGENTS_REPO_URL = "https://github.com/TauricResearch/TradingAgents.git"


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


def _find_tradingagents_dir() -> Path | None:
    """Find an explicitly configured TradingAgents checkout."""
    env_dir = os.environ.get("TRADINGAGENTS_DIR")
    if env_dir:
        candidate = Path(env_dir).expanduser().resolve()
        if (candidate / ".git").exists():
            return candidate

    return None


def _is_tradingagents_installed() -> bool:
    return importlib.util.find_spec("tradingagents") is not None


def _latest_local_tag(repo_dir: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0", "HEAD"],
            cwd=repo_dir,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def _latest_remote_tag(repo_dir: Path) -> str:
    try:
        subprocess.run(
            ["git", "fetch", "--tags", "--quiet"],
            cwd=repo_dir,
            timeout=10,
            check=False,
            capture_output=True,
        )
        tag = subprocess.check_output(
            ["git", "tag", "--sort=-version:refname"],
            cwd=repo_dir,
            stderr=subprocess.DEVNULL,
            text=True,
        ).splitlines()
        return tag[0] if tag else "unknown"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"


def _has_local_changes(repo_dir: Path) -> bool:
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except subprocess.CalledProcessError:
        return True
    return bool(status.strip())


def _ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        reply = input(f"{prompt} {suffix} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    if not reply:
        return default
    return reply in ("y", "yes")


def _install_local_checkout(repo_dir: Path) -> bool:
    print("Installing TradingAgents checkout in the current environment...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(repo_dir), "--quiet"], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"TradingAgents install failed with exit code {exc.returncode}.")
        return False
    return True


def _update_local_checkout(repo_dir: Path) -> bool:
    if _has_local_changes(repo_dir):
        print(f"TradingAgents checkout has local changes: {repo_dir}")
        print("Skipping automatic pull. Commit, stash, or update it manually when ready.")
        return _install_local_checkout(repo_dir) if not _is_tradingagents_installed() else True

    print("Pulling latest TradingAgents...")
    try:
        subprocess.run(["git", "pull", "--ff-only"], cwd=repo_dir, check=True)
    except subprocess.CalledProcessError:
        print("Fast-forward failed, trying rebase...")
        try:
            subprocess.run(["git", "pull", "--rebase"], cwd=repo_dir, check=True)
        except subprocess.CalledProcessError as exc:
            print(f"TradingAgents update failed with exit code {exc.returncode}.")
            return False

    return _install_local_checkout(repo_dir)


def _update_git_dependency() -> bool:
    print("Updating TradingAgents from GitHub in the current environment...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", f"git+{TRADINGAGENTS_REPO_URL}", "--quiet"],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"TradingAgents install/update failed with exit code {exc.returncode}.")
        return False
    return True


def _check_tradingagents_updates() -> bool:
    """Check and optionally update TradingAgents before launching the UI."""
    print("Checking for TradingAgents updates...")
    repo_dir = _find_tradingagents_dir()

    if not repo_dir:
        if _is_tradingagents_installed():
            print("TradingAgents is installed in the current Python environment.")
            if _ask_yes_no("Update the installed TradingAgents package from GitHub?", default=False):
                return _update_git_dependency()
            print("Skipping TradingAgents update.")
            return True

        print("TradingAgents is not installed in the current Python environment.")
        if _ask_yes_no("Install TradingAgents from GitHub now?", default=True):
            return _update_git_dependency()
        else:
            print("Cannot launch TradingAgents UI without the TradingAgents package.")
            print(f"Install it later with: {sys.executable} -m pip install git+{TRADINGAGENTS_REPO_URL}")
            return False

    local = _latest_local_tag(repo_dir)
    remote = _latest_remote_tag(repo_dir)
    installed = _is_tradingagents_installed()

    if local == remote:
        print(f"TradingAgents is up-to-date ({local})")
        if not installed:
            return _install_local_checkout(repo_dir)
        return True

    print(f"TradingAgents update available: {local} -> {remote}")
    if _ask_yes_no("Update now?", default=True):
        if not _update_local_checkout(repo_dir):
            return False
        print(f"Updated TradingAgents to {_latest_local_tag(repo_dir)}")
    else:
        print("Skipping TradingAgents update.")
        if not installed:
            return _install_local_checkout(repo_dir)
    return True


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
        print("  Check TradingAgents updates, then launch the Streamlit UI.")
        print()
        print("Options:")
        print("  --help, -h    Show this message")
        print("  --port PORT   Specify server port (default: 8501)")
        print("  --host HOST   Bind server address (use 0.0.0.0 for phone/LAN access)")
        print("  --lan         Shortcut for --host 0.0.0.0")
        print()
        print("All other options are passed to Streamlit.")
        sys.exit(0)

    app_path = _resolve_app_path()

    if not _check_tradingagents_updates():
        sys.exit(1)

    # Build streamlit command
    port = "8501"
    host = None
    extra_args = []
    args = sys.argv[1:]
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
