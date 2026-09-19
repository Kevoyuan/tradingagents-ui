"""Safe report persistence built on the upstream TradingAgents report writer."""

from __future__ import annotations

import re
import shutil
from collections.abc import Callable
from pathlib import Path


def sanitize_model_filename(model: str) -> str:
    """Render a model id as one safe filename component.

    The retired Streamlit app passed its own helper in here; it lived in `app.py`
    and left with it, so the default now ships with the function that needs it.
    Model ids like `deepseek-v4-flash` pass through unchanged, which keeps the
    existing `complete_report__deep-<model>.md` names stable.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(model)).strip("-")
    return cleaned or "model"


def save_ui_reports(
    final_state: dict,
    ticker: str,
    trade_date: str,
    results_root: str | Path,
    deep_model: str,
    safe_filename_part: Callable[[str], str] = sanitize_model_filename,
) -> tuple[Path, str]:
    """Write the upstream report tree plus the UI's model-specific copy."""
    from tradingagents.dataflows.utils import safe_ticker_component
    from tradingagents.reporting import write_report_tree

    safe_ticker = safe_ticker_component(ticker)
    report_dir = Path(results_root) / safe_ticker / str(trade_date) / "reports"
    complete_report_path = write_report_tree(final_state, safe_ticker, report_dir)
    model_report_path = report_dir / f"complete_report__deep-{safe_filename_part(deep_model)}.md"
    shutil.copyfile(complete_report_path, model_report_path)
    return report_dir, complete_report_path.read_text(encoding="utf-8")
