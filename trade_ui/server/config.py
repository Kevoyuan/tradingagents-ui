"""Configuration and paths for the backend server."""

from __future__ import annotations

import os
from pathlib import Path


class ServerSettings:
    """Runtime server settings."""

    def __init__(
        self,
        runs_dir: Path | str | None = None,
        use_stub: bool | None = None,
        logs_dir: Path | str | None = None,
    ) -> None:
        env_dir = os.environ.get("TRADINGAGENTS_RUNS_DIR")
        if runs_dir is not None:
            self.runs_dir = Path(runs_dir).expanduser().resolve()
        elif env_dir:
            self.runs_dir = Path(env_dir).expanduser().resolve()
        else:
            self.runs_dir = (Path.home() / ".tradingagents" / "runs").resolve()

        env_logs = os.environ.get("TRADINGAGENTS_LOGS_DIR")
        if logs_dir is not None:
            self.logs_dir = Path(logs_dir).expanduser().resolve()
        elif env_logs:
            self.logs_dir = Path(env_logs).expanduser().resolve()
        else:
            self.logs_dir = (Path.home() / ".tradingagents" / "logs").resolve()

        if use_stub is not None:
            self.use_stub = use_stub
        else:
            env_stub = os.environ.get("TRADINGAGENTS_STUB", "").lower()
            self.use_stub = env_stub in ("1", "true", "yes")

        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
