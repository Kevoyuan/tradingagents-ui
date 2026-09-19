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
    assets = static / "assets"
    assets.mkdir()
    (assets / "index-abc123.js").write_text("console.log('bundle')", encoding="utf-8")
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


def test_spa_shell_revalidates_but_hashed_assets_stay_cacheable(tmp_path: Path) -> None:
    """The shell must never be served from heuristic cache.

    The launcher reuses an already-open app window, so a window that keeps a
    cached shell keeps loading the previous build's JS. That produced
    "the app is running old code" symptoms twice: once as counters stuck at
    zero, once as a Settings button that appeared to do nothing. The shell is
    the only file that names the bundle, so it carries `no-cache`; the hashed
    asset names change with their contents and stay cacheable.
    """
    client = TestClient(create_ui_app(static_dir=_make_static(tmp_path)))

    root = client.get("/")
    assert root.headers.get("cache-control") == "no-cache"

    # A deep route returns the same shell, so it carries the same directive.
    deep = client.get("/reports/NBIS/2026-09-18")
    assert deep.headers.get("cache-control") == "no-cache"

    asset = client.get("/assets/index-abc123.js")
    assert asset.status_code == 200
    assert asset.headers.get("cache-control") is None
