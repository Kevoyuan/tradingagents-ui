"""Pytest fixtures for backend server test suite."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trade_ui.server import create_app


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Provide an isolated temporary runs directory."""
    dir_path = tmp_path / "runs"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


@pytest.fixture
def app(runs_dir: Path):
    """Provide a FastAPI test app configured with isolated runs_dir and stub runner."""
    return create_app(runs_dir=runs_dir, use_stub=True)


@pytest.fixture
def client(app):
    """Provide a test HTTP client."""
    with TestClient(app) as test_client:
        yield test_client
