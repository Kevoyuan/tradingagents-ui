"""HTML export service for TradingAgents reports.

Implements Phase P4 export requirements per webapp-migration-plan.md:
- Section 6: Spawns Bun + vendored baoyu-markdown-to-html converter
- Off-thread execution (202 Accepted)
- State machine: idle | running | ready | failed
- Output filename: complete_report__export-<HTML_REPORT_THEME_VERSION>.html
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Literal

from trade_ui.report_index import load_report_sections

# Must match HTML_REPORT_THEME_VERSION in app.py while legacy UI remains; P5 removes duplication
HTML_REPORT_THEME_VERSION = "quant-terminal-readme-shot-v2"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BAOYU_MARKDOWN_TO_HTML_SCRIPT = PROJECT_ROOT / "tools" / "baoyu-markdown-to-html" / "scripts" / "main.ts"
BAOYU_MARKDOWN_TO_HTML_DIR = BAOYU_MARKDOWN_TO_HTML_SCRIPT.parent

_INSTALL_LOCK = threading.Lock()

ExportState = Literal["idle", "running", "ready", "failed"]


def get_export_filename() -> str:
    """Return the versioned export HTML filename."""
    return f"complete_report__export-{HTML_REPORT_THEME_VERSION}.html"


def get_bun_command() -> list[str]:
    """Return a command suitable for executing Bun or npx bun."""
    if shutil.which("bun"):
        return ["bun"]
    if shutil.which("npx"):
        return ["npx", "-y", "bun"]
    raise RuntimeError("Neither bun nor npx found on PATH")


def ensure_baoyu_dependencies() -> None:
    """Ensure marked and other converter dependencies are installed."""
    marked_package = BAOYU_MARKDOWN_TO_HTML_DIR / "node_modules" / "marked" / "package.json"
    if marked_package.exists():
        return
    with _INSTALL_LOCK:
        if marked_package.exists():
            return
        cmd = [*get_bun_command(), "install"]
        result = subprocess.run(
            cmd,
            cwd=BAOYU_MARKDOWN_TO_HTML_DIR,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
            raise RuntimeError(f"Failed to install HTML converter dependencies: {detail}")


def resolve_report_dir(logs_dir: Path | str, ticker: str, trade_date: str) -> Path:
    """Resolve report directory under logs_dir."""
    base = Path(logs_dir).expanduser().resolve() / ticker / trade_date
    rep_dir = base / "reports"
    if rep_dir.is_dir():
        return rep_dir
    return base


def run_export_sync(
    report_dir: Path,
    ticker: str,
    trade_date: str,
) -> Path:
    """Synchronously generate the export HTML and save it to complete_report__export-<VERSION>.html."""
    if not BAOYU_MARKDOWN_TO_HTML_SCRIPT.exists():
        raise RuntimeError(f"Bundled markdown converter not found: {BAOYU_MARKDOWN_TO_HTML_SCRIPT}")

    ensure_baoyu_dependencies()

    # Determine markdown source
    complete_md = report_dir / "complete_report.md"
    if complete_md.is_file():
        md_text = complete_md.read_text(encoding="utf-8")
    else:
        # Fallback to loading and concatenating sections
        sections = load_report_sections(report_dir, normalize=False)
        if not sections:
            raise RuntimeError(f"No report markdown or sections found in {report_dir}")
        md_parts: list[str] = [f"# {ticker} - {trade_date}\n"]
        for sec in sections:
            md_parts.append(f"\n## {sec.title}\n")
            for blk in sec.blocks:
                md_parts.append(f"\n### {blk.name}\n\n{blk.markdown}\n")
        md_text = "\n".join(md_parts)

    # Detect model name if present
    model_name: str | None = None
    for item in report_dir.glob("complete_report__deep-*.md"):
        m = re.search(r"complete_report__deep-(.+)\.md$", item.name)
        if m:
            model_name = m.group(1)
            break

    output_file = report_dir / get_export_filename()

    with tempfile.TemporaryDirectory(prefix="tradingagents-export-") as tmp:
        tmp_md = Path(tmp) / "report.md"
        tmp_md.write_text(md_text, encoding="utf-8")

        cmd = [
            *get_bun_command(),
            str(BAOYU_MARKDOWN_TO_HTML_SCRIPT),
            str(tmp_md),
            "--theme",
            "quant-terminal",
            "--keep-title",
            "--qt-ticker",
            ticker,
            "--qt-date",
            trade_date,
        ]
        if model_name:
            cmd.extend(["--qt-model", model_name])

        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
            raise RuntimeError(f"HTML generation failed: {detail}")

        try:
            payload = json.loads(result.stdout)
            html_path = Path(payload["htmlPath"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError(f"HTML generation returned invalid output: {result.stdout}") from exc

        html_content = html_path.read_text(encoding="utf-8")
        output_file.write_text(html_content, encoding="utf-8")
        return output_file


class ExportManager:
    """Manages background report export tasks and status caching."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Key: (report_dir_str) -> {"state": ExportState, "error": str | None}
        self._tasks: dict[str, dict[str, Any]] = {}

    def _task_key(self, report_dir: Path) -> str:
        return str(report_dir.resolve())

    def get_status(self, report_dir: Path) -> dict[str, Any]:
        """Check status of export: idle | running | ready | failed."""
        key = self._task_key(report_dir)
        target_file = report_dir / get_export_filename()

        with self._lock:
            task = self._tasks.get(key)
            if task is not None:
                if task["state"] == "running":
                    return {"state": "running", "error": None}
                if task["state"] == "failed":
                    return {"state": "failed", "error": task.get("error")}

        if target_file.is_file():
            return {"state": "ready", "error": None}

        return {"state": "idle", "error": None}

    def get_cached_html(self, report_dir: Path) -> str | None:
        """Return cached export HTML content if ready, else None."""
        target_file = report_dir / get_export_filename()
        if target_file.is_file():
            return target_file.read_text(encoding="utf-8")
        return None

    def start_export(self, report_dir: Path, ticker: str, trade_date: str) -> None:
        """Launch export job in background thread."""
        key = self._task_key(report_dir)
        with self._lock:
            existing = self._tasks.get(key)
            if existing and existing["state"] == "running":
                return
            self._tasks[key] = {"state": "running", "error": None}

        def _worker() -> None:
            try:
                run_export_sync(report_dir, ticker, trade_date)
                with self._lock:
                    self._tasks[key] = {"state": "ready", "error": None}
            except Exception as exc:
                with self._lock:
                    self._tasks[key] = {"state": "failed", "error": str(exc)}

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()


export_manager = ExportManager()
