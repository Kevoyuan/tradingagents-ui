"""TradingAgents FastAPI backend package."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ["app", "create_app"]


def __getattr__(name: str) -> Any:
    """Import the ASGI app on first use rather than on package import.

    Importing `trade_ui.server.app` here built the whole API at package-import
    time. `report_index` imports `trade_ui.server.models` for the verdict model,
    which then re-entered this package and reached `api.py` while
    `report_index` was still half-built — a circular import that only showed up
    when a module touched `report_index` before anything else had imported
    `trade_ui.server`. `from trade_ui.server import create_app` keeps working;
    `import trade_ui.server` no longer drags the app in.
    """
    if name in ("app", "create_app"):
        # import_module, not `from trade_ui.server import app`: the from-import
        # form resolves through this very __getattr__ and recurses forever.
        app_module = importlib.import_module("trade_ui.server.app")
        return getattr(app_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
