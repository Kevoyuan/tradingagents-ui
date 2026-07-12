"""Tests for trade_ui.cli helper functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from trade_ui.cli import (
    _find_project_root,
    _resolve_app_path,
)


class TestFindProjectRoot:
    def test_returns_parent_of_cli_module(self):
        root = _find_project_root()
        assert (root / "app.py").exists() or (root / "trade_ui").is_dir()

    def test_returns_path_object(self):
        assert isinstance(_find_project_root(), Path)


class TestResolveAppPath:
    def test_env_path_takes_priority(self, monkeypatch, tmp_path):
        app = tmp_path / "app.py"
        app.write_text("# test")
        monkeypatch.setenv("TRADINGAGENTS_UI_APP_PATH", str(app))
        assert _resolve_app_path() == app.resolve()

    def test_env_path_exits_if_not_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TRADINGAGENTS_UI_APP_PATH", str(tmp_path / "nope.py"))
        with pytest.raises(SystemExit):
            _resolve_app_path()

    def test_falls_back_to_project_root(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TRADINGAGENTS_UI_APP_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        result = _resolve_app_path()
        # Should find app.py from installed package or cwd
        assert result.name == "app.py"
