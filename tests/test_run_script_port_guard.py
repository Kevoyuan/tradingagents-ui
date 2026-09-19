"""Regression tests for the ./run.sh port guard.

Before the guard, running ./run.sh while the app was already listening spent
about two seconds inside uvicorn startup and then exited with EADDRINUSE
(status 3). On screen that read as "the app ran for two seconds and quit".

The guard runs before the Python environment is resolved, so these tests stub
lsof/curl/open on PATH and never touch a real server or browser.
"""

from __future__ import annotations

import os
import pathlib
import stat
import subprocess

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUN_SCRIPT = REPO_ROOT / "run.sh"


HEALTH_PAYLOAD = '{"status":"ok"}'
# What a stray Streamlit instance answers on /health: 200, but HTML not JSON.
FOREIGN_PAYLOAD = "<!doctype html><html><body>streamlit</body></html>"


def _write_stub(
    bin_dir: pathlib.Path, name: str, *, exit_code: int, calls: pathlib.Path, stdout: str = ""
) -> None:
    path = bin_dir / name
    path.write_text(
        "#!/bin/sh\n" f'echo "$0 $*" >> "{calls}"\n' f"printf '%s' '{stdout}'\n" f"exit {exit_code}\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _prepare_fake_tools(
    tmp_path: pathlib.Path, *, port_busy: bool, health_body: str
) -> tuple[pathlib.Path, pathlib.Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls.txt"
    _write_stub(bin_dir, "lsof", exit_code=0 if port_busy else 1, calls=calls)
    _write_stub(bin_dir, "curl", exit_code=0, calls=calls, stdout=health_body)
    _write_stub(bin_dir, "open", exit_code=0, calls=calls)
    return bin_dir, calls


def _run_script(bin_dir: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env.pop("TRADINGAGENTS_UI_PORT", None)
    return subprocess.run(
        ["bash", str(RUN_SCRIPT), *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_reuses_server_already_listening_on_the_default_port(tmp_path):
    bin_dir, calls = _prepare_fake_tools(tmp_path, port_busy=True, health_body=HEALTH_PAYLOAD)

    result = _run_script(bin_dir)

    assert result.returncode == 0, result.stderr
    assert "already running at http://localhost:8501" in result.stdout
    log = calls.read_text(encoding="utf-8")
    # Probe the FastAPI app's own health route over IPv4, not the legacy shim.
    assert "http://127.0.0.1:8501/health" in log
    assert "_stcore" not in log
    assert "open http://localhost:8501" in log
    # It must stop there instead of falling through to a second server startup.
    assert "trade_ui.cli" not in log


def test_reports_foreign_process_holding_the_port(tmp_path):
    """A 200 on /health is not enough: a stray Streamlit answers 200 HTML."""
    bin_dir, calls = _prepare_fake_tools(tmp_path, port_busy=True, health_body=FOREIGN_PAYLOAD)

    result = _run_script(bin_dir)

    assert result.returncode == 1
    assert "Port 8501 is already in use by another process." in result.stderr
    assert "open" not in calls.read_text(encoding="utf-8")


def test_guard_follows_the_port_passed_on_the_command_line(tmp_path):
    bin_dir, calls = _prepare_fake_tools(tmp_path, port_busy=True, health_body=HEALTH_PAYLOAD)

    result = _run_script(bin_dir, "--port", "8502")

    assert result.returncode == 0, result.stderr
    log = calls.read_text(encoding="utf-8")
    assert "-iTCP:8502" in log
    assert "open http://localhost:8502" in log
