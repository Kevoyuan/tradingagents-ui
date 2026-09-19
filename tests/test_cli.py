"""Tests for trade_ui.cli helper functions."""

from __future__ import annotations

from pathlib import Path

from trade_ui.cli import _find_project_root


class TestFindProjectRoot:
    def test_returns_path_object(self):
        assert isinstance(_find_project_root(), Path)
