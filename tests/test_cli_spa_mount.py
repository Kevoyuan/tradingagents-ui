"""Regression tests for the SPA static mount in trade_ui.cli."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trade_ui.cli import create_ui_app


def _make_static(tmp_path: Path) -> Path:
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    return static


def test_spa_mount_rejects_websocket_instead_of_crashing(tmp_path: Path) -> None:
    """A websocket upgrade must be refused cleanly, not raise inside the handler.

    StaticFiles.__call__ asserts scope["type"] == "http". Before this guard, any
    websocket sent to the server raised AssertionError and produced a 500. The
    real-world trigger was a stale Streamlit tab that saw /_stcore/health answer
    on this port and assumed a Streamlit server was listening.
    """
    client = TestClient(create_ui_app(static_dir=_make_static(tmp_path)))

    # Starlette signals the refusal by raising while entering the connection.
    with pytest.raises(Exception), client.websocket_connect("/"):  # noqa: B017
        pass

    # The server must be unaffected.
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_spa_mount_serves_index_and_does_not_shadow_api(tmp_path: Path) -> None:
    """Deep routes fall back to the SPA, while /api stays owned by the API."""
    client = TestClient(create_ui_app(static_dir=_make_static(tmp_path)))

    root = client.get("/")
    assert root.status_code == 200
    assert 'id="root"' in root.text

    deep = client.get("/reports/NBIS/2026-09-18")
    assert deep.status_code == 200
    assert 'id="root"' in deep.text

    # /api/providers is not implemented, but it must 404 as an API route rather
    # than be swallowed by the SPA fallback.
    assert client.get("/api/providers").status_code == 404
