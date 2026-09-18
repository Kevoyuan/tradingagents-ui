"""Tests for Report Export endpoints and state machine."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from trade_ui.server import create_app
from trade_ui.server.export import (
    HTML_REPORT_THEME_VERSION,
    export_manager,
    get_export_filename,
)


def create_sample_report(root: Path, ticker: str, date: str) -> Path:
    rep_dir = root / ticker / date / "reports"
    rep_dir.mkdir(parents=True, exist_ok=True)
    (rep_dir / "5_portfolio").mkdir(parents=True, exist_ok=True)
    (rep_dir / "5_portfolio" / "decision.md").write_text(
        "**Rating**: Hold\n",
        encoding="utf-8",
    )
    (rep_dir / "complete_report.md").write_text(
        f"# {ticker} Report {date}\n\nSummary text.\n",
        encoding="utf-8",
    )
    return rep_dir


def test_export_status_and_get_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET .../export returns 404 when not generated; status reports idle."""
    logs_dir = tmp_path / "logs"
    create_sample_report(logs_dir, "XYZ", "2026-05-01")
    monkeypatch.setenv("TRADINGAGENTS_LOGS_DIR", str(logs_dir))

    app = create_app(runs_dir=tmp_path / "runs", use_stub=True)
    with TestClient(app) as client:
        # Non-existent report 404s
        assert client.get("/api/reports/MISSING/2026-01-01/export/status").status_code == 404
        assert client.get("/api/reports/MISSING/2026-01-01/export").status_code == 404

        # Existing report with no export is idle and 404s on HTML fetch
        status_res = client.get("/api/reports/XYZ/2026-05-01/export/status")
        assert status_res.status_code == 200
        assert status_res.json() == {"state": "idle", "error": None}

        export_res = client.get("/api/reports/XYZ/2026-05-01/export")
        assert export_res.status_code == 404


def test_export_cached_html_served(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET .../export serves cached HTML when the versioned file is present."""
    logs_dir = tmp_path / "logs"
    rep_dir = create_sample_report(logs_dir, "XYZ", "2026-05-01")
    monkeypatch.setenv("TRADINGAGENTS_LOGS_DIR", str(logs_dir))

    # Pre-populate cached export HTML file
    export_file = rep_dir / get_export_filename()
    sample_html = "<html><body><h1>Exported Report</h1></body></html>"
    export_file.write_text(sample_html, encoding="utf-8")

    app = create_app(runs_dir=tmp_path / "runs", use_stub=True)
    with TestClient(app) as client:
        status_res = client.get("/api/reports/XYZ/2026-05-01/export/status")
        assert status_res.status_code == 200
        assert status_res.json() == {"state": "ready", "error": None}

        export_res = client.get("/api/reports/XYZ/2026-05-01/export")
        assert export_res.status_code == 200
        assert export_res.text == sample_html
        assert "text/html" in export_res.headers["content-type"]


def test_theme_version_invalidation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An export with an outdated theme version is ignored (invalidated)."""
    assert HTML_REPORT_THEME_VERSION in get_export_filename()

    logs_dir = tmp_path / "logs"
    rep_dir = create_sample_report(logs_dir, "XYZ", "2026-05-01")
    monkeypatch.setenv("TRADINGAGENTS_LOGS_DIR", str(logs_dir))

    # Write old export with an outdated version
    old_file = rep_dir / "complete_report__export-quant-terminal-v1-old.html"
    old_file.write_text("<html>Old Theme</html>", encoding="utf-8")

    app = create_app(runs_dir=tmp_path / "runs", use_stub=True)
    with TestClient(app) as client:
        # Current version is not present, so status is idle and export returns 404
        status_res = client.get("/api/reports/XYZ/2026-05-01/export/status")
        assert status_res.status_code == 200
        assert status_res.json() == {"state": "idle", "error": None}

        assert client.get("/api/reports/XYZ/2026-05-01/export").status_code == 404


def test_export_state_machine_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /api/reports/.../export returns 202 and transitions state: running -> ready."""
    logs_dir = tmp_path / "logs"
    create_sample_report(logs_dir, "XYZ", "2026-05-01")
    monkeypatch.setenv("TRADINGAGENTS_LOGS_DIR", str(logs_dir))

    export_manager._tasks.clear()

    def fake_export_sync(report_path: Path, ticker: str, trade_date: str) -> Path:
        time.sleep(0.05)
        out = report_path / get_export_filename()
        out.write_text("<html><body>Synthetic Output</body></html>", encoding="utf-8")
        return out

    app = create_app(runs_dir=tmp_path / "runs", use_stub=True)
    with (
        patch("trade_ui.server.export.run_export_sync", side_effect=fake_export_sync),
        TestClient(app) as client,
    ):
        post_res = client.post("/api/reports/XYZ/2026-05-01/export")
        assert post_res.status_code == 202
        data = post_res.json()
        assert data["status"] == "accepted"

        # Wait briefly for worker thread to finish
        for _ in range(20):
            st = client.get("/api/reports/XYZ/2026-05-01/export/status").json()
            if st["state"] == "ready":
                break
            time.sleep(0.05)

        st = client.get("/api/reports/XYZ/2026-05-01/export/status").json()
        assert st["state"] == "ready"

        # Cached HTML can now be fetched
        html_res = client.get("/api/reports/XYZ/2026-05-01/export")
        assert html_res.status_code == 200
        assert "Synthetic Output" in html_res.text


def test_export_state_machine_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /api/reports/.../export captures worker errors: running -> failed."""
    logs_dir = tmp_path / "logs"
    create_sample_report(logs_dir, "XYZ", "2026-05-01")
    monkeypatch.setenv("TRADINGAGENTS_LOGS_DIR", str(logs_dir))

    export_manager._tasks.clear()

    def failing_export_sync(report_path: Path, ticker: str, trade_date: str) -> Path:
        time.sleep(0.05)
        raise RuntimeError("Synthetic conversion failure")

    app = create_app(runs_dir=tmp_path / "runs", use_stub=True)
    with (
        patch("trade_ui.server.export.run_export_sync", side_effect=failing_export_sync),
        TestClient(app) as client,
    ):
        post_res = client.post("/api/reports/XYZ/2026-05-01/export")
        assert post_res.status_code == 202

        # Poll for failed state
        for _ in range(20):
            st = client.get("/api/reports/XYZ/2026-05-01/export/status").json()
            if st["state"] == "failed":
                break
            time.sleep(0.05)

        st = client.get("/api/reports/XYZ/2026-05-01/export/status").json()
        assert st["state"] == "failed"
        assert "Synthetic conversion failure" in (st["error"] or "")

        # Reading report remains functional (404 for missing export, but detail route works)
        assert client.get("/api/reports/XYZ/2026-05-01/export").status_code == 404
        detail_res = client.get("/api/reports/XYZ/2026-05-01")
        assert detail_res.status_code == 200
